import bz2
import json
from pathlib import Path

from run_lanl_ingest import build_result


def write_bz2(path: Path, text: str) -> None:
    path.write_bytes(bz2.compress(text.encode("utf-8")))


def test_build_result_on_small_frozen_like_streams(tmp_path):
    host = tmp_path / "wls_day-02.bz2"
    network = tmp_path / "netflow_day-02.bz2"

    host_events = [
        {"EventID": 4624, "UserName": "User1", "LogonID": "L1", "Computer": "Comp1", "Time": 2},
        {"EventID": 4624, "UserName": "Comp2$", "Computer": "Comp2", "Time": 3},
        {"EventID": 4688, "UserName": "User1", "ProcessName": "a.exe", "ProcessID": "10", "ParentProcessID": "5", "Computer": "Comp1", "Time": 4},
        {"EventID": 4688, "UserName": "SYSTEM", "ProcessName": "svc.exe", "ProcessID": "11", "ParentProcessID": "10", "Computer": "Comp1", "Time": 5},
    ]
    write_bz2(host, "".join(json.dumps(x) + "\n" for x in host_events))
    write_bz2(network, "6,10,Comp1,Comp3,6,1000,443,1,2,100,200\n")

    result = build_result(host, network)

    assert result["status"] == "PASS"
    assert result["host"]["raw_records"] == 4
    assert result["host"]["parsed_records"] == 4
    assert result["host"]["malformed_records"] == 0
    assert result["host"]["emitted"] == {"H": 2, "P": 2, "T": 2}
    assert result["network"]["emitted"] == {"T": 1}
    assert result["host"]["account_categories"] == {
        "deidentified_person": 2,
        "machine_account": 1,
        "named_or_other": 1,
    }
    assert result["host"]["unique_person_accounts"] == 1
    assert result["combined"]["host_network_device_overlap"] == 1
    assert result["combined"]["emitted"] == {"H": 2, "P": 2, "T": 3}
    assert result["guardrails"]["attack_or_red_team_labels_read"] is False
    assert result["guardrails"]["defensive_intervention_C_inferred"] is False
