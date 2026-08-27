#!/usr/bin/env python3
"""Reproducible OpTC pilot ingestion for DCHAG v3.

Fetches one immutable public eCAR snippet, verifies source identity using Git's
blob hash construction and byte size, maps records through ``optc_adapter``, and
writes aggregate-only JSON. Red-team ground truth is deliberately never read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from optc_adapter import map_ecar_event

SOURCE_URL = (
    "https://raw.githubusercontent.com/brbickel/ecar-challenge/"
    "45b7c7c85ddce4b44f84f68af7822c5466a7077d/data.json"
)
EXPECTED_BYTES = 5_649_857
EXPECTED_GIT_BLOB_SHA1 = "25279a41030981ead9bf6134432aa6112429eb82"


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def load_records(data: bytes):
    text = data.decode("utf-8")
    stripped = text.lstrip()
    if stripped.startswith("["):
        obj = json.loads(text)
        if not isinstance(obj, list):
            raise ValueError("JSON top level is not a list")
        yield from obj
        return
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {lineno}: {exc}") from exc


def summarize_timestamps(timestamps: list[int]) -> dict:
    """Summarize valid timestamps without mutating source-record order."""
    nondecreasing = all(a <= b for a, b in zip(timestamps, timestamps[1:]))
    min_ts = min(timestamps) if timestamps else None
    max_ts = max(timestamps) if timestamps else None
    span_ms = max_ts - min_ts if min_ts is not None and max_ts is not None and len(timestamps) >= 2 else None
    return {
        "valid_timestamp_count": len(timestamps),
        "source_order_nondecreasing": nondecreasing,
        "min_timestamp_ms": min_ts,
        "max_timestamp_ms": max_ts,
        "span_ms": span_ms,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, help="Optional pre-downloaded data.json")
    ap.add_argument("--output", type=Path, default=Path("OPTC_INGEST_RESULTS.json"))
    args = ap.parse_args()

    if args.input:
        data = args.input.read_bytes()
        acquisition = f"local:{args.input}"
    else:
        with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
            data = response.read()
        acquisition = SOURCE_URL

    actual_sha1 = git_blob_sha1(data)
    if len(data) != EXPECTED_BYTES:
        raise SystemExit(f"source size mismatch: {len(data)} != {EXPECTED_BYTES}")
    if actual_sha1 != EXPECTED_GIT_BLOB_SHA1:
        raise SystemExit(f"source Git blob SHA-1 mismatch: {actual_sha1}")

    n_records = 0
    n_mapping_failures = 0
    typed_counts = Counter()
    object_counts = Counter()
    action_counts = Counter()
    role_counts = Counter()
    principal_records = 0
    hostname_records = 0
    missing_actor = 0
    missing_object_id = 0
    timestamps = []

    for event in load_records(data):
        n_records += 1
        object_counts[str(event.get("object", "UNKNOWN")).upper()] += 1
        action_counts[str(event.get("action", "UNKNOWN")).upper()] += 1
        if event.get("principal") not in (None, ""):
            principal_records += 1
        if event.get("hostname") not in (None, ""):
            hostname_records += 1
        if event.get("actorID") in (None, ""):
            missing_actor += 1
        if event.get("objectID") in (None, ""):
            missing_object_id += 1
        ts = event.get("timestamp_ms", event.get("timestamp"))
        if ts is not None:
            try:
                timestamps.append(int(ts))
            except (TypeError, ValueError):
                pass
        try:
            mapped = map_ecar_event(event)
        except Exception:
            n_mapping_failures += 1
            continue
        for obs in mapped:
            typed_counts[obs.dchag_type] += 1
            role_counts[obs.evidence_role] += 1

    result = {
        "experiment_id": "V3-OPTC-INGEST-001-C1",
        "parent_protocol_id": "V3-OPTC-INGEST-001",
        "correction": "C1 source-order temporal endpoint",
        "source": {
            "acquisition": acquisition,
            "immutable_url": SOURCE_URL,
            "bytes": len(data),
            "git_blob_sha1": actual_sha1,
        },
        "red_team_ground_truth_used": False,
        "records": n_records,
        "mapping_failures": n_mapping_failures,
        "record_coverage": {
            "principal_records": principal_records,
            "hostname_records": hostname_records,
            "missing_actor_id": missing_actor,
            "missing_object_id": missing_object_id,
        },
        "typed_observations": dict(sorted(typed_counts.items())),
        "evidence_roles": dict(sorted(role_counts.items())),
        "source_objects": dict(object_counts.most_common()),
        "source_actions": dict(action_counts.most_common()),
        "temporal": summarize_timestamps(timestamps),
        "claim_boundary": (
            "This experiment measures observational schema/typing coverage only. "
            "It does not estimate defensive-control causal effects."
        ),
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
