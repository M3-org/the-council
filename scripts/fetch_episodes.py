#!/usr/bin/env python3
"""
Fetch JedAI Council episodes from Shmotime API and update list.txt.

This script:
1. Fetches all episodes from the Shmotime API
2. Generates proper URL slugs from episode names
3. Cross-references with existing list.txt
4. Outputs new episodes that need dates assigned

Requires: pip install requests python-dotenv
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library required. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    # dotenv is optional - will use env vars directly
    load_dotenv = lambda: None

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Constants
API_URL = "https://shmotime.com/wp-json/shmotime/v1/get-show-by-id"
BASE_URL = "https://shmotime.com/shmotime_episode/"
LIST_FILE = PROJECT_ROOT / "list.txt"
SHOW_ID = "crypto_jedi"


def slugify(name: str) -> str:
    """Convert episode name to WordPress-style URL slug."""
    import html
    # Decode HTML entities first
    slug = html.unescape(name)
    slug = slug.lower()
    # Remove apostrophes and special quotes
    slug = re.sub(r"[''']", "", slug)
    # Replace colons
    slug = re.sub(r"[:]", "", slug)
    # Replace ampersands with nothing (WordPress drops them)
    slug = re.sub(r"[&]", "", slug)
    # Remove remaining non-alphanumeric except spaces and hyphens
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    # Replace spaces with hyphens
    slug = re.sub(r"\s+", "-", slug)
    # Remove consecutive hyphens
    slug = re.sub(r"-+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    return slug


def fetch_episodes() -> list[dict]:
    """Fetch episodes from Shmotime API."""
    passcode = os.getenv("WORDPRESS_PASSCODE", "")

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Accept": "application/json",
    }

    params = {"id": SHOW_ID}
    if passcode:
        params["passcode"] = passcode

    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("episodes", [])
    except requests.RequestException as e:
        print(f"Error fetching episodes: {e}", file=sys.stderr)
        sys.exit(1)


def load_existing_list() -> dict[str, str]:
    """Load existing list.txt and return {slug: date} mapping."""
    existing = {}
    if LIST_FILE.exists():
        for line in LIST_FILE.read_text().splitlines():
            if "," in line and "https://" in line:
                date, url = line.strip().split(",", 1)
                # Extract slug from URL
                slug = url.rstrip("/").split("/")[-1]
                existing[slug] = date
    return existing


def verify_url_exists(url: str, get_date: bool = False) -> tuple[bool, str | None]:
    """Check if a URL exists and optionally get its publish date."""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0",
    }
    try:
        if get_date:
            # GET request to extract publish date from meta tag
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            if response.status_code == 200:
                # Look for article:published_time or datePublished
                import re as regex
                match = regex.search(
                    r'property="article:published_time"\s+content="([^"]+)"',
                    response.text
                )
                if match:
                    # Parse ISO date to YYYY-MM-DD
                    date_str = match.group(1)[:10]
                    return True, date_str
                # Fallback: look for datePublished in JSON-LD
                match = regex.search(r'"datePublished"\s*:\s*"([^"]+)"', response.text)
                if match:
                    date_str = match.group(1)[:10]
                    return True, date_str
                return True, None
            return False, None
        else:
            response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            return response.status_code == 200, None
    except requests.RequestException:
        return False, None


def verify_urls_batch(urls: list[str], max_workers: int = 10, get_date: bool = False) -> dict[str, tuple[bool, str | None]]:
    """Verify multiple URLs concurrently."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(verify_url_exists, url, get_date): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                exists, date = future.result()
                results[url] = (exists, date)
            except Exception:
                results[url] = (False, None)
    return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch JedAI Council episodes")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--missing", action="store_true", help="Show only missing episodes")
    parser.add_argument("--urls-only", action="store_true", help="Output only URLs")
    parser.add_argument("--update-list", action="store_true", help="Update list.txt with new episodes")
    parser.add_argument("--verify", action="store_true", help="Verify URLs exist (slow but accurate)")
    parser.add_argument("--get-dates", action="store_true", help="Fetch publish dates for missing episodes (slower)")
    args = parser.parse_args()

    print("Fetching episodes from API...", file=sys.stderr)
    episodes = fetch_episodes()
    print(f"Found {len(episodes)} episodes in API", file=sys.stderr)

    existing = load_existing_list()
    print(f"Found {len(existing)} episodes in list.txt", file=sys.stderr)

    results = []
    missing = []

    for ep in episodes:
        name = ep.get("name", "")
        slug = slugify(name)
        url = f"{BASE_URL}{slug}/"
        date = existing.get(slug, None)

        entry = {
            "id": ep.get("id", ""),
            "name": name,
            "slug": slug,
            "url": url,
            "date": date,
            "in_list": date is not None
        }
        results.append(entry)

        if date is None:
            missing.append(entry)

    # Verify missing URLs if requested
    if (args.verify or args.get_dates) and missing:
        # Deduplicate URLs first
        seen_urls = set()
        unique_missing = []
        for m in missing:
            if m["url"] not in seen_urls:
                seen_urls.add(m["url"])
                unique_missing.append(m)

        print(f"\nVerifying {len(unique_missing)} unique URLs...", file=sys.stderr)
        urls_to_verify = [m["url"] for m in unique_missing]
        verification_results = verify_urls_batch(urls_to_verify, get_date=args.get_dates)

        verified_missing = []
        for m in unique_missing:
            exists, publish_date = verification_results.get(m["url"], (False, None))
            m["verified"] = exists
            if publish_date:
                m["date"] = publish_date
            if exists:
                verified_missing.append(m)

        print(f"Verified: {len(verified_missing)} URLs exist", file=sys.stderr)
        missing = verified_missing

    # Output
    if args.json:
        output = missing if args.missing else results
        print(json.dumps(output, indent=2))
    elif args.urls_only:
        for r in (missing if args.missing else results):
            print(r["url"])
    else:
        # Default: show summary and missing
        print(f"\nTotal episodes: {len(results)}", file=sys.stderr)
        print(f"In list.txt: {len(results) - len(missing)}", file=sys.stderr)
        print(f"Missing: {len(missing)}", file=sys.stderr)

        if missing:
            print("\nMissing episodes (need dates):")
            for m in missing:
                print(f"  {m['id']}: {m['name']}")
                print(f"    URL: {m['url']}")


if __name__ == "__main__":
    main()
