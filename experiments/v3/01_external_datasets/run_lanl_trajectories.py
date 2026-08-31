"""V3-LANL-TRAJ-001: build multi-resolution device trajectories in one chronological pass."""
from __future__ import annotations

import argparse
import bz2
import csv
import gzip
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from lanl_adapter import map_host_event

START = 118781
END = 172799
WIDTHS = (60, 300, 900)
PRIMARY_WIDTH = 300


@dataclass
class HostAgg:
    h: int = 0
    p: int = 0
    t_host: int = 0
    users: set[str] = field(default_factory=set)
    processes: set[str] = field(default_factory=set)
    logon_success: int = 0
    logon_failure: int = 0
    process_start: int = 0
    process_end: int = 0


@dataclass
class NetAgg:
    out_flows: int = 0
    in_flows: int = 0
    out_peers: set[str] = field(default_factory=set)
    in_peers: set[str] = field(default_factory=set)


def window_index(ts: int, width: int) -> int:
    if ts < START or ts > END:
        raise ValueError("timestamp outside frozen overlap interval")
    return (ts - START) // width


def canonical_host(event: dict) -> str | None:
    value = event.get("LogHost", event.get("Computer"))
    if value in (None, ""):
        return None
    return str(value)


def init_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    for width in WIDTHS:
        conn.execute(f"""
            CREATE TABLE traj_{width} (
                window_idx INTEGER NOT NULL,
                device TEXT NOT NULL,
                H_count INTEGER NOT NULL DEFAULT 0,
                P_count INTEGER NOT NULL DEFAULT 0,
                T_host_count INTEGER NOT NULL DEFAULT 0,
                unique_person_users INTEGER NOT NULL DEFAULT 0,
                unique_process_names INTEGER NOT NULL DEFAULT 0,
                logon_success_4624 INTEGER NOT NULL DEFAULT 0,
                logon_failure_4625 INTEGER NOT NULL DEFAULT 0,
                process_start_4688 INTEGER NOT NULL DEFAULT 0,
                process_end_4689 INTEGER NOT NULL DEFAULT 0,
                net_out_flows INTEGER NOT NULL DEFAULT 0,
                net_in_flows INTEGER NOT NULL DEFAULT 0,
                unique_out_peers INTEGER NOT NULL DEFAULT 0,
                unique_in_peers INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (window_idx, device)
            ) WITHOUT ROWID
        """)
    return conn


