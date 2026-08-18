from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class EventRecord:
    timestamp: int
    actor: str
    action: str
    resource: str
    attributes: dict[str,Any]

@dataclass(frozen=True)
class EvidenceItem:
    time: int
    node: str
    value: int|None
    rule_id: str
    source_fields: tuple[str,...]

class DeterministicEventMapper:
    """Simple exact-match adapter used as reference plumbing; context adapters supply rules."""
    def __init__(self,rules:list[dict]):
        self.rules=list(rules)
    def map(self,event:EventRecord)->list[EvidenceItem]:
        out=[]
        for r in self.rules:
            if r.get("action") not in (None,event.action): continue
            if r.get("resource") not in (None,event.resource): continue
            out.append(EvidenceItem(event.timestamp,r["node"],int(r.get("value",1)),r["id"],("action","resource")))
        return out
