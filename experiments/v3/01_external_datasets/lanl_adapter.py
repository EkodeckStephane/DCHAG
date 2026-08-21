"""Conservative LANL Unified Host/Network -> DCHAG v3 adapter.

Maps only directly observable host/network fields. No red-team labels or
intervention truth are read or inferred.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping, Sequence

AUTH_SESSION_EVENT_IDS = {
    4768, 4769, 4770, 4774, 4776,
    4624, 4625, 4634, 4647, 4648, 4672,
    4800, 4801, 4802, 4803,
}
PROCESS_EVENT_IDS = {4688, 4689}
SYSTEM_EVENT_IDS = {4608, 4609, 1100}


@dataclass(frozen=True)
class LanlObservation:
    timestamp_s: int
    dchag_type: str
    evidence_role: str
    source_kind: str
    event_id: int | None = None
    user: str | None = None
    log_host: str | None = None
    source_device: str | None = None
    destination_device: str | None = None
    process_name: str | None = None
    process_id: str | None = None
    parent_process_id: str | None = None
    logon_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _time(record: Mapping[str, Any]) -> int:
    value = record.get("Time", record.get("time"))
    if value is None:
        raise ValueError("LANL record lacks Time/time")
    return int(value)


def map_host_event(event: Mapping[str, Any]) -> list[LanlObservation]:
    ts = _time(event)
    try:
        event_id = int(event["EventID"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("LANL host event lacks valid EventID") from exc

    user = _text(event.get("UserName")) or _text(event.get("SubjectUserName"))
    base = dict(
        timestamp_s=ts,
        source_kind="host",
        event_id=event_id,
        user=user,
        log_host=_text(event.get("LogHost", event.get("Computer"))),
        source_device=_text(event.get("Source")),
        destination_device=_text(event.get("Destination")),
        process_name=_text(event.get("ProcessName")),
        process_id=_text(event.get("ProcessID")),
        parent_process_id=_text(event.get("ParentProcessID")),
        logon_id=_text(event.get("LogonID", event.get("SubjectLogonID"))),
    )

    out: list[LanlObservation] = []
    if user is not None and (event_id in AUTH_SESSION_EVENT_IDS or event_id in PROCESS_EVENT_IDS):
        out.append(LanlObservation(dchag_type="H", evidence_role="user_associated_action", **base))

    if event_id in PROCESS_EVENT_IDS:
        out.append(LanlObservation(dchag_type="P", evidence_role="process_transition", **base))
    else:
        out.append(LanlObservation(dchag_type="T", evidence_role="technical_host_event", **base))
    return out


def map_network_flow(fields: Mapping[str, Any] | Sequence[Any]) -> list[LanlObservation]:
    if isinstance(fields, Mapping):
        ts = _time(fields)
        src = _text(fields.get("SrcDevice"))
        dst = _text(fields.get("DstDevice"))
    else:
        if len(fields) < 4:
            raise ValueError("LANL network flow requires at least Time, Duration, SrcDevice, DstDevice")
        ts = int(fields[0])
        src = _text(fields[2])
        dst = _text(fields[3])

    return [LanlObservation(
        timestamp_s=ts,
        dchag_type="T",
        evidence_role="network_flow",
        source_kind="network",
        source_device=src,
        destination_device=dst,
    )]
