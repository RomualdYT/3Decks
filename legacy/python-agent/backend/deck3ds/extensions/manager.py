"""Extension lifecycle, trust registry and cached contributions.

Native code is never imported into the agent. Approval is tied to the SHA-256
of the whole installed package. Process isolation is not an OS sandbox.
"""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from .manifest import ExtensionError, load_manifest, reference, validate_values
from .output import normalize, short
from .packages import (
    fingerprint,
    install_archive,
    read_json,
    retire_package,
    write_private_json,
)
from .worker import Worker


@dataclass
class Installed:
    path: Path
    manifest: dict
    digest: str
    enabled: bool = False
    approved: str = ""
    status: str = "disabled"
    error: str = ""
    worker: Worker | None = None
    snapshot: dict = field(default_factory=dict)
    next_poll: float = 0
    updated_at: float = 0
    lock: object = field(default_factory=threading.RLock)


class ExtensionManager:
    def __init__(self, root: Path | None, platform: str) -> None:
        self.root = root.expanduser().resolve() if root else None
        self.platform = platform
        self.items: dict[str, Installed] = {}
        self.discovery_errors: list[str] = []
        self._registry_lock = threading.RLock()
        self._registry: dict = {}
        self._registry_error = ""
        self._closing = False
        self.rescan()

    def rescan(self) -> None:
        if self.root is None:
            return
        with self._registry_lock:
            try:
                self._registry = read_json(self.root / "registry.json")
                self._registry_error = ""
            except ExtensionError as error:
                # Fail closed without preventing the native agent from starting.
                self._registry = {}
                self._registry_error = str(error)
                self.close()
                self.items = {}
            found = {}
            errors = [self._registry_error] if self._registry_error else []
            paths = sorted((self.root / "packages").glob("*"))
            if len(paths) > 64:
                errors.append(
                    "Maximum 64 installed extensions; extra packages are ignored"
                )
            for path in paths[:64]:
                if not path.is_dir() or path.is_symlink():
                    continue
                try:
                    manifest = load_manifest(path / "extension.json")
                    if manifest["id"] != path.name:
                        raise ExtensionError("Folder name must match manifest id")
                    digest = fingerprint(path)
                    old = self.items.get(path.name)
                    if old and old.digest == digest:
                        found[path.name] = old
                        continue
                    if old:
                        self._stop(old)
                    state = self._registry.get(path.name, {})
                    if not isinstance(state, dict):
                        state = {}
                    item = Installed(
                        path,
                        manifest,
                        digest,
                        state.get("enabled") is True,
                        str(state.get("approved", "")),
                    )
                    if self.platform not in manifest["platforms"]:
                        item.status = "unsupported"
                    elif item.approved != digest:
                        item.status = "untrusted"
                    elif item.enabled:
                        item.status = "starting"
                    found[path.name] = item
                except (ExtensionError, OSError) as error:
                    errors.append(f"{path.name}: {error}")
            for identifier, old in self.items.items():
                if identifier not in found:
                    self._stop(old)
            self.items = found
            self.discovery_errors = errors

    def _item(self, identifier: str) -> Installed:
        item = self.items.get(identifier)
        if item is None:
            raise ExtensionError(
                "Extension is missing; install it from the Extensions tab"
            )
        return item

    def _settings_path(self, identifier: str) -> Path:
        return self.root / "data" / identifier / "settings.json"

    def _settings(self, item: Installed) -> dict:
        return read_json(self._settings_path(item.manifest["id"]))

    def _save_approval(self, item: Installed) -> None:
        with self._registry_lock:
            if self._registry_error:
                raise ExtensionError(
                    self._registry_error
                    + "; repair or move registry.json, then refresh"
                )
            self._registry[item.manifest["id"]] = {
                "enabled": item.enabled,
                "approved": item.approved,
            }
            write_private_json(self.root / "registry.json", self._registry)

    def _stop(self, item: Installed) -> None:
        with item.lock:
            if item.worker:
                item.worker.stop()
                item.worker = None
            item.snapshot = {}
            item.updated_at = 0
            item.next_poll = 0

    def _start(self, item: Installed) -> None:
        if not item.enabled or item.approved != fingerprint(item.path):
            item.status = "untrusted"
            raise ExtensionError("Package changed: review and approve it again")
        if self.platform not in item.manifest["platforms"]:
            raise ExtensionError(
                "This extension does not support this operating system"
            )
        settings = validate_values(item.manifest["settings"], self._settings(item))
        data_dir = self.root / "data" / item.manifest["id"] / "storage"
        data_dir.mkdir(parents=True, exist_ok=True)
        worker = Worker(item.path, item.manifest)
        try:
            worker.start(settings, data_dir)
        except Exception:
            worker.close()
            raise
        item.worker = worker
        item.status = "ready"
        item.error = ""
        item.next_poll = 0

    def enable(self, identifier: str, enabled: bool, digest: str = "") -> None:
        item = self._item(identifier)
        with self._registry_lock, item.lock:
            if self._registry_error:
                raise ExtensionError(
                    self._registry_error
                    + "; repair or move registry.json, then refresh"
                )
            if enabled:
                actual = fingerprint(item.path)
                if digest != actual or digest != item.digest:
                    raise ExtensionError(
                        "Package changed: refresh before approving activation"
                    )
                if self.platform not in item.manifest["platforms"]:
                    raise ExtensionError("Unsupported operating system")
                validate_values(item.manifest["settings"], self._settings(item))
                item.approved = actual
            self._stop(item)
            item.enabled = enabled
            item.status = "starting" if enabled else "disabled"
            item.error = ""
            self._save_approval(item)
            if enabled:
                try:
                    self._start(item)
                except ExtensionError as error:
                    self._fail(item, error)
                    raise

    def configure(self, identifier: str, values: dict) -> None:
        item = self._item(identifier)
        with item.lock:
            merged = {**self._settings(item), **values}
            checked = validate_values(item.manifest["settings"], merged)
            write_private_json(self._settings_path(identifier), checked)
            self._stop(item)
            if item.enabled and item.approved == item.digest:
                item.status = "starting"

    def restart(self, identifier: str) -> None:
        item = self._item(identifier)
        if not item.enabled or item.approved != item.digest:
            raise ExtensionError("Approve and activate the extension first")
        with item.lock:
            self._stop(item)
            item.status = "starting"
            item.error = ""

    def install(self, archive: Path) -> str:
        if self.root is None:
            raise ExtensionError("No extension directory is configured")
        with self._registry_lock:
            if self._registry_error:
                raise ExtensionError(self._registry_error)
            if len(self.items) >= 64:
                raise ExtensionError("Maximum 64 installed extensions")
            identifier = install_archive(archive, self.root)
            # Reinstalling a removed package must never resurrect old approval.
            self._registry[identifier] = {"enabled": False, "approved": ""}
            write_private_json(self.root / "registry.json", self._registry)
            self.rescan()
            return identifier

    def remove(self, identifier: str) -> None:
        item = self._item(identifier)
        self.enable(identifier, False)
        with self._registry_lock:
            retire_package(item.path, self.root)
            self.items.pop(identifier, None)

    def _fail(self, item: Installed, error: Exception) -> None:
        self._stop(item)
        item.status = "error"
        item.error = (
            str(error)
            if isinstance(error, ExtensionError)
            else "Extension runtime failed"
        )

    def poll(self, item: Installed) -> None:
        with item.lock:
            if (
                self._closing
                or item.status not in ("starting", "ready")
                or time.monotonic() < item.next_poll
            ):
                return
            try:
                if item.worker is None:
                    self._start(item)
                snapshot = normalize(item.manifest, item.worker.call("poll", {}))
                item.snapshot = snapshot
                item.updated_at = time.time()
                item.next_poll = time.monotonic() + item.manifest["poll_interval"]
            except Exception as error:
                self._fail(item, error)

    async def run(self) -> None:
        pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="3decks-extension")
        loop = asyncio.get_running_loop()
        try:
            while True:
                # A dedicated bounded pool cannot starve native platform work.
                await asyncio.gather(
                    *(
                        loop.run_in_executor(pool, self.poll, item)
                        for item in list(self.items.values())
                    )
                )
                await asyncio.sleep(0.5)
        finally:
            self._closing = True
            await asyncio.to_thread(pool.shutdown, wait=True, cancel_futures=True)
            await asyncio.to_thread(self.close)

    def execute(self, kind: str, arguments: dict) -> dict:
        target = reference(kind)
        if target is None:
            raise ExtensionError("Invalid extension action reference")
        item = self._item(target[0])
        # A slow poll must not create an unbounded command queue.
        if not item.lock.acquire(timeout=5):
            raise ExtensionError("Extension busy; try again")
        try:
            if item.status != "ready" or not item.worker:
                raise ExtensionError("Extension unavailable; check the Extensions tab")
            action = next(
                (
                    action
                    for action in item.manifest["actions"]
                    if action["id"] == target[1]
                ),
                None,
            )
            if action is None:
                raise ExtensionError("This extension action no longer exists")
            checked = validate_values(action["arguments"], arguments)
            response = item.worker.call(
                "action", {"action": target[1], "arguments": checked}
            )
            if (
                not isinstance(response, dict)
                or not isinstance(response.get("ok"), bool)
                or not isinstance(response.get("message", ""), str)
            ):
                raise ExtensionError("Invalid action result")
            item.next_poll = 0
            return {
                "ok": response["ok"],
                "message": short(response.get("message", ""), 63),
            }
        except ExtensionError:
            # Bad action arguments do not disable an otherwise healthy worker.
            if item.worker and (
                item.worker.process is None or item.worker.process.poll() is not None
            ):
                self._fail(
                    item,
                    ExtensionError("Extension process stopped; restart it from the UI"),
                )
            raise
        finally:
            item.lock.release()

    def validate_config(self, config) -> None:
        """Keep references to missing packages portable; validate installed ones."""
        for page in config.pages:
            for value, group in (
                (page.source, "sources"),
                (page.dashboard, "dashboards"),
            ):
                target = reference(value)
                if (
                    target
                    and target[0] in self.items
                    and not any(
                        spec["id"] == target[1]
                        for spec in self.items[target[0]].manifest[group]
                    )
                ):
                    raise ExtensionError(f"Unknown extension {group}: {value}")
            for button in page.buttons:
                for action in (button.action, button.hold_action):
                    target = reference(action.kind) if action else None
                    if target and target[0] in self.items:
                        spec = next(
                            (
                                spec
                                for spec in self.items[target[0]].manifest["actions"]
                                if spec["id"] == target[1]
                            ),
                            None,
                        )
                        if spec is None:
                            raise ExtensionError(
                                f"Unknown extension action: {action.kind}"
                            )
                        validate_values(spec["arguments"], action.args)

    def catalog(self) -> dict:
        actions, sources, dashboards = [], [], []
        for item in list(self.items.values()):
            manifest = item.manifest
            for group, destination in (
                ("actions", actions),
                ("sources", sources),
                ("dashboards", dashboards),
            ):
                for spec in manifest[group]:
                    key = f"ext:{manifest['id']}/{spec['id']}"
                    entry = {
                        **spec,
                        "extension": manifest["id"],
                        "extension_name": manifest["name"],
                        "supported": item.status == "ready",
                        "capability": None,
                    }
                    entry.update(
                        {"kind": key, "category": "extensions"}
                        if group == "actions"
                        else {"name": key}
                    )
                    destination.append(entry)
        return {"actions": actions, "sources": sources, "dashboards": dashboards}

    def describe(self) -> dict:
        result = []
        for item in list(self.items.values()):
            settings_error = ""
            try:
                settings = self._settings(item)
            except ExtensionError as error:
                settings = {}
                settings_error = str(error)
            secret_names = {
                spec["name"]
                for spec in item.manifest["settings"]
                if spec["type"] == "password"
            }
            result.append(
                {
                    "manifest": item.manifest,
                    "digest": item.digest,
                    "enabled": item.enabled,
                    "status": item.status,
                    "error": settings_error or item.error,
                    "updated_at": item.updated_at,
                    "settings": {
                        key: value
                        for key, value in settings.items()
                        if key not in secret_names
                    },
                    "secret_fields_set": [
                        key for key in secret_names if settings.get(key)
                    ],
                }
            )
        return {
            "api_version": 1,
            "directory": str(self.root or ""),
            "extensions": result,
            "errors": self.discovery_errors,
        }

    def close(self) -> None:
        for item in list(self.items.values()):
            self._stop(item)
