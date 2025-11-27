#!/usr/bin/env python3
"""Utilities for wiping or snapshotting RaeburnBrainAI memory shards."""

from __future__ import annotations

import argparse
from pathlib import Path

from RaeburnBrainAI.memory import MemoryStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage RaeburnBrainAI memory shards.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    wipe_p = sub.add_parser("wipe", help="Wipe a shard (agent id)")
    wipe_p.add_argument("agent", help="Agent id to wipe (use 'global' for shared shard)")

    snap_p = sub.add_parser("snapshot", help="Export a shard to JSON")
    snap_p.add_argument("agent", help="Agent id to snapshot")
    snap_p.add_argument("dest", help="Destination JSON file")

    args = parser.parse_args()
    store = MemoryStore()

    if args.cmd == "wipe":
        store.wipe(args.agent)
        print(f"Wiped shard for agent {args.agent}")
    elif args.cmd == "snapshot":
        dest = Path(args.dest)
        store.snapshot(args.agent, dest)
        print(f"Snapshot saved to {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
