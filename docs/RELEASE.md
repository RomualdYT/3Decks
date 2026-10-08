# Release process

The active GitHub Actions workflows are [Quality](../.github/workflows/quality.yml), [Release candidate](../.github/workflows/release.yml) and [Publish qualified release](../.github/workflows/publish-release.yml). They package **Tauri and the 3DS app**. A `vX.Y.Z` tag runs the full quality suite, then builds macOS Apple Silicon, macOS Intel and Windows x64 sequentially so their updater entries merge into one `latest.json`. It attaches the 3DS `.3dsx` and `.cia`, validates all expected platforms and files, generates SHA-256 checksums, and leaves the GitHub Release **as a draft**.

macOS packages use ad-hoc signing, without Apple Developer membership or notarization. Windows installers have no Authenticode signature. Configure the updater keys below, then qualify the installers and updater before publishing a candidate. Pushes to `main` and pull requests run lightweight Linux checks, but do not publish a version.

## CI and build consumption

- **Pushes and pull requests:** documentation checks always run. Editor changes also run frontend checks and a webview build; console changes run host tests on Linux. Markdown-only edits do not trigger compilation. Superseded runs are cancelled.
- **Release tags:** run the complete quality suite, including native Rust tests on macOS/Windows, console host tests on Linux/macOS, 3DS packaging, and Focus packaging on Linux/macOS/Windows. Updater keys are checked before these jobs start.
- **Manual qualification:** run **Quality** from the Actions tab with `full` enabled to validate any branch before tagging.
- **Temporary packages:** Actions artifacts are retained for seven days. Files attached to a GitHub Release are independent of that retention period.

Native Rust and extension changes are qualified automatically at release time; run their local checks or manual full qualification for earlier feedback. The lightweight and full checks share one workflow to keep their commands consistent.

Official builds include the public 3Decks Twitch Client ID. Forks distributed as a different application must set repository variable `DECKS_TWITCH_CLIENT_ID` to their own Public Twitch application Client ID. No Client Secret is required. See [stream chat](STREAM_CHAT.md).

## One-time repository setup

1. Generate a Tauri updater key pair with `cd apps/desktop && npm run tauri -- signer generate -w /safe/location/3decks.key` (see [Tauri updater signing](https://v2.tauri.app/plugin/updater/#signing-updates)). Store the **private** key as GitHub Actions secret `TAURI_SIGNING_PRIVATE_KEY` and its password, if used, as `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`. Store the public key content as repository variable `DECKS_UPDATER_PUBKEY`. Never commit the private key.
2. Allow GitHub Actions to create Releases (`contents: write`). Protect release tags. Configure required reviewers on the `production` environment for the publish workflow. An environment with no protection rules does not require an approval.

No Apple or Windows code-signing certificates or secrets are needed. `bundle.macOS.signingIdentity` is `"-"` in the shared Tauri configuration, so local and release bundles use ad-hoc signing. The release workflow fails early if updater keys are missing or JavaScript/Rust Tauri versions disagree. Before bundling, `tools/prepare_desktop_release.py` injects the public key into `plugins.updater` in the release overlay. The same key is embedded at compile time; adding it later cannot make an already built binary update-capable. Tauri generates updater bundles and `.sig` files only for release builds via `apps/desktop/src-tauri/tauri.release.conf.json`.

## Prepare a candidate

1. Update all three desktop versions: `apps/desktop/package.json`, `apps/desktop/src-tauri/Cargo.toml`, `apps/desktop/src-tauri/tauri.conf.json`. Refresh `apps/desktop/package-lock.json` and `apps/desktop/src-tauri/Cargo.lock` if needed. The tag validator rejects mismatches.
2. Run local frontend, Rust and console tests. Review the platform matrix and the [Windows test plan](../apps/desktop/docs/WINDOWS_TEST_PLAN.md). Build and test an installable candidate on both operating systems, following [qualification](QUALIFICATION.md).
3. Commit and push the version change, then create and push the annotated tag `vX.Y.Z`. Tagging is the explicit trigger; pushing `main` alone never creates a release.
4. Inspect the draft: binaries, macOS first-launch approval, Windows installation warnings, `latest.json`, checksum manifest and actual install/update behavior. Test a real 3DS or Citra with the packaged version. After the gates pass, run **Publish qualified release** with the tag. The workflow rechecks assets and checksums, then publishes the draft. GitHub requests environment approval only when required reviewers have been configured.

The updater uses `https://github.com/RomualdYT/3Decks/releases/latest/download/latest.json`. A configured editor checks after opening; users can also check from **Settings → Advanced → Updates**. Installation requires an explicit click. A draft is invisible to regular clients; publication makes this version eligible for updates. Do not publish a draft with failed jobs, invalid updater signatures or unverified Windows behavior. Linux packaging is deferred until its native feature and platform validation are complete. The configured direct Windows installer does not provide the package identity required for notification history.

For a local DMG, use `npm run tauri -- build --bundles dmg` from `apps/desktop/`; the base configuration does not generate updater artifacts. macOS Gatekeeper approval and Keychain prompts after updates are documented in [installation](INSTALLATION.md#first-launch-on-macos). Ad-hoc signing is separate from the mandatory Tauri updater signature. See [Tauri ad-hoc signing](https://v2.tauri.app/distribute/sign/macos/#ad-hoc-signing).
