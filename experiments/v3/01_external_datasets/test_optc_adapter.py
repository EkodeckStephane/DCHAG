from optc_adapter import map_ecar_event


def test_process_with_principal_maps_to_h_and_p():
    event = {
        "timestamp": 1539120748904,
        "hostname": "H1",
        "object": "PROCESS",
        "action": "CREATE",
        "actorID": "a",
        "objectID": "o",
        "pid": 10,
        "ppid": 5,
        "principal": r"H1\user",
    }
    mapped = map_ecar_event(event)
    assert [x.dchag_type for x in mapped] == ["H", "P"]
    assert mapped[0].evidence_role == "user_associated_action"
    assert mapped[1].evidence_role == "process_transition"


def test_technical_event_without_principal_maps_only_to_t():
    event = {
        "timestamp_ms": 2,
        "hostname": "H2",
        "object": "FLOW",
        "action": "START",
        "actorID": "a2",
        "objectID": "o2",
        "pid": -1,
        "ppid": -1,
    }
    mapped = map_ecar_event(event)
    assert [x.dchag_type for x in mapped] == ["T"]
    assert mapped[0].pid is None
    assert mapped[0].ppid is None


def test_file_event_with_principal_maps_to_h_and_t():
    event = {
        "timestamp_ms": 3,
        "hostname": "H3",
        "object": "FILE",
        "action": "OPEN",
        "principal": r"H3\u",
        "pid": "7",
        "ppid": "not-an-int",
    }
    mapped = map_ecar_event(event)
    assert [x.dchag_type for x in mapped] == ["H", "T"]
    assert mapped[1].pid == 7
    assert mapped[1].ppid is None


def test_missing_timestamp_is_rejected():
    try:
        map_ecar_event({"object": "PROCESS"})
    except ValueError:
        return
    raise AssertionError("missing timestamp must be rejected")
