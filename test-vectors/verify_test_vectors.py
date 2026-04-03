#!/usr/bin/env python3
"""Recompute MPCP v1.0 test-vector hashes; exit 1 on mismatch."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def canonical_json_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    expected_path = ROOT / "expected-hashes.json"
    with open(expected_path, encoding="utf-8") as f:
        manifest = json.load(f)

    errors = []
    for key, entry in manifest.items():
        if key == "description" or not isinstance(entry, dict):
            continue
        src = ROOT / entry["sourceFile"]
        prefix = entry["prefix"].encode("utf-8")
        want = entry["sha256_hex"]
        with open(src, encoding="utf-8") as f:
            obj = json.load(f)
        body = canonical_json_bytes(obj)
        got = sha256_hex(prefix + body)
        if got != want:
            errors.append(f"{key}: expected {want} got {got} ({src.name})")

    if errors:
        print("FAIL", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print("OK — all test vector hashes match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
