#!/usr/bin/env python3
"""
Small helper to add all changes, commit, and push.

Defaults:
    commit message: "feat: enrich model registry and router"
    branch: "master"

Usage:
    python tools/commit_push.py
    python tools/commit_push.py --message "chore: update docs" --branch main
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import List


def run_cmd(cmd: List[str]) -> None:
    """Run a shell command and surface errors."""
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Commit and push helper.")
    parser.add_argument(
        "--message",
        default="feat: enrich model registry and router",
        help="Commit message to use.",
    )
    parser.add_argument(
        "--branch",
        default="master",
        help="Branch to push to (default: master).",
    )
    args = parser.parse_args()

    try:
        run_cmd(["git", "status"])
        run_cmd(["git", "add", "."])
        run_cmd(["git", "commit", "-m", args.message])
        run_cmd(["git", "push", "origin", args.branch])
    except subprocess.CalledProcessError as exc:
        print(f"[error] Command failed: {exc}", file=sys.stderr)
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
