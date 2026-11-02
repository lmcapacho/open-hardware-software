#!/usr/bin/env python3
"""Find maintained, end-user circuit-simulation applications for the catalog."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SEARCH_TOPICS = ("circuit-simulation", "eda")
SIMULATION_TERMS = ("simulator", "simulation")
EXCLUDED_TERMS = (
    "agent",
    "board",
    "bom",
    "component library",
    "compact model",
    "core",
    "firmware",
    "hardware description language",
    "mcp",
    "model-context-protocol",
    "plugin",
    "roadmap",
    "skill",
    "tutorial",
    "verilog-a",
)
MINIMUM_STARS = 10
MAXIMUM_CANDIDATES = 20
ACTIVE_WITHIN_DAYS = 540
USER_AGENT = "open-hardware-software-discovery/1.0"


def github_request(url: str, token: str | None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def catalog_repositories(catalog: list[dict]) -> set[str]:
    repositories = set()
    for tool in catalog:
        url = tool.get("repository_url", "").rstrip("/")
        if "github.com/" in url.lower():
            repositories.add(url.lower())
    return repositories


def search_topic(topic: str, token: str | None) -> list[dict]:
    query = f"topic:{topic} archived:false fork:false stars:>={MINIMUM_STARS}"
    url = "https://api.github.com/search/repositories?" + urlencode(
        {"q": query, "sort": "updated", "order": "desc", "per_page": 20}
    )
    response = github_request(url, token)
    return response.get("items", [])


def is_active(repository: dict, cutoff: dt.datetime) -> bool:
    pushed_at = repository.get("pushed_at")
    license_info = repository.get("license") or {}
    license_id = license_info.get("spdx_id")
    if not pushed_at or not license_id or license_id == "NOASSERTION":
        return False
    pushed_date = dt.datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
    return pushed_date >= cutoff


def is_relevant(repository: dict) -> bool:
    text = " ".join([repository.get("full_name", ""), repository.get("description") or ""]).casefold()
    return any(term in text for term in SIMULATION_TERMS) and not any(term in text for term in EXCLUDED_TERMS)


def latest_stable_release(repository: str, token: str | None) -> dict | None:
    try:
        release = github_request(f"https://api.github.com/repos/{repository}/releases/latest", token)
    except Exception:
        return None
    if release.get("prerelease") or not release.get("published_at"):
        return None
    return release


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("index.json"))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    existing = catalog_repositories(catalog)
    token = os.environ.get("GITHUB_TOKEN")
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=ACTIVE_WITHIN_DAYS)
    candidates: dict[str, dict] = {}
    errors = []

    for topic in SEARCH_TOPICS:
        try:
            repositories = search_topic(topic, token)
        except Exception as error:  # The report should preserve failures instead of aborting the workflow.
            errors.append({"topic": topic, "message": str(error)})
            continue
        for repository in repositories:
            html_url = repository["html_url"].rstrip("/")
            if html_url.lower() in existing or not is_active(repository, cutoff) or not is_relevant(repository):
                continue
            release = latest_stable_release(repository["full_name"], token)
            if release is None or release["published_at"][:10] < cutoff.date().isoformat():
                continue
            candidate = candidates.setdefault(
                html_url.lower(),
                {
                    "name": repository["full_name"],
                    "url": html_url,
                    "description": repository.get("description") or "No description provided.",
                    "license": repository["license"].get("spdx_id", "NOASSERTION"),
                    "stars": repository["stargazers_count"],
                    "pushed_at": repository["pushed_at"][:10],
                    "version": release["tag_name"],
                    "release_date": release["published_at"][:10],
                    "topics": set(),
                },
            )
            candidate["topics"].add(topic)

    ranked_candidates = sorted(candidates.values(), key=lambda item: (-item["stars"], item["name"].casefold()))
    for candidate in ranked_candidates:
        candidate["topics"] = sorted(candidate["topics"])

    report = {
        "tool_count": len(catalog),
        "minimum_stars": MINIMUM_STARS,
        "active_within_days": ACTIVE_WITHIN_DAYS,
        "candidates": ranked_candidates[:MAXIMUM_CANDIDATES],
        "errors": errors,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Found {len(report['candidates'])} candidate(s) from {len(SEARCH_TOPICS)} topic searches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
