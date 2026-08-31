import bz2
import csv
import gzip
import json
from pathlib import Path

from run_lanl_trajectories import build


def write_bz2(path: Path, text: str) -> None:
    path.write_bytes(bz2.compress(text.encode("utf-8")))


def test_small_overlap_trajectory(tmp_path):
    host = tmp_path / "host.bz2"
    net = tmp_path / "net.bz2"
    db = tmp_path / "traj.sqlite"
    result = tmp_path / "result.json"
    traj = tmp_path / "traj.csv.gz"

    # One pre-overlap host record must be excluded; remaining records span two 300-s windows.
    host_events = [
        {"EventID": 4624, "UserName": "User1", "Computer": "Comp1", "LogonID": "L0", "Time": 118700},
        {"EventID": 4624, "UserName": "User1", "Computer": "Comp1", "LogonID": "L1", "Time": 118800},
        {"EventID": 4688, "UserName": "User1", "Computer": "Comp1", "ProcessName": "a.exe", "ProcessID": "1", "Time": 118850},
        {"EventID": 4624, "UserName": "Comp2$", "Computer": "Comp2", "Time": 119100},
    ]
    write_bz2(host, "".join(json.dumps(x)+"\n" for x in host_events))
    write_bz2(net, "118820,1,Comp1,Comp3,6,1,2,1,2,10,20\n119120,1,Comp3,Comp2,6,1,2,1,2,10,20\n")

    out = build(host, net, db, result, traj)
    assert out["status"] == "PASS"
    assert out["host_diagnostics"]["excluded_before_overlap"] == 1
    s300 = out["summaries"]["300"]
    assert s300["active_device_windows"] >= 4
    assert s300["H_rows"] >= 1
    assert s300["P_rows"] >= 1
    assert s300["T_rows"] >= 2
    assert out["guardrails"]["defensive_intervention_C_inferred"] is False

    with gzip.open(traj, "rt", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    assert "active_types" in rows[0]
    assert all("C" not in row for row in rows)
