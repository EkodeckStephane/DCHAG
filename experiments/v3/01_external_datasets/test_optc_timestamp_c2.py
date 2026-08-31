from __future__ import annotations

import pytest

from optc_adapter import map_ecar_event, parse_ecar_timestamp_ms


def test_exact_optc_iso_example_to_epoch_ms():
    assert parse_ecar_timestamp_ms("2019-09-23T15:47:55.538-04:00") == 1569268075538


def test_z_timestamp_is_accepted():
    assert parse_ecar_timestamp_ms("2019-09-23T19:47:55.538Z") == 1569268075538


def test_existing_numeric_timestamp_behavior_is_preserved():
    assert parse_ecar_timestamp_ms(1539120748904) == 1539120748904
    assert parse_ecar_timestamp_ms("1539120748904") == 1539120748904


def test_timezone_naive_iso_is_rejected():
    with pytest.raises(ValueError):
        parse_ecar_timestamp_ms("2019-09-23T15:47:55.538")


def test_representative_real_schema_flow_maps_to_h_and_t():
    event = {
        "action": "START",
        "actorID": "472bfd43-b28b-4304-8926-dd344bbdfc91",
        "hostname": "SysClient0874.systemia.com",
        "id": "08d0a314-53e1-4029-adc3-0fdbafe805e3",
        "object": "FLOW",
        "objectID": "ac226bc7-30a6-4ae5-b16c-35accbfc6a48",
        "pid": 868,
        "ppid": 560,
        "principal": r"NT AUTHORITY\NETWORK SERVICE",
        "timestamp": "2019-09-23T15:47:55.538-04:00",
    }
    mapped = map_ecar_event(event)
    assert [x.dchag_type for x in mapped] == ["H", "T"]
    assert all(x.timestamp_ms == 1569268075538 for x in mapped)


def test_invalid_nonfinite_and_boolean_timestamps_are_rejected():
    for value in [True, False, float("nan"), float("inf"), "nan", "inf"]:
        with pytest.raises(ValueError):
            parse_ecar_timestamp_ms(value)
