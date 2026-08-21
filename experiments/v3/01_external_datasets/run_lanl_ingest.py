"""V3-LANL-INGEST-001: stream a frozen LANL host+netflow day and retain aggregates only."""
from __future__ import annotations

import argparse
import bz2
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

from lanl_adapter import map_host_event, map_network_flow

PERSON_RE = re.compile(r"^User\d+$", re.IGNORECASE)
DEVICE_RE = re.compile(r"^Comp\d+$", re.IGNORECASE)


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def account_category(value: object) -> str:
    if value in (None, ""):
        return "missing"
    text = str(value)
    if PERSON_RE.fullmatch(text):
        return "deidentified_person"
    if text.endswith("$"):
        return "machine_account"
    return "named_or_other"


def add_device(target: set[str], value: object) -> None:
    if value in (None, ""):
        return
    text = str(value)
    if DEVICE_RE.fullmatch(text):
        target.add(text)


def update_time(stats: dict, ts: int) -> None:
    if stats["min_time"] is None or ts < stats["min_time"]:
        stats["min_time"] = ts
    if stats["max_time"] is None or ts > stats["max_time"]:
        stats["max_time"] = ts
    prev = stats["previous_time"]
    if prev is not None and ts < prev:
        stats["timestamp_order_violations"] += 1
    stats["previous_time"] = ts


def ingest_host(path: Path) -> tuple[dict, set[str]]:
    stats = {
        "compressed_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "raw_records": 0,
        "parsed_records": 0,
        "malformed_records": 0,
        "emitted": Counter(),
        "event_ids": Counter(),
        "account_categories": Counter(),
        "person_accounts": set(),
        "host_devices": set(),
        "process_names": set(),
        "process_ids": set(),
        "parent_process_ids": set(),
        "session_keys": set(),
        "user_process_pairs": set(),
        "min_time": None,
        "max_time": None,
        "previous_time": None,
        "timestamp_order_violations": 0,
    }

    with bz2.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            stats["raw_records"] += 1
            try:
                event = json.loads(line)
                event_id = int(event["EventID"])
                ts = int(event.get("Time", event.get("time")))
                observations = map_host_event(event)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                stats["malformed_records"] += 1
                continue

            stats["parsed_records"] += 1
            stats["event_ids"][str(event_id)] += 1
            update_time(stats, ts)

            user = event.get("UserName") or event.get("SubjectUserName")
            category = account_category(user)
            stats["account_categories"][category] += 1
            if category == "deidentified_person":
                user = str(user)
                stats["person_accounts"].add(user)
            else:
                user = None

            for key in ("LogHost", "Computer", "Source", "Destination"):
                add_device(stats["host_devices"], event.get(key))

            process_name = event.get("ProcessName")
            if process_name not in (None, ""):
                stats["process_names"].add(str(process_name))
            process_id = event.get("ProcessID")
            if process_id not in (None, ""):
                stats["process_ids"].add(str(process_id))
            parent_id = event.get("ParentProcessID")
            if parent_id not in (None, ""):
                stats["parent_process_ids"].add(str(parent_id))

            log_host = event.get("LogHost", event.get("Computer"))
            logon_id = event.get("LogonID", event.get("SubjectLogonID"))
            if user and logon_id not in (None, ""):
                stats["session_keys"].add((user, str(log_host), str(logon_id)))
            if user and event_id in (4688, 4689):
                stats["user_process_pairs"].add((user, str(log_host), str(process_id)))

            for obs in observations:
                stats["emitted"][obs.dchag_type] += 1

    host_devices = stats.pop("host_devices")
    process_ids = stats.pop("process_ids")
    parent_process_ids = stats.pop("parent_process_ids")
    stats["unique_person_accounts"] = len(stats.pop("person_accounts"))
    stats["unique_process_names"] = len(stats.pop("process_names"))
    stats["unique_process_ids"] = len(process_ids)
    stats["unique_parent_process_ids"] = len(parent_process_ids)
    stats["parent_id_seen_as_process_id"] = len(process_ids & parent_process_ids)
    stats["unique_session_keys"] = len(stats.pop("session_keys"))
    stats["unique_user_process_keys"] = len(stats.pop("user_process_pairs"))
    stats["unique_host_devices"] = len(host_devices)
    stats["parse_fraction"] = (
        stats["parsed_records"] / stats["raw_records"] if stats["raw_records"] else None
    )
    stats["emitted"] = dict(sorted(stats["emitted"].items()))
    stats["event_ids"] = dict(sorted(stats["event_ids"].items(), key=lambda kv: int(kv[0])))
    stats["account_categories"] = dict(sorted(stats["account_categories"].items()))
    stats.pop("previous_time")
    return stats, host_devices


def ingest_network(path: Path) -> tuple[dict, set[str]]:
    stats = {
        "compressed_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "raw_records": 0,
        "parsed_records": 0,
        "malformed_records": 0,
        "emitted": Counter(),
        "network_devices": set(),
        "min_time": None,
        "max_time": None,
        "previous_time": None,
        "timestamp_order_violations": 0,
    }

    with bz2.open(path, "rt", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row:
                continue
            stats["raw_records"] += 1
            try:
                if len(row) < 11:
                    raise ValueError("network row has fewer than 11 fields")
                ts = int(row[0])
                observations = map_network_flow(row)
            except (TypeError, ValueError):
                stats["malformed_records"] += 1
                continue

            stats["parsed_records"] += 1
            update_time(stats, ts)
            add_device(stats["network_devices"], row[2])
            add_device(stats["network_devices"], row[3])
            for obs in observations:
                stats["emitted"][obs.dchag_type] += 1

    network_devices = stats.pop("network_devices")
    stats["unique_network_devices"] = len(network_devices)
    stats["parse_fraction"] = (
        stats["parsed_records"] / stats["raw_records"] if stats["raw_records"] else None
    )
    stats["emitted"] = dict(sorted(stats["emitted"].items()))
    stats.pop("previous_time")
    return stats, network_devices


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True, type=Path)
    parser.add_argument("--network", required=True, type=Path)
    parser.add_argument("--output", default="LANL_INGEST_RESULTS.json", type=Path)
    args = parser.parse_args()

    host_stats, host_devices = ingest_host(args.host)
    network_stats, network_devices = ingest_network(args.network)
    overlap = host_devices & network_devices
    union = host_devices | network_devices

    emitted_total = Counter(host_stats["emitted"]) + Counter(network_stats["emitted"])
    total_obs = sum(emitted_total.values())
    result = {
        "experiment_id": "V3-LANL-INGEST-001",
        "status": "PASS",
        "claim_boundary": "observational ingestibility, typed coverage, temporal/linkage feasibility only",
        "host": host_stats,
        "network": network_stats,
        "combined": {
            "emitted": dict(sorted(emitted_total.items())),
            "emitted_proportions": {
                key: value / total_obs for key, value in sorted(emitted_total.items())
            } if total_obs else {},
            "total_typed_observations": total_obs,
            "host_network_device_overlap": len(overlap),
            "host_network_device_union": len(union),
            "host_network_device_jaccard": len(overlap) / len(union) if union else None,
        },
        "guardrails": {
            "attack_or_red_team_labels_read": false,
            "defensive_intervention_C_inferred": false,
            "counterfactual_effect_claim": false
        }
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
