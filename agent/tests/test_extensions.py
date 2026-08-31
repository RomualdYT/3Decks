"""Extension API contract, real subprocess lifecycle and hostile package tests.

All fixtures are temporary. No third-party program, account or host permission
is needed; this suite runs unchanged on the three CI operating systems.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import stat
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from deck3ds.config import Action, ConfigError, parse, to_raw
from deck3ds.actions import Dispatcher
from deck3ds.extensions.bridge import (
    config_message,
    fill_sources,
    localized_state,
    preview_payload,
    state_payload,
)
from deck3ds.extensions.manager import ExtensionManager
from deck3ds.extensions.manifest import (
    ExtensionError,
    fields,
    load_manifest,
    reference,
    validate_values,
)
from deck3ds.extensions.output import normalize, short
from deck3ds.extensions.packages import fingerprint, install_archive
from deck3ds.extensions.scaffold import create, pack
from deck3ds.extensions.worker import Worker
from deck3ds.protocol import encode
from deck3ds.server import Options, Server
from deck3ds.ui.api import Api
from deck3ds.ui.http import HttpError, Request
from test_agent import FakePlatform

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "examples" / "extensions" / "focus-timer"
)
IDENTIFIER = "org.3decks.focus-timer"
PREFIX = f"ext:{IDENTIFIER}/"


def configuration(layout="grid"):
    return parse(
        {
            "pages": [
                {
                    "id": "focus",
                    "title": "Focus",
                    "dashboard": PREFIX + "timer",
                    "source": PREFIX + "presets",
                    "layout": layout,
                    "buttons": [],
                }
            ]
        }
    )


class ExtensionFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.package = self.root / "source"
        shutil.copytree(EXAMPLE, self.package)
        self.manager = ExtensionManager(self.root / "extensions", sys.platform)
        self.addCleanup(self.manager.close)

    def install(self):
        archive = self.root / "example.3deckext"
        pack(self.package, archive)
        self.manager.install(archive)
        return self.manager.items[IDENTIFIER]

    def activate(self):
        item = self.install()
        self.manager.enable(IDENTIFIER, True, item.digest)
        self.manager.poll(item)
        return item


class ManifestTests(ExtensionFixture):
    def test_reference_namespace(self):
        self.assertEqual(reference(PREFIX + "start"), (IDENTIFIER, "start"))
        for value in (None, "volume.up", "ext:../../tmp/run", "ext:com.example/a/b"):
            self.assertIsNone(reference(value))

    def test_typed_fields_and_defaults(self):
        specs = fields(
            [
                {
                    "name": "number",
                    "type": "number",
                    "min": -10,
                    "max": -1,
                    "default": -3,
                },
                {"name": "enabled", "type": "boolean", "default": True},
                {
                    "name": "mode",
                    "type": "select",
                    "choices": [{"value": "one"}],
                    "required": True,
                },
            ],
            "test",
        )
        self.assertEqual(
            validate_values(specs, {"mode": "one"}),
            {"number": -3, "enabled": True, "mode": "one"},
        )
        self.assertEqual(
            validate_values(specs, {"number": None, "mode": "one"})["number"], -3
        )
        for values in (
            {},
            {"mode": "two"},
            {"mode": "one", "number": True},
            {"mode": "one", "number": float("nan")},
            {"mode": "one", "other": 1},
        ):
            with self.subTest(values=values), self.assertRaises(ExtensionError):
                validate_values(specs, values)

    def test_invalid_manifests(self):
        path = self.package / "extension.json"
        original = json.loads(path.read_text())
        variants = [
            {"api_version": True},
            {"api_version": 2},
            {"entrypoint": "../outside.py"},
            {"runtime": "shell"},
            {"settings": [{"name": "bad", "type": []}]},
            {"name": "\ud800"},
            {"permissions": [{}]},
            {"platforms": ["mac"]},
            {"settings": [{"name": "secret", "type": "password", "default": "token"}]},
            {
                "actions": [
                    {"id": "start", "title": "Start", "arguments": [{"name": "type"}]}
                ]
            },
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                path.write_text(json.dumps({**original, **variant}))
                with self.assertRaises(ExtensionError):
                    load_manifest(path)

    def test_missing_extensions_roundtrip(self):
        raw = {
            "pages": [
                {
                    "id": "main",
                    "title": "Main",
                    "dashboard": "ext:com.missing/tile",
                    "buttons": [
                        {
                            "id": "run",
                            "label": "Run",
                            "action": {"type": "ext:com.missing/run", "amount": 7},
                        }
                    ],
                }
            ]
        }
        config = parse(raw)
        self.manager.validate_config(config)
        self.assertEqual(
            parse(to_raw(config)).pages[0].buttons[0].action.args, {"amount": 7}
        )
        self.assertFalse(
            state_payload(self.manager, config)["extension_buttons"][0]["available"]
        )

    def test_nonfinite_and_oversized_arguments_rejected(self):
        for value in (float("nan"), "x" * 9000):
            with self.assertRaises(ConfigError):
                parse(
                    {
                        "pages": [
                            {
                                "id": "main",
                                "buttons": [
                                    {
                                        "id": "run",
                                        "action": {
                                            "type": PREFIX + "start",
                                            "value": value,
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                )

    def test_unknown_icon_is_safe_to_save_from_catalog(self):
        self.install()
        spec = next(
            item
            for item in self.manager.catalog()["actions"]
            if item["kind"] == PREFIX + "start"
        )
        parsed = parse(
            {
                "pages": [
                    {
                        "id": "main",
                        "buttons": [
                            {
                                "id": "run",
                                "icon": spec["icon"],
                                "action": {"type": spec["kind"], "minutes": 5},
                            }
                        ],
                    }
                ]
            }
        )
        self.manager.validate_config(parsed)


class PackageTests(ExtensionFixture):
    def test_import_never_runs_code_and_requires_digest(self):
        item = self.install()
        self.assertIsNone(item.worker)
        self.assertEqual(item.status, "untrusted")
        with self.assertRaises(ExtensionError):
            self.manager.enable(IDENTIFIER, True, "wrong")
        self.assertIsNone(item.worker)

    def test_reimport_does_not_overwrite(self):
        item = self.install()
        with self.assertRaises(ExtensionError):
            self.manager.install(self.root / "example.3deckext")
        self.assertEqual(fingerprint(item.path), item.digest)

    def test_traversal_absolute_symlink_and_duplicate_archives(self):
        cases = [
            "../escape",
            "/tmp/escape",
            "C:/escape",
            "a\\escape",
            "NUL.txt",
            "aux/test.py",
            "main.py.",
        ]
        for index, name in enumerate(cases):
            archive = self.root / f"bad{index}.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr(name, "bad")
            with self.subTest(name=name), self.assertRaises(ExtensionError):
                install_archive(archive, self.manager.root)
        archive = self.root / "link.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            info = zipfile.ZipInfo("link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            bundle.writestr(info, "../outside")
        with self.assertRaises(ExtensionError):
            install_archive(archive, self.manager.root)
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("A", "a")
            bundle.writestr("a", "b")
        with self.assertRaises(ExtensionError):
            install_archive(archive, self.manager.root)
        self.assertFalse((self.root / "escape").exists())

    def test_many_files_rejected(self):
        archive = self.root / "many.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            for i in range(257):
                bundle.writestr(f"file{i}", "")
        with self.assertRaises(ExtensionError):
            install_archive(archive, self.manager.root)

    def test_corrupt_registry_fails_closed_preserving_file(self):
        item = self.activate()
        process = item.worker.process
        path = self.manager.root / "registry.json"
        path.write_text("broken")
        self.manager.rescan()
        self.assertTrue(self.manager.discovery_errors)
        self.assertIsNotNone(process.poll())
        item = self.manager.items[IDENTIFIER]
        with self.assertRaises(ExtensionError):
            self.manager.enable(IDENTIFIER, True, item.digest)
        self.assertEqual(path.read_text(), "broken")

    def test_code_edit_revokes_trust(self):
        item = self.activate()
        process = item.worker.process
        with (item.path / "main.py").open("a") as stream:
            stream.write("\n# changed\n")
        self.manager.rescan()
        self.assertEqual(self.manager.items[IDENTIFIER].status, "untrusted")
        self.assertIsNotNone(process.poll())

    def test_remove_is_recoverable_and_reinstall_untrusted(self):
        self.activate()
        self.manager.configure(IDENTIFIER, {"title": "Retained"})
        self.manager.remove(IDENTIFIER)
        self.assertEqual(len(list((self.manager.root / "trash").iterdir())), 1)
        self.manager.install(self.root / "example.3deckext")
        item = self.manager.items[IDENTIFIER]
        self.assertFalse(item.enabled)
        self.assertEqual(
            self.manager.describe()["extensions"][0]["settings"]["title"], "Retained"
        )

    def test_other_os_not_started(self):
        self.manager.platform = "unsupported"
        item = self.install()
        self.assertEqual(item.status, "unsupported")
        with self.assertRaises(ExtensionError):
            self.manager.enable(IDENTIFIER, True, item.digest)


class RuntimeTests(ExtensionFixture):
    def test_real_action_dashboard_state_sources(self):
        item = self.activate()
        self.assertEqual(item.status, "ready", item.error)
        self.assertTrue(self.manager.execute(PREFIX + "start", {"minutes": 1})["ok"])
        self.manager.poll(item)
        self.assertTrue(item.snapshot["states"]["running"])
        self.assertEqual(
            item.snapshot["dashboards"]["timer"]["cards"][0]["value"], "01:00"
        )
        for layout in ("grid", "list"):
            config = configuration(layout)
            self.assertTrue(fill_sources(self.manager, config))
            self.assertFalse(fill_sources(self.manager, config))
            payload = config_message(self.manager, config, "fr")
            self.assertEqual(payload["pages"][0]["dashboard"], "extension")
            self.assertEqual(
                payload["pages"][0]["entries" if layout == "list" else "buttons"][1][
                    "label"
                ],
                "Réinitialiser",
            )
            self.assertNotIn("arguments", json.dumps(payload))
            self.assertEqual(to_raw(config)["pages"][0]["buttons"], [])
            self.assertTrue(
                state_payload(self.manager, config)["extension_buttons"][0]["active"]
            )

    def test_config_validates_installed_contributions(self):
        self.install()
        config = configuration()
        self.manager.validate_config(config)
        config.pages[0].dashboard = PREFIX + "unknown"
        with self.assertRaises(ExtensionError):
            self.manager.validate_config(config)

    def test_action_validation_does_not_disable_worker(self):
        item = self.activate()
        with self.assertRaises(ExtensionError):
            self.manager.execute(PREFIX + "start", {"minutes": -1})
        self.assertEqual(item.status, "ready")
        self.assertTrue(self.manager.execute(PREFIX + "toggle", {})["ok"])

    def test_disable_and_crash_are_contained(self):
        item = self.activate()
        item.worker.process.kill()
        item.worker.process.wait(timeout=2)
        item.next_poll = 0
        self.manager.poll(item)
        self.assertEqual(item.status, "error")
        self.assertEqual(item.snapshot, {})
        dispatcher = Dispatcher(FakePlatform(), configuration(), self.manager)
        self.assertFalse(dispatcher.run(Action(PREFIX + "toggle")).ok)
        self.assertTrue(dispatcher.run(Action("volume.up")).ok)
        self.manager.restart(IDENTIFIER)
        self.manager.poll(item)
        self.assertEqual(item.status, "ready")
        self.manager.enable(IDENTIFIER, False)
        self.assertIsNone(item.worker)

    def test_timeout_kills_only_worker(self):
        (self.package / "hang.py").write_text("import time\ntime.sleep(60)\n")
        worker = Worker(
            self.package, {"runtime": "command", "command": [sys.executable, "hang.py"]}
        )
        self.addCleanup(worker.close)
        # Launch without the initial 5-second handshake for a fast timeout test.
        import subprocess

        worker.process = subprocess.Popen(
            [sys.executable, str(self.package / "hang.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        started = time.monotonic()
        with self.assertRaises(ExtensionError):
            worker.call("poll", {}, timeout=0.1)
        self.assertLess(time.monotonic() - started, 3)
        self.assertIsNone(worker.process)

    def test_command_runtime_and_graceful_shutdown(self):
        (self.package / "command.py").write_text(
            "import json, sys\nfrom pathlib import Path\n"
            "for line in sys.stdin:\n"
            " r=json.loads(line)\n"
            " if r['method']=='shutdown': Path('stopped').write_text('yes')\n"
            " print(json.dumps({'id':r['id'],'result':{'api_version':1}}),flush=True)\n",
            encoding="utf-8",
        )
        worker = Worker(
            self.package,
            {
                "id": "com.example.command",
                "runtime": "command",
                "command": [sys.executable, "command.py"],
            },
        )
        self.addCleanup(worker.close)
        worker.start({}, self.root / "data")
        worker.stop()
        self.assertEqual((self.package / "stopped").read_text(), "yes")

    def test_secret_redaction_and_corrupt_settings(self):
        path = self.package / "extension.json"
        manifest = json.loads(path.read_text())
        manifest["settings"].append({"name": "token", "type": "password"})
        path.write_text(json.dumps(manifest))
        self.install()
        self.manager.configure(IDENTIFIER, {"token": "TOP_SECRET"})
        self.manager.configure(IDENTIFIER, {"title": "New title"})
        description = self.manager.describe()
        self.assertNotIn("TOP_SECRET", json.dumps(description))
        self.assertEqual(description["extensions"][0]["secret_fields_set"], ["token"])
        settings_path = self.manager._settings_path(IDENTIFIER)
        if os.name != "nt":
            self.assertEqual(settings_path.stat().st_mode & 0o777, 0o600)
        settings_path.write_text("broken")
        self.assertTrue(self.manager.describe()["extensions"][0]["error"])

    def test_scaffold_packs_and_runs_without_repository_example(self):
        source = create(self.root / "starter", "com.example.counter")
        with self.assertRaises(ExtensionError):
            create(source, "com.example.counter")
        archive = self.root / "starter.3deckext"
        pack(source, archive)
        self.manager.install(archive)
        item = self.manager.items["com.example.counter"]
        self.manager.enable(item.manifest["id"], True, item.digest)
        self.manager.execute("ext:com.example.counter/increment", {"amount": 2})
        self.manager.poll(item)
        self.assertEqual(
            item.snapshot["dashboards"]["counter"]["cards"][0]["value"], "2"
        )
        self.manager.restart(item.manifest["id"])
        self.manager.poll(item)
        self.assertEqual(
            item.snapshot["dashboards"]["counter"]["cards"][0]["value"], "2"
        )


class OutputAndApiTests(ExtensionFixture):
    def test_console_socket_handshake_action_refresh_and_localization(self):
        import struct

        item = self.activate()
        server = Server(configuration(), FakePlatform())
        server.extensions = self.manager
        server.dispatcher.extensions = self.manager

        async def scenario():
            listener = await asyncio.start_server(server._handle_client, "127.0.0.1", 0)
            reader, writer = await asyncio.open_connection(
                "127.0.0.1", listener.sockets[0].getsockname()[1]
            )

            async def receive():
                header = await asyncio.wait_for(reader.readexactly(4), 3)
                return json.loads(
                    await asyncio.wait_for(
                        reader.readexactly(struct.unpack(">I", header)[0]), 3
                    )
                )

            async def send(message):
                writer.write(encode(message))
                await writer.drain()

            try:
                await send({"type": "hello", "protocol": 1, "language": "fr"})
                self.assertEqual((await receive())["type"], "hello.ok")
                self.assertEqual(
                    (await receive())["pages"][0]["dashboard"], "extension"
                )
                await server._refresh_state()
                state = await receive()
                self.assertEqual(
                    state["extension_panels"][0]["cards"][0]["label"], "Temps restant"
                )
                await send({"type": "config.request"})
                self.assertEqual((await receive())["type"], "config.snapshot")
                self.assertEqual(
                    (await receive())["extension_panels"][0]["cards"][0]["label"],
                    "Temps restant",
                )
                await send(
                    {
                        "type": "button.press",
                        "id": 7,
                        "page": "focus",
                        "button": "toggle",
                    }
                )
                self.assertTrue((await receive())["ok"])
                await asyncio.to_thread(self.manager.poll, item)
                await server._refresh_state()
                update = await receive()
                if update["type"] == "config.snapshot":
                    update = await receive()
                self.assertTrue(update["extension_buttons"][0]["active"])
                await send({"type": "ping", "id": 8})
                self.assertEqual((await receive())["type"], "pong")
            finally:
                writer.close()
                await writer.wait_closed()
                listener.close()
                await listener.wait_closed()
                for client in list(server.clients):
                    await client.close()

        asyncio.run(scenario())

    def test_large_twelve_page_sources_fit_wire_budget(self):
        import copy

        item = self.activate()
        entry = item.snapshot["sources"]["presets"][0]
        item.snapshot["sources"]["presets"] = [
            dict(
                entry,
                id=f"entry_{i:026d}",
                label={"en": "x" * 64, "fr": "é" * 64},
                detail={"en": "x" * 80, "fr": "é" * 80},
            )
            for i in range(32)
        ]
        config = configuration("list")
        original = config.pages[0]
        config.pages = [copy.deepcopy(original) for _ in range(12)]
        for i, page in enumerate(config.pages):
            page.id = f"page{i}"
        fill_sources(self.manager, config)
        payload = config_message(self.manager, config, "fr")
        self.assertLessEqual(len(encode(payload)), 60004)
        self.assertTrue(all(page["entries"] for page in payload["pages"]))
        state = localized_state(state_payload(self.manager, config), "fr")
        self.assertLess(len(encode(state)), 65540)

    def test_locale_named_arguments_are_not_translated(self):
        from deck3ds.extensions.bridge import source_entries

        item = self.activate()
        item.snapshot["sources"]["presets"][0]["action"]["arguments"] = {
            "en": "one",
            "fr": "two",
        }
        self.assertEqual(
            source_entries(self.manager, PREFIX + "presets", "fr")[0]["action"][
                "arguments"
            ],
            {"en": "one", "fr": "two"},
        )

    def test_malformed_worker_output_is_contained(self):
        for index, code in enumerate(
            (
                "print('not json', flush=True)",
                "print('x'*70000, flush=True)",
                'print(\'{"id":999,"result":{}}\', flush=True)',
            )
        ):
            path = self.package / f"bad{index}.py"
            path.write_text(code)
            worker = Worker(
                self.package,
                {
                    "id": "com.example.bad",
                    "runtime": "command",
                    "command": [sys.executable, str(path)],
                },
            )
            with self.subTest(code=code):
                try:
                    with self.assertRaises(ExtensionError):
                        worker.start({}, self.root / "data")
                finally:
                    worker.close()

    def test_invalid_output_is_rejected(self):
        manifest = load_manifest(self.package / "extension.json")
        for raw in (
            None,
            {"states": {"x": 1}},
            {"sources": {"unknown": []}},
            {"dashboards": {"timer": {"cards": [{}] * 5}}},
            {"sources": {"presets": [{"id": "a", "action": {"id": "not_declared"}}]}},
        ):
            with self.subTest(raw=raw), self.assertRaises(ExtensionError):
                normalize(manifest, raw)
        self.assertEqual(short("ééé", 5), "éé")

    def test_localization_and_preview_do_not_leak_action_args(self):
        self.activate()
        config = configuration()
        payload = localized_state(state_payload(self.manager, config), "fr")
        self.assertEqual(
            payload["extension_panels"][0]["cards"][0]["label"], "Temps restant"
        )
        self.assertNotIn("arguments", json.dumps(preview_payload(self.manager)))
        self.assertLess(len(encode(payload)), 65540)

    def test_api_schema_and_trust_boundary(self):
        self.install()
        platform = FakePlatform()
        platform.name = sys.platform
        server = Server(
            configuration(), platform, Options(config_path=self.root / "config.json")
        )
        server.extensions = self.manager
        api = Api(server)

        def request(raw):
            return Request("POST", "/api/extensions", {}, json.dumps(raw).encode())

        async def checks():
            schema = json.loads((await api.get_schema(request({}))).body)
            self.assertTrue(
                any(action["kind"] == PREFIX + "start" for action in schema["actions"])
            )
            with self.assertRaises(HttpError):
                await api.manage_extension(
                    request({"operation": "enable", "id": IDENTIFIER})
                )
            await api.manage_extension(
                request(
                    {
                        "operation": "enable",
                        "id": IDENTIFIER,
                        "trust": True,
                        "digest": self.manager.items[IDENTIFIER].digest,
                    }
                )
            )
            self.assertEqual(self.manager.items[IDENTIFIER].status, "ready")
            with self.assertRaises(HttpError):
                await api.manage_extension(
                    request({"operation": "remove", "id": IDENTIFIER})
                )

        asyncio.run(checks())


if __name__ == "__main__":
    unittest.main()
