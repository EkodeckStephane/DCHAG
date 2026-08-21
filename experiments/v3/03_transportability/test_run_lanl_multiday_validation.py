import bz2
import csv
import json
from pathlib import Path
import numpy as np

from run_lanl_multiday_validation import (
    build_disjoint_panel, stable_fold, transition_counts, run_day,
)


def _write_host(path: Path, rows):
    with bz2.open(path, "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _write_net(path: Path, rows):
    with bz2.open(path, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)


def test_person_filter_excludes_machine_and_system_accounts(tmp_path):
    host = tmp_path/"h.bz2"; net = tmp_path/"n.bz2"
    _write_host(host, [
        {"Time":86400,"EventID":4608,"Computer":"Comp1"},
        {"Time":86500,"EventID":4624,"UserName":"User1","Computer":"Comp1"},
        {"Time":86501,"EventID":4624,"UserName":"Comp1$","Computer":"Comp1"},
        {"Time":86502,"EventID":4625,"UserName":"SYSTEM","Computer":"Comp1"},
        {"Time":86801,"EventID":4688,"UserName":"SYSTEM","Computer":"Comp1"},
        {"Time":172799,"EventID":4609,"Computer":"Comp1"},
    ])
    _write_net(net, [
        [86500,1,"Comp1","Comp2",6,1,2,1,1,1,1],
        [172799,1,"Comp2","Comp1",6,1,2,1,1,1,1],
    ])
    devices, states, diag = build_disjoint_panel(2, host, net)
    i = list(devices).index("Comp1")
    assert states[i,:,0].sum() == 1
    assert states[i,:,1].sum() == 1
    assert states[i,:,2].sum() >= 1
    assert diag["host"]["person_login_events"] == 1
    assert diag["host"]["excluded_nonperson_login_events"] == 2
    assert diag["interval_start"] == 86500
    assert diag["interval_end"] == 172799


def test_channels_are_disjoint_by_raw_event_class(tmp_path):
    host = tmp_path/"h.bz2"; net = tmp_path/"n.bz2"
    _write_host(host, [
        {"Time":86400,"EventID":4624,"UserName":"User1","Computer":"C"},
        {"Time":86401,"EventID":4688,"UserName":"User1","Computer":"C"},
        {"Time":172799,"EventID":4609,"Computer":"C"},
    ])
    _write_net(net, [
        [86400,1,"C","D",6,1,2,1,1,1,1],
        [172799,1,"D","C",6,1,2,1,1,1,1],
    ])
    devices, states, _ = build_disjoint_panel(2, host, net)
    i = list(devices).index("C")
    assert states[i,0].tolist() == [1,1,1]


def test_stable_fold_is_deterministic():
    assert stable_fold("Comp123") == stable_fold("Comp123")
    assert 0 <= stable_fold("Comp123") < 5


def test_transition_counts_shapes():
    states=np.zeros((2,4,3),dtype=np.uint8)
    states[0,0,0]=1; states[0,1,1]=1
    mask=np.array([True,False])
    neg,pos=transition_counts(states,mask,1)
    assert neg.shape==(8,) and pos.shape==(8,)
    assert int(neg.sum()+pos.sum()) == 3


def test_run_day_guardrails(tmp_path):
    host = tmp_path/"h.bz2"; net = tmp_path/"n.bz2"
    rows=[]
    for t,eid,user in [
        (86400,4624,"User1"),(86410,4624,"Comp1$"),(86420,4625,"SYSTEM"),
        (86700,4688,"User1"),(87000,4625,"User2"),(87300,4689,"SYSTEM")
    ]:
        rows.append({"Time":t,"EventID":eid,"UserName":user,"Computer":"Comp1"})
        rows.append({"Time":t,"EventID":eid,"UserName":user,"Computer":"Comp2"})
    rows.append({"Time":172799,"EventID":4609,"Computer":"Comp1"})
    _write_host(host, rows)
    _write_net(net, [
        [86400,1,"Comp1","Comp2",6,1,2,1,1,1,1],
        [86700,1,"Comp2","Comp1",6,1,2,1,1,1,1],
        [87000,1,"Comp1","Comp2",6,1,2,1,1,1,1],
        [172799,1,"Comp2","Comp1",6,1,2,1,1,1,1],
    ])
    r=run_day(2,host,net)
    assert r["guardrails"]["attack_or_red_team_labels_read"] is False
    assert r["guardrails"]["same_window_edges_allowed"] is False
    assert r["diagnostics"]["host"]["excluded_nonperson_login_events"] >= 2
