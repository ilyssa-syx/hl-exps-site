#!/usr/bin/env python3
"""Incrementally upload local visualization assets to the site's R2 bucket."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACCOUNT_ID = "818a801f60dd235b5dc37fabaa1a2dce"
DEFAULT_PUBLIC_BASE = "https://pub-1eb5d3d086d6442b89e5a0e0bca12d9d.r2.dev/hl-exps-site/v1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, default=ROOT / "r2_assets")
    parser.add_argument("--account-id", default=DEFAULT_ACCOUNT_ID)
    parser.add_argument("--bucket", default="hl-exps-site")
    parser.add_argument("--prefix", default="hl-exps-site/v1")
    parser.add_argument("--profile", default="hl-exps-r2")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if shutil.which("aws") is None:
        raise FileNotFoundError("aws CLI is required")
    asset_root = args.asset_root.resolve()
    if not asset_root.is_dir() or not any(path.is_file() for path in asset_root.rglob("*")):
        raise FileNotFoundError(f"asset staging directory is empty: {asset_root}")
    destination = f"s3://{args.bucket}/{args.prefix.strip('/')}"
    command = [
        "aws", "s3", "sync", str(asset_root), destination,
        "--profile", args.profile,
        "--endpoint-url", f"https://{args.account_id}.r2.cloudflarestorage.com",
        "--region", "auto",
        "--cache-control", "public, max-age=31536000, immutable",
        "--only-show-errors",
    ]
    if args.dry_run:
        command.append("--dryrun")
    subprocess.run(command, check=True)
    verb = "Previewed" if args.dry_run else "Published"
    print(f"{verb} {asset_root} at {DEFAULT_PUBLIC_BASE}")


if __name__ == "__main__":
    main()