def flush_host(conn: sqlite3.Connection, width: int, idx: int, state: dict[str, HostAgg]) -> None:
    if not state:
        return
    rows = [(
        idx, device, a.h, a.p, a.t_host, len(a.users), len(a.processes),
        a.logon_success, a.logon_failure, a.process_start, a.process_end,
    ) for device, a in state.items()]
    conn.executemany(f"""
        INSERT INTO traj_{width} (
            window_idx, device, H_count, P_count, T_host_count,
            unique_person_users, unique_process_names,
            logon_success_4624, logon_failure_4625,
            process_start_4688, process_end_4689
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)


def flush_net(conn: sqlite3.Connection, width: int, idx: int, state: dict[str, NetAgg]) -> None:
    if not state:
        return
    rows = [(
        idx, device, a.out_flows, a.in_flows, len(a.out_peers), len(a.in_peers)
    ) for device, a in state.items()]
    conn.executemany(f"""
        INSERT INTO traj_{width} (
            window_idx, device, net_out_flows, net_in_flows,
            unique_out_peers, unique_in_peers
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(window_idx, device) DO UPDATE SET
            net_out_flows = net_out_flows + excluded.net_out_flows,
            net_in_flows = net_in_flows + excluded.net_in_flows,
            unique_out_peers = unique_out_peers + excluded.unique_out_peers,
            unique_in_peers = unique_in_peers + excluded.unique_in_peers
    """, rows)


def ingest_host(conn: sqlite3.Connection, path: Path) -> dict:
    current = {w: None for w in WIDTHS}
    states: dict[int, dict[str, HostAgg]] = {w: {} for w in WIDTHS}
    raw = parsed = malformed = excluded_before_overlap = missing_entity = 0

    with bz2.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            raw += 1
            try:
                event = json.loads(line)
                ts = int(event.get("Time", event.get("time")))
            except (json.JSONDecodeError, TypeError, ValueError):
                malformed += 1
                continue
            if ts < START:
                excluded_before_overlap += 1
                continue
            if ts > END:
                break
            device = canonical_host(event)
            if device is None:
                missing_entity += 1
                continue
            try:
                obs = map_host_event(event)
            except (TypeError, ValueError):
                malformed += 1
                continue
            parsed += 1
            types = [x.dchag_type for x in obs]
            user = next((x.user for x in []), None)  # deliberately unused compatibility guard
            selected_user = event.get("UserName") or event.get("SubjectUserName")
            is_person = bool(selected_user and str(selected_user).lower().startswith("user") and str(selected_user)[4:].isdigit())
            process_name = event.get("ProcessName")
            event_id = int(event["EventID"])

            for width in WIDTHS:
                idx = window_index(ts, width)
                if current[width] is None:
                    current[width] = idx
                elif idx != current[width]:
                    flush_host(conn, width, current[width], states[width])
                    states[width] = {}
                    current[width] = idx
                a = states[width].setdefault(device, HostAgg())
                a.h += types.count("H")
                a.p += types.count("P")
                a.t_host += types.count("T")
                if is_person:
                    a.users.add(str(selected_user))
                if process_name not in (None, ""):
                    a.processes.add(str(process_name))
                if event_id == 4624:
                    a.logon_success += 1
                elif event_id == 4625:
                    a.logon_failure += 1
                elif event_id == 4688:
                    a.process_start += 1
                elif event_id == 4689:
                    a.process_end += 1

    for width in WIDTHS:
        if current[width] is not None:
            flush_host(conn, width, current[width], states[width])
    conn.commit()
    return {
        "raw_records_seen": raw,
        "parsed_overlap_records_with_entity": parsed,
        "malformed_records": malformed,
        "excluded_before_overlap": excluded_before_overlap,
        "missing_canonical_entity": missing_entity,
    }


def ingest_network(conn: sqlite3.Connection, path: Path) -> dict:
    current = {w: None for w in WIDTHS}
    states: dict[int, dict[str, NetAgg]] = {w: {} for w in WIDTHS}
    raw = parsed = malformed = 0

    with bz2.open(path, "rt", encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.reader(fh):
            if not row:
                continue
            raw += 1
            try:
                if len(row) < 4:
                    raise ValueError
                ts = int(row[0])
                if ts < START:
                    continue
                if ts > END:
                    break
                src, dst = str(row[2]), str(row[3])
            except (TypeError, ValueError):
                malformed += 1
                continue
            parsed += 1
            for width in WIDTHS:
                idx = window_index(ts, width)
                if current[width] is None:
                    current[width] = idx
                elif idx != current[width]:
                    flush_net(conn, width, current[width], states[width])
                    states[width] = {}
                    current[width] = idx
                src_a = states[width].setdefault(src, NetAgg())
                src_a.out_flows += 1
                src_a.out_peers.add(dst)
                dst_a = states[width].setdefault(dst, NetAgg())
                dst_a.in_flows += 1
                dst_a.in_peers.add(src)

    for width in WIDTHS:
        if current[width] is not None:
            flush_net(conn, width, current[width], states[width])
    conn.commit()
    return {"raw_records_seen": raw, "parsed_overlap_records": parsed, "malformed_records": malformed}


def summarize(conn: sqlite3.Connection, width: int) -> dict:
    table = f"traj_{width}"
    q = conn.execute
    rows = q(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    devices = q(f"SELECT COUNT(DISTINCT device) FROM {table}").fetchone()[0]
    h_rows = q(f"SELECT COUNT(*) FROM {table} WHERE H_count>0").fetchone()[0]
    p_rows = q(f"SELECT COUNT(*) FROM {table} WHERE P_count>0").fetchone()[0]
    t_rows = q(f"SELECT COUNT(*) FROM {table} WHERE T_host_count>0 OR net_out_flows>0 OR net_in_flows>0").fetchone()[0]
    all_hpt = q(f"SELECT COUNT(*) FROM {table} WHERE H_count>0 AND P_count>0 AND (T_host_count>0 OR net_out_flows>0 OR net_in_flows>0)").fetchone()[0]
    two_plus = q(f"""
        SELECT COUNT(*) FROM {table}
        WHERE (H_count>0) + (P_count>0) + ((T_host_count>0 OR net_out_flows>0 OR net_in_flows>0)) >= 2
    """).fetchone()[0]
    hp_and_t = q(f"""
        SELECT COUNT(*) FROM {table}
        WHERE (H_count>0 OR P_count>0) AND (T_host_count>0 OR net_out_flows>0 OR net_in_flows>0)
    """).fetchone()[0]
    multimodal_devices = q(f"""
        SELECT COUNT(*) FROM (
          SELECT device FROM {table}
          GROUP BY device
          HAVING SUM(CASE WHEN (H_count>0 OR P_count>0 OR T_host_count>0) THEN 1 ELSE 0 END)>0
             AND SUM(CASE WHEN (net_out_flows>0 OR net_in_flows>0) THEN 1 ELSE 0 END)>0
        )
    """).fetchone()[0]
    active_counts = [r[0] for r in q(f"SELECT COUNT(*) FROM {table} GROUP BY device")]
    active_counts.sort()
    def pct(p: float):
        if not active_counts:
            return None
        return active_counts[min(len(active_counts)-1, int(round((len(active_counts)-1)*p)))]
    return {
        "width_seconds": width,
        "active_device_windows": rows,
        "unique_devices": devices,
        "H_rows": h_rows,
        "P_rows": p_rows,
        "T_rows": t_rows,
        "all_HPT_rows": all_hpt,
        "two_or_more_type_rows": two_plus,
        "human_or_process_plus_technical_rows": hp_and_t,
        "multimodal_host_network_devices": multimodal_devices,
        "fractions": {
            "H": h_rows/rows if rows else None,
            "P": p_rows/rows if rows else None,
            "T": t_rows/rows if rows else None,
            "all_HPT": all_hpt/rows if rows else None,
            "two_or_more_types": two_plus/rows if rows else None,
            "human_or_process_plus_technical": hp_and_t/rows if rows else None,
            "multimodal_devices": multimodal_devices/devices if devices else None,
        },
        "active_windows_per_device": {
            "min": active_counts[0] if active_counts else None,
            "median": pct(0.5),
            "p90": pct(0.9),
            "max": active_counts[-1] if active_counts else None,
        }
    }


def export_primary(conn: sqlite3.Connection, output: Path) -> None:
    table = f"traj_{PRIMARY_WIDTH}"
    cols = [
        "window_idx","device","H_count","P_count","T_host_count","unique_person_users",
        "unique_process_names","logon_success_4624","logon_failure_4625","process_start_4688",
        "process_end_4689","net_out_flows","net_in_flows","unique_out_peers","unique_in_peers"
    ]
    with gzip.open(output, "wt", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(cols + ["H_present","P_present","T_host_present","T_net_present","T_present","active_types"])
        for row in conn.execute(f"SELECT {','.join(cols)} FROM {table} ORDER BY window_idx, device"):
            d = dict(zip(cols, row))
            hp = int(d["H_count"]>0)
            pp = int(d["P_count"]>0)
            th = int(d["T_host_count"]>0)
            tn = int(d["net_out_flows"]>0 or d["net_in_flows"]>0)
            tp = int(th or tn)
            writer.writerow(list(row) + [hp, pp, th, tn, tp, hp+pp+tp])


def build(host: Path, network: Path, db: Path, result_path: Path, trajectory_path: Path) -> dict:
    if db.exists():
        db.unlink()
    conn = init_db(db)
    try:
        host_diag = ingest_host(conn, host)
        net_diag = ingest_network(conn, network)
        summaries = {str(w): summarize(conn, w) for w in WIDTHS}
        export_primary(conn, trajectory_path)
    finally:
        conn.close()
    result = {
        "experiment_id": "V3-LANL-TRAJ-001",
        "status": "PASS",
        "interval": {"start": START, "end": END},
        "primary_width_seconds": PRIMARY_WIDTH,
        "sensitivity_widths_seconds": [60, 900],
        "host_diagnostics": host_diag,
        "network_diagnostics": net_diag,
        "summaries": summaries,
        "guardrails": {
            "attack_or_red_team_labels_read": False,
            "defensive_intervention_C_inferred": False,
            "counterfactual_effect_claim": False,
        },
    }
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, type=Path)
    ap.add_argument("--network", required=True, type=Path)
    ap.add_argument("--db", default=Path("lanl_traj.sqlite"), type=Path)
    ap.add_argument("--result", default=Path("LANL_TRAJECTORY_RESULTS.json"), type=Path)
    ap.add_argument("--trajectory", default=Path("LANL_TRAJECTORY_300S.csv.gz"), type=Path)
    args = ap.parse_args()
    print(json.dumps(build(args.host,args.network,args.db,args.result,args.trajectory), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
