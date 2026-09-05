# Release qualification

[Documentation](README.md) · [Français](QUALIFICATION.fr.md) · [Tests](TESTING.md) · [Publishing](PUBLIC_RELEASE.md)

Use this checklist for each release candidate. Record the commit, artifact, OS and interpreter used. Passing simulated tests is not proof that native permissions or hardware work.

## Automated gate

Run the [test commands](TESTING.md) and the full remote Linux/macOS/Windows × Python 3.12–3.14 matrix. Require the configured coverage gate, static checks, generated-contract checks, frontend and console builds, and isolated wheel installation to pass.

The wheel check exercises packaged assets and CLI/HTTP/TCP/extension behavior outside the checkout. OS integrations in portable tests use controlled providers; they must not ask for personal permissions or operate a real console.

Retain the CI report and artifacts for the candidate. Report actual outcomes in release notes, rather than keeping transient test counts in user documentation.

## Native checklist

- [ ] Install the published-format artifact on macOS and Windows.
- [ ] Open every editor view; check fonts, console image, responsive layout and keyboard navigation.
- [ ] Create, reorder, save and reload pages/buttons. Test shortcut capture and explicit concurrent-edit conflicts.
- [ ] Verify menu appearance, connection status, media preference retention and quick settings.
- [ ] Verify macOS Automation, Accessibility and notification permissions with the distributed executable, including denial and later approval.
- [ ] Test Windows native actions, media and dialogs; test notification denial/approval with the intended MSIX identity.
- [ ] Test Spotify/Music as supported, file/folder selection and real OBS without affecting a live stream.
- [ ] Use a physical 3DS: discovery, manual connection, pairing/revocation, FR/EN, actions, sleep/wake and reconnection.
- [ ] Import, review, enable, configure, restart and remove an extension; verify native cards and generated lists.
- [ ] Stop while saving, while a dialog is open and while an extension is slow; inspect remaining processes/sockets.
- [ ] Test second launch, launch at login, restart, update, uninstall and rollback with backed-up data.
- [ ] Measure idle usage and a suitable [endurance scenario](PERFORMANCE.md).

## Release evidence

Distinguish automated results, manual native results and outstanding checks. Do not claim Windows/MSIX qualification from a Mac run, actual 3DS performance from loopback, or multi-hour stability from a short test.

Review screenshots/log excerpts for private data before attaching them. Dependency audits must be run for the candidate; an earlier clean result is not a permanent security guarantee. Store packaging is not proof of a published or accepted Store submission.
