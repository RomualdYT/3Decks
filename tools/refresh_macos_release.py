"""Maintain an existing draft by its stable ID (draft tags may be provisional)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        redirected = super().redirect_request(request, response, code, message, headers, url)
        if urlsplit(url).hostname not in {"api.github.com", "uploads.github.com"}:
            redirected.remove_header("Authorization")
        return redirected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "download", "upload", "notes"])
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    repository = os.environ["GITHUB_REPOSITORY"]
    tag = os.environ["RELEASE_TAG"]
    release_id = os.environ["RELEASE_ID"]
    if not release_id.isdigit():
        raise ValueError("Release ID must be numeric")
    base = f"https://api.github.com/repos/{repository}"
    opener = build_opener(PublicRedirect())

    def request(url, data=None, method=None, accept="application/vnd.github+json"):
        headers = {
            "Authorization": "Bearer " + os.environ["GH_TOKEN"],
            "User-Agent": "3Decks-release-maintenance",
            "Accept": accept,
        }
        if data is not None:
            headers["Content-Type"] = "application/octet-stream" if isinstance(data, bytes) else "application/json"
            if not isinstance(data, bytes):
                data = json.dumps(data).encode()
        with opener.open(Request(url, data=data, method=method, headers=headers), timeout=120) as response:
            return response.read()

    release_url = f"{base}/releases/{release_id}"
    release = json.loads(request(release_url))
    if not release["draft"]:
        raise ValueError("Only an existing draft may be refreshed")
    if release["tag_name"] != tag and release["name"] != f"3Decks {tag}":
        raise ValueError("Release name does not match the requested version")
    request(f"{base}/git/ref/tags/{quote(tag, safe='')}")

    if args.command == "validate":
        print(f"Validated existing draft {release_id}: {release['name']}")
    elif args.command == "download":
        destination, = args.paths
        destination.mkdir()
        for asset in release["assets"]:
            if Path(asset["name"]).name != asset["name"]:
                raise ValueError("Unsafe release asset name")
            (destination / asset["name"]).write_bytes(request(asset["url"], accept="application/octet-stream"))
        print(f"Downloaded {len(release['assets'])} original assets")
    elif args.command == "upload":
        replacements, metadata = args.paths
        version = tag.removeprefix("v")
        expected = {
            f"3Decks_{version}_{arch}{suffix}"
            for arch in ("aarch64", "x64")
            for suffix in (".dmg", ".app.tar.gz", ".app.tar.gz.sig")
        }
        packages = {path.name: path for path in replacements.iterdir() if path.is_file()}
        if packages.keys() != expected:
            raise ValueError("Expected exactly the six macOS replacement assets")
        packages.update({name: metadata / name for name in ("latest.json", "SHA256SUMS.txt")})
        existing = {asset["name"]: asset for asset in release["assets"]}
        upload_url = release["upload_url"].split("{", 1)[0]
        for name, path in packages.items():
            content = path.read_bytes()
            if name in existing:
                request(existing[name]["url"], method="DELETE")
            request(upload_url + "?name=" + quote(name, safe=""), data=content, method="POST")
            print(f"Replaced {name}")
    else:
        body = release["body"] or ""
        body += ("\n\n### macOS package refresh\n\n"
                 f"The Apple Silicon and Intel packages were rebuilt from commit `{os.environ['GITHUB_SHA']}` "
                 "to restore media automation and correct notification access diagnostics. "
                 "Windows and Nintendo 3DS packages are unchanged.\n")
        request(release_url, data={"body": body}, method="PATCH")
        print("Recorded macOS build provenance")


if __name__ == "__main__":
    main()
