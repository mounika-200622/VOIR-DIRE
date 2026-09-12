"""What actually happened to the closures a ward has already filed.

A closure HELD if nobody reported the same thing again afterwards. It CAME BACK
if they did. That is the only ground truth in this project, it is read off the
ward's own records, and it is knowable only in hindsight.

Which is the whole point of keeping it here and nowhere near the gate. The gate
decides with what a clerk can see at the moment of closing. This module knows
how it turned out, and is allowed to be used for exactly two things: making a
case out of a closure that came back, and testing a proposed rule against
closures that held.
"""
from __future__ import annotations

from pathlib import Path

from .claim import Claim, when


def label(ward: Path) -> list[tuple[Claim, bool]]:
    """Every filed closure, paired with whether it held.

    True means it held. False means the same asset was reported again after it
    was declared resolved.
    """
    claims = Claim.load_all(ward)
    reports: dict[str, list] = {}
    for claim in claims:
        for c in claim.siblings:
            asset = c.get("asset_id")
            seen = when(c.get("reported_at"))
            if asset and seen:
                reports.setdefault(asset, []).append(seen)
        break                      # siblings is the same list on every claim

    out = []
    for claim in claims:
        closed = when(claim.closure.get("closed_at"))
        again = [t for t in reports.get(claim.asset, []) if closed and t > closed]
        out.append((claim, not again))
    return out


def came_back(ward: Path) -> list[Claim]:
    """The closures that did not hold. Each one is a case waiting to be filed."""
    return [c for c, held in label(ward) if not held]


def held(ward: Path) -> list[Claim]:
    """The closures that did hold.

    These are what a proposed rule is tested against. A rule that would have
    refused one of these is a rule that would have sent a crew back to a road
    that was already fixed, and it does not get to block anything.
    """
    return [c for c, ok in label(ward) if ok]
