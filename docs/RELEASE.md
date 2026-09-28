# Release process

The active GitHub Actions workflows are [Quality](../.github/workflows/quality.yml), [Release candidate](../.github/workflows/release.yml) and [Publish qualified release](../.github/workflows/publish-release.yml). They package **Tauri and the 3DS app**. A `vX.Y.Z` tag runs the full quality suite, then builds macOS Apple Silicon, macOS Intel and Windows x64 sequentially so their updater entries merge into one `latest.json`. It attaches the 3DS `.3dsx` and `.cia`, validates all expected platforms and files, generates SHA-256 checksums, and leaves the GitHub Release **as a draft**.

This pipeline is implemented but has **not** yet completed a signed, multi-platform release. Configure the secrets below and qualify the Windows installer and updater before treating it as production ready. Pushing `main` runs quality checks, but does not publish a version.

## One-time repository setup

1. Generate a Tauri updater key pair with `cd desktop && npm run tauri signer generate -- -w /safe/location/3decks.key` (see [Tauri updater signing](https://v2.tauri.app/plugin/updater/#signing-updates)). Store the **private** key as GitHub Actions secret `TAURI_SIGNING_PRIVATE_KEY` and its password, if used, as `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`. Store the public key content as repository variable `DECKS_UPDATER_PUBKEY`. Never commit the private key.
2. Add macOS Developer ID Application `.p12` as base64 secret `APPLE_CERTIFICATE`, plus `APPLE_CERTIFICATE_PASSWORD`, `APPLE_ID`, `APPLE_PASSWORD` (an app-specific password), and `APPLE_TEAM_ID`. `APPLE_SIGNING_IDENTITY` is optional when Tauri can infer it from the certificate. Confirm both architectures are signed and notarized before publication.
3. Add the Windows Authenticode `.pfx` as base64 secret `WINDOWS_CERTIFICATE` and its export password as `WINDOWS_CERTIFICATE_PASSWORD`. The workflow imports it into the runner certificate store and supplies its thumbprint to Tauri. Confirm the installer signature and timestamp on a real Windows machine.
4. Allow GitHub Actions to create Releases (`contents: write`). Protect release tags. Configure a protected `production` environment with required reviewers for the publish workflow.

The release workflow intentionally fails early if required signing material is missing. The updater public key is embedded at compile time; adding it later cannot make an already built binary update-capable. Tauri generates updater bundles and `.sig` files only for release builds via `desktop/src-tauri/tauri.release.conf.json`.

## Prepare a candidate

1. Update all three desktop versions: `desktop/package.json`, `desktop/src-tauri/Cargo.toml`, `desktop/src-tauri/tauri.conf.json`. Refresh `desktop/package-lock.json` and `desktop/src-tauri/Cargo.lock` if needed. The tag validator rejects mismatches.
2. Run local frontend, Rust and console tests. Review the platform matrix and the [Windows test plan](../desktop/docs/WINDOWS_TEST_PLAN.md). Build and test an installable candidate on both operating systems.
3. Commit and push the version change, then create and push the annotated tag `vX.Y.Z`. Tagging is the explicit trigger; pushing `main` alone never creates a release.
4. Inspect the draft: binaries, signing/notarization, `latest.json`, checksum manifest and actual install/update behavior. Test a real 3DS or Citra with the packaged version. After the gates pass, run **Publish qualified release** with the tag. The workflow rechecks assets and checksums, then publishes the draft after environment approval.

The updater uses `https://github.com/RomualdYT/3Decks/releases/latest/download/latest.json`. The user starts a check from **Settings → Advanced → Updates**; there is no background update check yet. A draft is invisible to regular clients; publication makes this version eligible for updates. Do not publish a draft with failed jobs, unsigned installers, invalid updater signatures or unverified Windows behavior. Linux packaging is deferred until its native feature and platform validation are complete. The first direct Windows installer will not provide the packaged identity required for notification history.

For local unsigned UI tests, use `npm run tauri -- build --bundles dmg --no-sign --ci` from `desktop/`; these builds have no updater artifacts and are not distribution releases.
