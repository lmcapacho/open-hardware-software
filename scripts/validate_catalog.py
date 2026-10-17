#!/usr/bin/env python3
"""Validate the catalog structure and the public URLs referenced by each tool."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REQUIRED_FIELDS = {
    "name": str,
    "slug": str,
    "description": str,
    "version": str,
    "release_date": str,
    "platforms": list,
    "license": str,
    "license_url": str,
    "category": str,
    "website": str,
    "download_url": str,
    "repository_url": str,
    "documentation_url": str,
    "screenshot_url": str,
    "logo_url": str,
    "tags": list,
    "language": list,
    "status": str,
    "features": list,
}
URL_FIELDS = (
    "license_url",
    "website",
    "download_url",
    "repository_url",
    "documentation_url",
    "screenshot_url",
    "logo_url",
)
URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
LOCAL_SCREENSHOT_PREFIX = "assets/"
USER_AGENT = "open-hardware-software-catalog-validator/1.0"


def load_catalog(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)
    if not isinstance(catalog, list):
        raise ValueError("The catalog root must be a JSON array.")
    return catalog


def is_local_screenshot(value: str) -> bool:
    return value.startswith(LOCAL_SCREENSHOT_PREFIX) and ".." not in Path(value).parts


def validate_structure(catalog: list[dict], repository_root: Path) -> list[dict]:
    issues = []
    slugs: dict[str, int] = {}
    names: dict[str, int] = {}

    for index, tool in enumerate(catalog, start=1):
        reference = tool.get("name", f"entry #{index}") if isinstance(tool, dict) else f"entry #{index}"
        if not isinstance(tool, dict):
            issues.append({"tool": reference, "field": "entry", "message": "must be an object"})
            continue

        for field, expected_type in REQUIRED_FIELDS.items():
            value = tool.get(field)
            if not isinstance(value, expected_type) or (isinstance(value, (str, list)) and not value):
                issues.append(
                    {"tool": reference, "field": field, "message": f"must be a non-empty {expected_type.__name__}"}
                )

        slug = tool.get("slug")
        if isinstance(slug, str) and slug:
            normalized_slug = slug.lower()
            if normalized_slug in slugs:
                issues.append({"tool": reference, "field": "slug", "message": f"duplicates entry #{slugs[normalized_slug]}"})
            else:
                slugs[normalized_slug] = index

        name = tool.get("name")
        if isinstance(name, str) and name:
            normalized_name = name.casefold()
            if normalized_name in names:
                issues.append({"tool": reference, "field": "name", "message": f"duplicates entry #{names[normalized_name]}"})
            else:
                names[normalized_name] = index

        release_date = tool.get("release_date")
        if isinstance(release_date, str):
            try:
                parsed_date = dt.date.fromisoformat(release_date)
                if parsed_date > dt.date.today():
                    issues.append({"tool": reference, "field": "release_date", "message": "cannot be in the future"})
            except ValueError:
                issues.append({"tool": reference, "field": "release_date", "message": "must use YYYY-MM-DD"})

        for field in URL_FIELDS:
            value = tool.get(field)
            if not isinstance(value, str) or not value:
                continue
            if field == "screenshot_url" and is_local_screenshot(value):
                if not (repository_root / "docs" / value).is_file():
                    issues.append({"tool": reference, "field": field, "message": "local screenshot file does not exist"})
            elif not URL_PATTERN.match(value):
                issues.append({"tool": reference, "field": field, "message": "must use an HTTP(S) URL or a local docs/assets path"})

    return issues


def check_url(url: str, timeout: int) -> tuple[bool, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
    try:
        with urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 400, f"HTTP {response.status}"
    except HTTPError as error:
        # Several valid hosts reject HEAD requests; retry with a small GET request.
        if error.code not in {403, 405, 501}:
            return False, f"HTTP {error.code}"
    except (URLError, TimeoutError) as error:
        return False, str(error.reason if isinstance(error, URLError) else error)

    request = Request(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 400, f"HTTP {response.status}"
    except HTTPError as error:
        return False, f"HTTP {error.code}"
    except (URLError, TimeoutError) as error:
        return False, str(error.reason if isinstance(error, URLError) else error)


def validate_urls(catalog: list[dict], timeout: int) -> list[dict]:
    checks = [
        (tool.get("name", "[unknown]"), field, tool[field])
        for tool in catalog
        if isinstance(tool, dict)
        for field in URL_FIELDS
        if isinstance(tool.get(field), str) and URL_PATTERN.match(tool[field])
    ]
    issues = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(check_url, url, timeout): (tool, field, url) for tool, field, url in checks}
        for future in concurrent.futures.as_completed(futures):
            tool, field, url = futures[future]
            valid, result = future.result()
            if not valid:
                issues.append({"tool": tool, "field": field, "message": result, "url": url})
    return sorted(issues, key=lambda issue: (issue["tool"].casefold(), issue["field"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("index.json"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--skip-links", action="store_true", help="Skip live URL checks.")
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    try:
        catalog = load_catalog(args.catalog)
        structural_issues = validate_structure(catalog, args.catalog.resolve().parent)
        link_issues = [] if args.skip_links else validate_urls(catalog, args.timeout)
        report = {
            "has_errors": bool(structural_issues or link_issues),
            "tool_count": len(catalog),
            "structural_issues": structural_issues,
            "link_issues": link_issues,
        }
    except (OSError, ValueError, json.JSONDecodeError) as error:
        report = {"has_errors": True, "tool_count": 0, "structural_issues": [{"tool": "catalog", "field": "index.json", "message": str(error)}], "link_issues": []}

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Validated {report['tool_count']} tools; found {len(report['structural_issues']) + len(report['link_issues'])} issue(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
