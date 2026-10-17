#!/usr/bin/env python3
"""Find catalog entries whose latest GitHub release differs from the recorded version."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


GITHUB_REPOSITORY = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/#?]+)", re.IGNORECASE)
VERSION_IN_TAG = re.compile(r"\d+(?:[._-]\d+)+")
NON_RELEASE_TAGS = {"continuous", "continuous_build", "latest", "nightly"}
USER_AGENT = "open-hardware-software-release-checker/1.0"


def github_repository(url: str) -> tuple[str, str] | None:
    match = GITHUB_REPOSITORY.match(url)
    if not match:
        return None
    return match.group(1), match.group(2).removesuffix(".git")


def request_json(url: str, token: str | None) -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def latest_release(owner: str, repository: str, token: str | None) -> dict | None:
    url = f"https://api.github.com/repos/{owner}/{repository}/releases/latest"
    try:
        release = request_json(url, token)
    except HTTPError as error:
        if error.code == 404:
            return None
        raise
    return release if isinstance(release, dict) else None


def normalize_version(value: str) -> str:
    """Compare version tags despite common prefixes and separator choices."""
    match = VERSION_IN_TAG.search(value)
    if match:
        return re.sub(r"[._-]", ".", match.group()).lower()
    return value.lower().lstrip("v")


def is_reviewable_release(release: dict, recorded_release_date: str) -> bool:
    tag = release.get("tag_name", "").lower()
    published_at = release.get("published_at", "")
    return (
        not release.get("prerelease")
        and tag not in NON_RELEASE_TAGS
        and not tag.startswith("weekly-")
        and published_at[:10] > recorded_release_date
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("index.json"))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    token = os.environ.get("GITHUB_TOKEN")
    updates, errors, checked = [], [], 0

    for tool in catalog:
        repository = github_repository(tool.get("repository_url", ""))
        if not repository:
            continue
        owner, name = repository
        checked += 1
        try:
            release = latest_release(owner, name, token)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            errors.append({"tool": tool["name"], "repository": f"{owner}/{name}", "message": str(error)})
            continue
        if release is None:
            continue

        tag = release.get("tag_name", "")
        recorded_version = tool["version"]
        if is_reviewable_release(release, tool["release_date"]) and normalize_version(tag) != normalize_version(recorded_version):
            updates.append(
                {
                    "tool": tool["name"],
                    "recorded_version": recorded_version,
                    "latest_version": tag,
                    "published_at": release["published_at"][:10],
                    "url": release.get("html_url", f"https://github.com/{owner}/{name}/releases"),
                }
            )

    report = {"has_updates": bool(updates), "tool_count": len(catalog), "checked_repositories": checked, "updates": sorted(updates, key=lambda item: item["tool"].casefold()), "errors": errors}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {checked} GitHub repositories; found {len(updates)} update(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
