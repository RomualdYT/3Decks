"""Regression checks on actual build artifacts; run after ./build.sh all."""
import importlib.util
import unittest
from unittest.mock import patch

import check_console_package as package


class ConsolePackagingTests(unittest.TestCase):
    def test_current_package(self):
        package.check_cia((package.APP / "deck3ds.cia").read_bytes())

    def test_truncated_cia(self):
        with self.assertRaisesRegex(ValueError, "Truncated"):
            package.check_cia((package.APP / "deck3ds.cia").read_bytes()[:0x2040])

    def test_wrong_cia_header(self):
        data = bytearray((package.APP / "deck3ds.cia").read_bytes())
        data[0] ^= 1
        with self.assertRaisesRegex(ValueError, "CIA header"):
            package.check_cia(data)

    @staticmethod
    def cia_content_offset(data):
        offset = package.align64(package.u32(data, 0))
        for field in (8, 12, 16):
            offset = package.align64(offset + package.u32(data, field))
        return offset

    def test_wrong_title(self):
        data = bytearray((package.APP / "deck3ds.cia").read_bytes())
        ncch = self.cia_content_offset(data)
        data[ncch + 0x118] ^= 1
        with self.assertRaisesRegex(ValueError, "title ID"):
            package.check_cia(data)

    def test_corrupt_exefs(self):
        data = bytearray((package.APP / "deck3ds.cia").read_bytes())
        ncch = self.cia_content_offset(data)
        exefs = ncch + package.u32(data, ncch + 0x1A0) * 512
        data[exefs + 512] ^= 1
        with self.assertRaisesRegex(ValueError, "hash"):
            package.check_cia(data)

    def test_missing_kernel_permission(self):
        with patch.object(package.subprocess, "check_output", return_value="svc 0x7b"):
            with self.assertRaisesRegex(ValueError, "Missing kernel permissions"):
                package.check_syscalls("objdump")

    def test_release_version(self):
        spec = importlib.util.spec_from_file_location(
            "package_version", package.ROOT / "apps/console/packaging/package_version.py")
        version = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(version)
        self.assertEqual(version.encode("v1.2.3"), 1059)
        for tag in ("v1.0.16", "v64.0.0", "v0.64.0", "v1.0.0-beta", "main"):
            with self.assertRaises(ValueError):
                version.encode(tag)
