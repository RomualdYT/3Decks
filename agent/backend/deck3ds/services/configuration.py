"""One transaction boundary for HTTP saves and external configuration edits."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from .. import config as configuration
from ..config import Config, ConfigError
from ..extensions.manifest import ExtensionError
from ..feature_catalog import FEATURE_SPECS
from .errors import ServiceError
from .executor import WorkPool


def fingerprint(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "missing"


class ConfigService:
    def __init__(
        self,
        initial: Config,
        path: Path | None,
        pool: WorkPool,
        validate_extensions: Callable[[Config], None],
        install: Callable[[Config], None],
        publish: Callable[[], Awaitable[None]],
        log: Callable[[str], None],
    ) -> None:
        self.current = copy.deepcopy(initial)
        self.path = path
        self._pool = pool
        self._validate_extensions = validate_extensions
        self._install = install
        self._publish = publish
        self._log = log
        self._lock = asyncio.Lock()
        self._accepted = fingerprint(path)
        self._observed = self._accepted
        self._pending: set[asyncio.Task[dict[str, Any]]] = set()
        self._closing = False

    def document(self) -> dict[str, Any]:
        return {
            "config": configuration.to_raw(self.current),
            "path": str(self.path or ""),
        }

    def prepare(self, raw: object) -> Config:
        if not isinstance(raw, dict):
            raise ServiceError(400, "un objet est attendu", "invalid_body")
        candidate = dict(raw)
        candidate["scripts"] = {
            name: list(argv) for name, argv in self.current.scripts.items()
        }
        candidate["revision"] = self.current.revision + 1
        try:
            parsed = configuration.parse(candidate)
            self._validate_extensions(parsed)
            return parsed
        except (ConfigError, ExtensionError) as error:
            raise ServiceError(422, str(error), "invalid_config") from error

    def validate(self, raw: object) -> dict[str, Any]:
        try:
            self.prepare(raw)
        except ServiceError as error:
            if error.status != 422:
                raise
            return {"valid": False, "error": error.message}
        return {"valid": True, "error": ""}

    async def save(self, raw: object) -> dict[str, Any]:
        if self._closing:
            raise ServiceError(503, "Agent en cours d'arret", "stopping")
        task = asyncio.create_task(self._save(copy.deepcopy(raw)), name="config-commit")
        self._pending.add(task)

        def finished(completed: asyncio.Task[dict[str, Any]]) -> None:
            self._pending.discard(completed)
            if not completed.cancelled():
                completed.exception()

        task.add_done_callback(finished)
        return await asyncio.shield(task)

    async def update_runtime_settings(
        self,
        *,
        features: dict[str, bool] | None = None,
        obs_enabled: bool | None = None,
    ) -> dict[str, Any]:
        """Commit trusted tray changes through the regular transaction path."""

        changes = features or {}
        unknown = set(changes) - set(FEATURE_SPECS)
        if unknown:
            raise ValueError(f"Unknown features: {sorted(unknown)}")
        if any(type(value) is not bool for value in changes.values()):
            raise TypeError("Feature values must be booleans")
        raw = self.document()["config"]
        raw_features = raw["features"]
        assert isinstance(raw_features, dict)
        raw_features.update(changes)
        if obs_enabled is not None:
            if type(obs_enabled) is not bool:
                raise TypeError("OBS state must be a boolean")
            integrations = raw["integrations"]
            assert isinstance(integrations, dict)
            obs = integrations["obs"]
            assert isinstance(obs, dict)
            obs["enabled"] = obs_enabled
        return await self.save(raw)

    async def _save(self, raw: object) -> dict[str, Any]:
        async with self._lock:
            if self.path is None:
                raise ServiceError(
                    409,
                    "aucun fichier de configuration a enregistrer",
                    "no_config_file",
                )
            if not isinstance(raw, dict):
                raise ServiceError(400, "un objet est attendu", "invalid_body")
            revision = raw.get("revision")
            changed = await self._pool.run(fingerprint, self.path) != self._accepted
            if changed or (type(revision) is int and revision != self.current.revision):
                raise ServiceError(
                    409,
                    "la configuration a change depuis son ouverture; rechargez-la",
                    "config_conflict",
                )
            parsed = self.prepare(raw)
            try:
                committed = await self._pool.run(configuration.save, parsed, self.path)
            except OSError as error:
                raise ServiceError(
                    500,
                    "ecriture de la configuration impossible",
                    "config_write_failed",
                ) from error
            self.current = parsed
            # Fingerprint our commit, not an external edit racing after replace().
            self._accepted = committed
            self._observed = self._accepted
            self._install(copy.deepcopy(parsed))
            await self._publish_safely()
            self._log(
                f"Configuration enregistree (revision {parsed.revision}, {len(parsed.pages)} pages)"
            )
            return {"saved": True, "config": configuration.to_raw(parsed)}

    async def _publish_safely(self) -> None:
        try:
            await self._publish()
        except Exception:
            self._log(
                "Configuration enregistree; diffusion differee jusqu'a la prochaine connexion"
            )

    async def reload_if_changed(self) -> bool:
        if self.path is None or self._closing:
            return False
        async with self._lock:
            stamp = await self._pool.run(fingerprint, self.path)
            if stamp in ("missing", self._observed):
                return False
            self._observed = stamp
            try:
                text = await self._pool.run(self.path.read_text, encoding="utf-8")
                loaded = configuration.parse(json.loads(text))
                self._validate_extensions(loaded)
            except (OSError, ValueError, ConfigError, ExtensionError):
                self._log("Configuration externe invalide; ancienne version conservee")
                return False
            loaded.revision = max(loaded.revision, self.current.revision + 1)
            self.current = loaded
            self._accepted = hashlib.sha256(text.encode("utf-8")).hexdigest()
            self._observed = self._accepted
            self._install(copy.deepcopy(loaded))
            await self._publish_safely()
            self._log(f"Configuration rechargee (revision {loaded.revision})")
            return True

    def stop_admissions(self) -> None:
        self._closing = True

    async def close(self) -> None:
        self.stop_admissions()
        if self._pending:
            await asyncio.gather(*self._pending, return_exceptions=True)
