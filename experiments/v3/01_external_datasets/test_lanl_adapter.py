from lanl_adapter import map_host_event, map_network_flow


def types(obs):
    return [x.dchag_type for x in obs]


def test_official_kerberos_sample_is_user_associated_and_technical():
    event = {
        "EventID": 4769,
        "UserName": "User624729",
        "ServiceName": "Comp883934$",
        "DomainName": "Domain002",
        "Status": "0x0",
        "Source": "Comp309534",
        "Computer": "ActiveDirectory",
        "Time": 2,
    }
    obs = map_host_event(event)
    assert types(obs) == ["H", "T"]
    assert obs[0].evidence_role == "user_associated_action"
    assert obs[1].evidence_role == "technical_host_event"
    assert all(x.source_device == "Comp309534" for x in obs)


def test_process_start_with_user_is_h_plus_p():
    event = {
        "EventID": 4688,
        "UserName": "User1",
        "ProcessName": "example.exe",
        "ProcessID": "123",
        "ParentProcessID": "77",
        "LogHost": "Comp1",
        "Time": 100,
    }
    obs = map_host_event(event)
    assert types(obs) == ["H", "P"]
    assert obs[1].process_id == "123"
    assert obs[1].parent_process_id == "77"


def test_process_start_without_user_is_p_only():
    event = {"EventID": 4688, "ProcessName": "svc.exe", "LogHost": "Comp1", "Time": 101}
    obs = map_host_event(event)
    assert types(obs) == ["P"]


def test_system_event_is_technical_only():
    obs = map_host_event({"EventID": 4608, "LogHost": "Comp1", "Time": 102})
    assert types(obs) == ["T"]


def test_official_network_sample_is_technical_flow():
    row = [761, 4434, "Comp132598", "Comp817788", 6, "Port12597", 22, 89159, 85257, 15495068, 69768940]
    obs = map_network_flow(row)
    assert types(obs) == ["T"]
    assert obs[0].evidence_role == "network_flow"
    assert obs[0].source_device == "Comp132598"
    assert obs[0].destination_device == "Comp817788"


def test_no_intervention_type_is_ever_emitted():
    events = [
        {"EventID": 4624, "UserName": "U1", "Time": 1},
        {"EventID": 4688, "UserName": "U1", "Time": 2},
        {"EventID": 4608, "Time": 3},
    ]
    emitted = [x.dchag_type for event in events for x in map_host_event(event)]
    emitted += [x.dchag_type for x in map_network_flow([4, 1, "C1", "C2"])]
    assert "C" not in emitted
