"""Conservative OpTC eCAR -> DCHAG v3 typed-observation adapter.

This adapter maps only directly observable fields. It never reads red-team ground truth
and never invents defensive-control interventions from observational telemetry.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping


@dataclass(frozen=True)
class TypedObservation:
    timestamp_ms: int
    dchag_type: str
    source_object: str
    source_action: str
    principal: str | None
    hostname: str | None
    actor_id: str | None
    object_id: str | None
    pid: int | None
    ppid: int | None
    evidence_role: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return None if value < 0 else value


def map_ecar_event(event: Mapping[str, Any]) -> list[TypedObservation]:
    """Map one eCAR event to one or more conservative DCHAG observations.

    H: only a user-associated observable action when ``principal`` is present.
    P: process/activity transition when the event concerns a process.
    T: technical host/network/file/registry/etc. event.
    C: never inferred here; external observational telemetry has no intervention oracle.
    """
    ts = event.get("timestamp_ms", event.get("timestamp"))
    if ts is None:
        raise ValueError("eCAR event lacks timestamp/timestamp_ms")
    ts = int(ts)

    obj = str(event.get("object", "UNKNOWN")).upper()
    action = str(event.get("action", "UNKNOWN")).upper()
    principal = event.get("principal")
    principal = str(principal) if principal not in (None, "") else None
    hostname = event.get("hostname")
    hostname = str(hostname) if hostname not in (None, "") else None
    actor_id = event.get("actorID")
    actor_id = str(actor_id) if actor_id not in (None, "") else None
    object_id = event.get("objectID")
    object_id = str(object_id) if object_id not in (None, "") else None
    pid = _int_or_none(event.get("pid"))
    ppid = _int_or_none(event.get("ppid"))

    base = dict(
        timestamp_ms=ts,
        source_object=obj,
        source_action=action,
        principal=principal,
        hostname=hostname,
        actor_id=actor_id,
        object_id=object_id,
        pid=pid,
        ppid=ppid,
    )

    out: list[TypedObservation] = []
    if principal is not None:
        out.append(TypedObservation(dchag_type="H", evidence_role="user_associated_action", **base))

    if obj == "PROCESS":
        out.append(TypedObservation(dchag_type="P", evidence_role="process_transition", **base))
    else:
        out.append(TypedObservation(dchag_type="T", evidence_role="technical_event", **base))

    return out
