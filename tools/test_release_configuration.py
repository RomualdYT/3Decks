"""Fast checks for release configuration before compiling installers."""

import base64
import json
import plistlib
import tempfile
import unittest
from pathlib import Path

from check_release_version import check_tauri_versions
from prepare_desktop_release import TEMPLATE, prepare


class ReleaseConfigurationTests(unittest.TestCase):
    PUBLIC_KEY = base64.b64encode(
        b"untrusted comment: minisign public key\n" + base64.b64encode(b"Ed" + bytes(40)) + b"\n"
    ).decode()

    def test_macos_bundle_can_request_media_automation(self):
        desktop = Path(__file__).resolve().parents[1] / "apps/desktop/src-tauri"
        config = json.loads((desktop / "tauri.conf.json").read_text())
        macos = config["bundle"]["macOS"]
        entitlements = plistlib.loads((desktop / macos["entitlements"]).read_bytes())
        self.assertIs(entitlements["com.apple.security.automation.apple-events"], True)
        info = plistlib.loads((desktop / macos["infoPlist"]).read_bytes())
        self.assertTrue(info["NSAppleEventsUsageDescription"].strip())

    def test_prepares_updater_overlay_without_changing_template(self):
        original = TEMPLATE.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "release.json"
            prepare(output, f"  {self.PUBLIC_KEY}\n")
            config = json.loads(output.read_text())
            self.assertTrue(config["bundle"]["createUpdaterArtifacts"])
            self.assertEqual(config["plugins"]["updater"]["pubkey"], self.PUBLIC_KEY)
            self.assertNotIn("privateKey", config["plugins"]["updater"])
        self.assertEqual(TEMPLATE.read_bytes(), original)

    def test_rejects_missing_public_key_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "release.json"
            with self.assertRaisesRegex(ValueError, "Missing updater public key"):
                prepare(output, " \n")
            self.assertFalse(output.exists())

    def test_accepts_matching_minor_versions_with_different_patches(self):
        check_tauri_versions(self.npm_lock(), self.cargo_lock("2.12.0", "2.8.0"))

    def test_rejects_malformed_public_key_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "release.json"
            with self.assertRaisesRegex(ValueError, "Invalid updater public key"):
                prepare(output, "not-a-public-key")
            self.assertFalse(output.exists())

    def test_rejects_api_minor_mismatch(self):
        with self.assertRaisesRegex(ValueError, "Tauri version mismatch.*api"):
            check_tauri_versions(self.npm_lock(), self.cargo_lock("2.11.1", "2.8.1"))

    def test_rejects_plugin_minor_mismatch(self):
        with self.assertRaisesRegex(ValueError, "Tauri version mismatch.*plugin-dialog"):
            check_tauri_versions(self.npm_lock(), self.cargo_lock("2.12.1", "2.7.3"))

    def test_rejects_missing_rust_plugin(self):
        with self.assertRaisesRegex(ValueError, "tauri-plugin-dialog missing"):
            check_tauri_versions(self.npm_lock(), {"package": [{"name": "tauri", "version": "2.12.1"}]})

    @staticmethod
    def npm_lock():
        return {"packages": {
            "": {"dependencies": {"@tauri-apps/api": "^2.12.1", "@tauri-apps/plugin-dialog": "^2.8.1"}},
            "node_modules/@tauri-apps/api": {"version": "2.12.1"},
            "node_modules/@tauri-apps/plugin-dialog": {"version": "2.8.1"},
        }}

    @staticmethod
    def cargo_lock(api, dialog):
        return {"package": [
            {"name": "tauri", "version": api},
            {"name": "tauri-plugin-dialog", "version": dialog},
        ]}


if __name__ == "__main__":
    unittest.main()
