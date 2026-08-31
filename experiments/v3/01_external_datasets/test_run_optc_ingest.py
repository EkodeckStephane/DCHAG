from __future__ import annotations

import run_optc_ingest as ingest


def test_temporal_summary_preserves_source_order():
    out = ingest.summarize_timestamps([1000, 1200, 1100, 1400])
    assert out["valid_timestamp_count"] == 4
    assert out["source_order_nondecreasing"] is False
    assert out["min_timestamp_ms"] == 1000
    assert out["max_timestamp_ms"] == 1400
    assert out["span_ms"] == 400


def test_temporal_summary_monotone_sequence():
    out = ingest.summarize_timestamps([1000, 1000, 1200, 1400])
    assert out["source_order_nondecreasing"] is True
    assert out["span_ms"] == 400


def test_temporal_summary_empty_and_singleton():
    empty = ingest.summarize_timestamps([])
    assert empty["valid_timestamp_count"] == 0
    assert empty["source_order_nondecreasing"] is True
    assert empty["min_timestamp_ms"] is None
    assert empty["max_timestamp_ms"] is None
    assert empty["span_ms"] is None

    one = ingest.summarize_timestamps([1234])
    assert one["valid_timestamp_count"] == 1
    assert one["source_order_nondecreasing"] is True
    assert one["min_timestamp_ms"] == 1234
    assert one["max_timestamp_ms"] == 1234
    assert one["span_ms"] is None
