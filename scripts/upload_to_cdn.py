#!/usr/bin/env python3
"""
Bunny CDN Upload Script for JedAI Council recordings.

Uploads video files and metadata to Bunny CDN, generates a manifest,
and updates episode records with CDN URLs.

Usage:
    python scripts/upload_to_cdn.py --file recordings/episode.mp4 --remote the-council/
    python scripts/upload_to_cdn.py --dir recordings/ --remote the-council/ --pattern "*.mp4"
    python scripts/upload_to_cdn.py --dry-run --file recordings/episode.mp4

Environment Variables:
    BUNNY_STORAGE_ZONE     Storage zone name (required)
    BUNNY_STORAGE_PASSWORD Storage zone API password (required)
    BUNNY_CDN_URL          CDN URL (default: https://{zone}.b-cdn.net)
    BUNNY_STORAGE_HOST     Storage API host (default: https://la.storage.bunnycdn.com)

Requires: pip install requests python-dotenv
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests library required. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *args: None

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Constants
DEFAULT_STORAGE_HOST = "https://la.storage.bunnycdn.com"
DEFAULT_TIMEOUT = 300  # 5 minutes for large video files
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
ALLOWED_EXTENSIONS = {".mp4", ".webm", ".json", ".png", ".jpg", ".jpeg"}


@dataclass
class UploadResult:
    """Result of a single upload operation."""
    local_path: str
    remote_path: str
    cdn_url: str
    success: bool
    message: str
    size: int = 0


@dataclass
class CDNConfig:
    """CDN configuration."""
    storage_zone: str
    password: str
    storage_host: str = DEFAULT_STORAGE_HOST
    cdn_url: str = ""
    dry_run: bool = False

    def __post_init__(self):
        if not self.cdn_url:
            self.cdn_url = f"https://{self.storage_zone}.b-cdn.net"


def get_config_from_env() -> CDNConfig:
    """Load CDN configuration from environment variables."""
    storage_zone = os.getenv("BUNNY_STORAGE_ZONE", "")
    password = os.getenv("BUNNY_STORAGE_PASSWORD", "")
    storage_host = os.getenv("BUNNY_STORAGE_HOST", DEFAULT_STORAGE_HOST)
    cdn_url = os.getenv("BUNNY_CDN_URL", "")

    return CDNConfig(
        storage_zone=storage_zone,
        password=password,
        storage_host=storage_host,
        cdn_url=cdn_url
    )


def validate_remote_path(path: str) -> tuple[bool, str]:
    """Validate and sanitize remote path."""
    # Strip leading slashes
    clean = path.lstrip("/")

    # Block path traversal
    if ".." in clean:
        return False, "Path traversal not allowed"

    # Block suspicious characters
    if any(c in clean for c in "<>|\x00"):
        return False, "Invalid characters in path"

    if not clean:
        return False, "Path cannot be empty"

    return True, clean


def get_content_type(file_path: str) -> str:
    """Get MIME type for file."""
    ext = Path(file_path).suffix.lower()
    types = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    return types.get(ext, "application/octet-stream")


def upload_file(
    local_path: str,
    remote_path: str,
    config: CDNConfig
) -> UploadResult:
    """Upload a single file to Bunny CDN."""
    local = Path(local_path)

    # Validate local file
    if not local.exists():
        return UploadResult(
            local_path=str(local),
            remote_path=remote_path,
            cdn_url="",
            success=False,
            message="File not found"
        )

    # Check file size
    size = local.stat().st_size
    if size > MAX_FILE_SIZE:
        return UploadResult(
            local_path=str(local),
            remote_path=remote_path,
            cdn_url="",
            success=False,
            message=f"File too large: {size / 1024 / 1024:.1f}MB (max {MAX_FILE_SIZE / 1024 / 1024:.0f}MB)",
            size=size
        )

    # Check extension
    if local.suffix.lower() not in ALLOWED_EXTENSIONS:
        return UploadResult(
            local_path=str(local),
            remote_path=remote_path,
            cdn_url="",
            success=False,
            message=f"File type not allowed: {local.suffix}"
        )

    # Validate remote path
    valid, clean_path = validate_remote_path(remote_path)
    if not valid:
        return UploadResult(
            local_path=str(local),
            remote_path=remote_path,
            cdn_url="",
            success=False,
            message=f"Invalid path: {clean_path}"
        )

    cdn_url = f"{config.cdn_url.rstrip('/')}/{clean_path}"

    # Dry run mode
    if config.dry_run:
        return UploadResult(
            local_path=str(local),
            remote_path=clean_path,
            cdn_url=cdn_url,
            success=True,
            message="dry-run",
            size=size
        )

    # Perform upload
    url = f"{config.storage_host}/{config.storage_zone}/{clean_path}"
    headers = {
        "AccessKey": config.password,
        "Content-Type": "application/octet-stream",
    }

    try:
        with open(local_path, "rb") as f:
            response = requests.put(
                url,
                data=f,
                headers=headers,
                timeout=DEFAULT_TIMEOUT
            )

        if response.status_code in (200, 201):
            return UploadResult(
                local_path=str(local),
                remote_path=clean_path,
                cdn_url=cdn_url,
                success=True,
                message="uploaded",
                size=size
            )
        else:
            return UploadResult(
                local_path=str(local),
                remote_path=clean_path,
                cdn_url="",
                success=False,
                message=f"HTTP {response.status_code}: {response.text[:100]}",
                size=size
            )
    except requests.RequestException as e:
        return UploadResult(
            local_path=str(local),
            remote_path=clean_path,
            cdn_url="",
            success=False,
            message=f"Request error: {e}",
            size=size
        )


def upload_directory(
    dir_path: str,
    remote_prefix: str,
    config: CDNConfig,
    pattern: str = "*",
    max_workers: int = 3
) -> list[UploadResult]:
    """Upload all matching files in a directory."""
    local_dir = Path(dir_path)
    if not local_dir.is_dir():
        raise ValueError(f"Not a directory: {dir_path}")

    # Find matching files
    files = [f for f in local_dir.iterdir() if f.is_file() and fnmatch(f.name, pattern)]

    if not files:
        print(f"No files matching '{pattern}' in {dir_path}", file=sys.stderr)
        return []

    results = []

    # Upload with progress
    def upload_one(file: Path) -> UploadResult:
        remote_path = f"{remote_prefix.rstrip('/')}/{file.name}"
        return upload_file(str(file), remote_path, config)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(upload_one, f): f for f in files}
        for i, future in enumerate(as_completed(future_to_file), 1):
            file = future_to_file[future]
            result = future.result()
            results.append(result)
            status = "✓" if result.success else "✗"
            print(f"[{status}] {i}/{len(files)} {file.name}", file=sys.stderr)

    return results


def generate_manifest(
    results: list[UploadResult],
    output_path: Optional[str] = None
) -> dict:
    """Generate a manifest JSON from upload results."""
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "provider": "bunny",
        "stats": {
            "total": len(results),
            "uploaded": sum(1 for r in results if r.success and r.message == "uploaded"),
            "skipped": sum(1 for r in results if r.success and r.message == "dry-run"),
            "failed": sum(1 for r in results if not r.success),
            "total_size": sum(r.size for r in results if r.success),
        },
        "files": [asdict(r) for r in results]
    }

    if output_path:
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"Manifest saved to: {output_path}", file=sys.stderr)

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Upload files to Bunny CDN")
    parser.add_argument("--file", help="Single file to upload")
    parser.add_argument("--dir", help="Directory to upload")
    parser.add_argument("--remote", required=True, help="Remote path/prefix on CDN")
    parser.add_argument("--pattern", default="*.mp4", help="File pattern for directory (default: *.mp4)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--manifest", help="Output manifest JSON path")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    if not args.file and not args.dir:
        parser.error("Either --file or --dir is required")

    config = get_config_from_env()
    config.dry_run = args.dry_run

    # Validate credentials (unless dry run)
    if not args.dry_run and (not config.storage_zone or not config.password):
        print("Error: Missing CDN credentials. Set BUNNY_STORAGE_ZONE and BUNNY_STORAGE_PASSWORD", file=sys.stderr)
        sys.exit(1)

    # Use placeholder for dry-run
    if args.dry_run:
        config.storage_zone = config.storage_zone or "dry-run-zone"
        config.password = config.password or "dry-run-password"
        config.cdn_url = config.cdn_url or "https://dry-run.b-cdn.net"

    results = []

    if args.file:
        # Single file upload
        remote_path = args.remote
        if remote_path.endswith("/"):
            remote_path += Path(args.file).name

        print(f"{'[DRY RUN] ' if args.dry_run else ''}Uploading: {args.file}", file=sys.stderr)
        result = upload_file(args.file, remote_path, config)
        results = [result]

        if result.success:
            print(f"✓ {result.cdn_url}", file=sys.stderr)
        else:
            print(f"✗ {result.message}", file=sys.stderr)

    elif args.dir:
        # Directory upload
        print(f"{'[DRY RUN] ' if args.dry_run else ''}Uploading directory: {args.dir}", file=sys.stderr)
        results = upload_directory(args.dir, args.remote, config, args.pattern)

    # Generate manifest if requested
    manifest = None
    if args.manifest:
        manifest = generate_manifest(results, args.manifest)

    # Output
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        # Summary
        stats = {
            "total": len(results),
            "uploaded": sum(1 for r in results if r.success and r.message == "uploaded"),
            "skipped": sum(1 for r in results if r.success and r.message == "dry-run"),
            "failed": sum(1 for r in results if not r.success),
            "total_size": sum(r.size for r in results if r.success),
        }
        print(f"\nUpload Statistics:", file=sys.stderr)
        print(f"  Total: {stats['total']}", file=sys.stderr)
        print(f"  Uploaded: {stats['uploaded']}", file=sys.stderr)
        if stats['skipped']:
            print(f"  Skipped (dry-run): {stats['skipped']}", file=sys.stderr)
        print(f"  Failed: {stats['failed']}", file=sys.stderr)
        print(f"  Size: {stats['total_size'] / 1024 / 1024:.1f} MB", file=sys.stderr)

        # Print CDN URLs for successful uploads
        successes = [r for r in results if r.success and r.cdn_url]
        if successes:
            print(f"\nCDN URLs:", file=sys.stderr)
            for r in successes[:5]:
                print(f"  {r.cdn_url}", file=sys.stderr)
                # Also output to stdout for easy capture
                print(f"CDN_URL={r.cdn_url}")
            if len(successes) > 5:
                print(f"  ... and {len(successes) - 5} more", file=sys.stderr)

    # Exit with error if any failures
    failures = [r for r in results if not r.success]
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
