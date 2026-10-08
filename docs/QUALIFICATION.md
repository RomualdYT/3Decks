# Release qualification

[Documentation](README.md) · [Français](QUALIFICATION.fr.md)

Before publishing a release, install its packages on macOS Intel/Apple Silicon
and Windows x64. Record actual OS versions, hardware, package versions and results.

- Check macOS ad-hoc signatures, first-launch approval through Privacy & Security, Windows installation warnings and checksums. Windows Authenticode and Apple notarization are not expected.
- Check first launch, setup, saved language/preferences, tray and window lifecycle.
- Check permissions, media, audio, available notifications, OBS and shortcuts.
- Pair a real console; check pages, reconnect, sleep/wake and action feedback.
- Import Focus and check its source/dashboard, timer persistence and localization.
- Check `latest.json` against packages and their Tauri updater signatures. When an earlier release
  exists, install an update from it and verify data retention and restart.

Keep unresolved failures in the draft release notes; publish only after the
checks pass. See [Release process](RELEASE.md),
[Windows checks](../apps/desktop/docs/WINDOWS_TEST_PLAN.md),
[macOS checks](../apps/desktop/docs/MACOS_TRAY_AND_SHORTCUTS_TEST.md) and
[performance measurement](PERFORMANCE.md).
