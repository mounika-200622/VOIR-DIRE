"""What is being claimed, in the only shape a check needs.

A ward marks a complaint resolved. That claim is the thing we judge, and it is
made of three parts: the complaint as it was reported, the closure as it was
filed, and whatever evidence came attached.

Everything here is read off the ward's own data files. Nothing is inferred, and
nothing asks a model - a check that needs a language model to decide whether a
photo exists is not a check.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

STAMP = "%Y-%m-%dT%H:%M:%SZ"


def when(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.strptime(text, STAMP)
    except ValueError:
        return None


@dataclass
class Claim:
    """One closure, waiting to be allowed or refused."""

    ward: Path
    complaint: dict
    closure: dict
    siblings: list[dict] = field(default_factory=list)   # everything else reported
    closed_ids: set[int] = field(default_factory=set)    # complaints already closed

    # ---- the questions a check asks -------------------------------------

    @property
    def id(self) -> int:
        return int(self.complaint.get("id", 0))

    @property
    def kind(self) -> str:
        return str(self.complaint.get("kind", ""))

    @property
    def asset(self) -> str:
        return str(self.complaint.get("asset_id", ""))

    def evidence(self, kind: str | None = None) -> list[dict]:
        got = self.closure.get("evidence") or []
        return [e for e in got if kind is None or e.get("type") == kind]

    def minutes_to_close(self) -> float | None:
        """How long between being assigned and being declared done."""
        start = when(self.complaint.get("assigned_at")) or when(self.complaint.get("reported_at"))
        end = when(self.closure.get("closed_at"))
        if not start or not end:
            return None
        return (end - start).total_seconds() / 60.0

    def metres_from_site(self, ev: dict) -> float | None:
        """Rough distance between the reported place and where evidence was taken.

        Flat-earth arithmetic on purpose. At the scale of one ward the error is
        metres, it needs no dependency, and a check that cannot run offline on a
        clerk's laptop will not be run at all.
        """
        loc = self.complaint.get("location") or {}
        lat, lon = loc.get("lat"), loc.get("lon")
        if lat is None or lon is None or ev.get("lat") is None or ev.get("lon") is None:
            return None
        dlat = (float(ev["lat"]) - float(lat)) * 111_320
        dlon = (float(ev["lon"]) - float(lon)) * 111_320 * 0.68   # cos(lat) near 12.9N
        return (dlat ** 2 + dlon ** 2) ** 0.5

    def open_on_same_asset(self) -> list[dict]:
        """Other complaints about the same thing that nobody has closed."""
        if not self.asset:
            return []
        closed_at = when(self.closure.get("closed_at"))
        out = []
        for other in self.siblings:
            if other.get("id") == self.id or other.get("asset_id") != self.asset:
                continue
            if other.get("id") in self.closed_ids:
                continue
            seen = when(other.get("reported_at"))
            if closed_at and seen and seen < closed_at:
                out.append(other)
        return out

    # ---- loading --------------------------------------------------------

    @classmethod
    def load_all(cls, ward: Path) -> list["Claim"]:
        """Every closure this ward has filed."""
        ward = Path(ward)
        complaints = json.loads((ward / "data" / "complaints.json").read_text(encoding="utf-8"))
        closures = json.loads((ward / "data" / "closures.json").read_text(encoding="utf-8"))
        closed_ids = {c["complaint_id"] for c in closures}
        by_id = {c["id"]: c for c in complaints}
        out = []
        for closure in closures:
            complaint = by_id.get(closure["complaint_id"])
            if complaint is None:
                continue
            out.append(cls(ward=ward, complaint=complaint, closure=closure,
                           siblings=complaints, closed_ids=closed_ids))
        return out

    @classmethod
    def one(cls, ward: Path, complaint_id: int) -> "Claim | None":
        for claim in cls.load_all(ward):
            if claim.id == complaint_id:
                return claim
        return None

    @classmethod
    def proposed(cls, ward: Path, complaint_id: int, evidence: list[dict],
                 closed_at: str | None = None) -> "Claim":
        """A closure nobody has filed yet - the one the gate is asked about.

        This is the whole point of running before the fact rather than after:
        the clerk has not pressed the button, so refusing costs nobody a
        reopened complaint three weeks later.
        """
        ward = Path(ward)
        complaints = json.loads((ward / "data" / "complaints.json").read_text(encoding="utf-8"))
        closures = json.loads((ward / "data" / "closures.json").read_text(encoding="utf-8"))
        by_id = {c["id"]: c for c in complaints}
        if complaint_id not in by_id:
            raise KeyError(f"no complaint {complaint_id} in {ward.name}")
        closure = {"complaint_id": complaint_id, "evidence": evidence,
                   "closed_at": closed_at or datetime.utcnow().strftime(STAMP)}
        return cls(ward=ward, complaint=by_id[complaint_id], closure=closure,
                   siblings=complaints,
                   closed_ids={c["complaint_id"] for c in closures})
