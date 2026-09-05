# Release procedure

[Documentation](README.md) · [Français](PUBLIC_RELEASE.fr.md) · [Qualification evidence](QUALIFICATION.md)

This is a maintainer checklist, not a statement that a release or Store listing already exists.

## 1. Prepare the source

- Review the complete diff, including generated assets and ignored personal data.
- Keep the tracked demo configuration neutral; never publish pairing registries, real settings or logs.
- Update `agent/backend/deck3ds/version.py`. The release tag must match the wheel version.
- Update English documentation and its French companions. Verify local links.
- Back up your own configuration directory separately from release artifacts.

From the repository root:

```sh
python3 tools/check_docs.py
```

From `agent/`:

```sh
uv sync --locked
uv run --locked python tools/audit_public_config.py --history
uv run --locked ruff check backend/deck3ds deck3ds tests tools
uv run --locked mypy
uv run --locked pytest --cov --cov-report=term-missing
uv run --locked python -m deck3ds.api.export --check ../docs/api/openapi.json
pnpm install --frozen-lockfile
pnpm api:check
pnpm typecheck
pnpm test:frontend
pnpm build
uv build
uv run --locked python tools/qualify_wheel.py
```

Build the console with `./build.sh` from the root. Run the [native checklist](QUALIFICATION.md) on both target operating systems before declaring a release qualified.

The public-config checker only checks selected credential fields and personal paths in `agent/config.json` and, optionally, its locally reachable history. Fetch complete history for that mode. It never prints values. **Audit the rest of the repository/history separately**; this is not a comprehensive secret scan. Rotate exposed credentials before any history cleanup.

## 2. Publish on GitHub

After review and native qualification, create and push the matching version tag intentionally. A `vMAJOR.MINOR.PATCH` tag triggers `Release`; merely building locally does not publish.

The reusable `Quality` workflow gates the release agent job. It builds the frontend/wheel and runs the Linux/macOS/Windows × Python 3.12–3.14 matrix, contract checks, installed-package smoke tests and console build. The release workflow renders launchers, checks tag/wheel consistency and publishes only after its required jobs succeed.

Expected assets include the wheel, source archive, macOS/Windows launchers, icons, console `.3dsx` and `SHA256SUMS.txt`. Check that the README installation URLs resolve against the resulting Release. A checksum is not a signing certificate.

Launchers use the same wheel, prepare private Python through uv and preserve user data. They request graceful shutdown before update/removal; timeout aborts replacement. An older agent may need manual Quit.

## 3. Optional Store submission

The workflow is prepared; there is no implied published Store listing.

1. Reserve the real application identity in Partner Center.
2. Run **Windows Store package** for an already-published release tag.
3. Enter the exact package name, publisher identity and publisher display name.
4. Download the unsigned `windows-store-submission-*` artifact.
5. Submit it through Partner Center and complete the required review/identity steps.

**Do not distribute the unsigned MSIX directly to users.** Accepted Store distribution supplies the signing/identity boundary; local Python installation does not. Verify launch, updates, uninstall, notification consent/refusal, native dialogs, media, OBS and extensions on Windows. No SQLite notification fallback may be added to mask missing identity.

## 4. Rollback and release evidence

Retain the previous release and backups. Stop the current agent, reinstall the previously qualified artifact and use the same selected config path. There is no legacy HTTP fallback. An extension may have changed its own data format, so retain its data backup too.

Attach the actual CI outcome and native qualification scope to release notes. Do not turn simulated tests, historical dependency audits or a short loopback benchmark into claims of universal compatibility or long-term endurance.
