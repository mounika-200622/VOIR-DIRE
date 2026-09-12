"""The shapes a rule can take.

Four of them, and that is deliberate. A rule is not free text and it is not
code someone wrote at three in the morning - it is one of these shapes with its
blanks filled in, which means every rule can be printed, argued with, replayed
against history, and switched off.

Each check answers one question about one closure and returns either None,
meaning it has nothing to say, or a sentence explaining what is wrong. No check
asks a model. No check reaches the network. Given the same closure they give
the same answer every time, which is the only reason the numbers later on mean
anything.
"""
from __future__ import annotations

from typing import Callable

from .claim import Claim


def needs_evidence(c: Claim, p: dict) -> str | None:
    """You closed it without showing anything.

    The commonest closure in every dataset we have looked at: marked resolved,
    nothing attached. Nobody is accusing anyone of anything - a crew that fixed
    a road and forgot the photo trips this too, which is exactly why the fix is
    one sentence rather than an investigation.
    """
    if p.get("kind") and c.kind != p["kind"]:
        return None
    want = p.get("evidence", "photo_after")
    if c.evidence(want):
        return None
    got = {e.get("type") for e in c.evidence()}
    had = f"only {', '.join(sorted(x for x in got if x))}" if got else "nothing attached"
    return f"no {want} on complaint {c.id}; {had}"


def needs_time(c: Claim, p: dict) -> str | None:
    """You closed it faster than the work takes.

    A pothole is not repaired in four minutes. This is the check that catches a
    closure filed to clear a queue rather than to fix a road, and the threshold
    comes from what this kind of job has actually taken in this ward, not from
    a number we picked.
    """
    if p.get("kind") and c.kind != p["kind"]:
        return None
    mins = c.minutes_to_close()
    floor = float(p.get("minutes", 5))
    if mins is None or mins >= floor:
        return None
    return (f"closed {mins:.0f} minutes after assignment; "
            f"{c.kind or 'this work'} has never taken under {floor:.0f}")


def evidence_on_site(c: Claim, p: dict) -> str | None:
    """Your photo is from somewhere else.

    The subtle one, and the reason it matters: a closure with a photo attached
    looks complete to every dashboard ever built. Checking the photo came from
    the reported place is the difference between evidence and paperwork.
    """
    limit = float(p.get("metres", 120))
    shots = c.evidence(p.get("evidence", "photo_after"))
    if not shots:
        return None
    placed = [(e, c.metres_from_site(e)) for e in shots]
    near = [d for _, d in placed if d is not None and d <= limit]
    if near:
        return None
    far = [d for _, d in placed if d is not None]
    if not far:
        return f"the photo on complaint {c.id} has no location on it"
    return (f"nearest photo is {min(far):.0f}m from where complaint {c.id} "
            f"was reported; the limit is {limit:.0f}m")


def not_while_open(c: Claim, p: dict) -> str | None:
    """Somebody else is still reporting the same thing.

    Four complaints about one stretch of road, one gets closed, three stay
    open. The road is not fixed. Someone's ticket is.
    """
    others = c.open_on_same_asset()
    floor = int(p.get("at_least", 1))
    if len(others) < floor:
        return None
    ids = ", ".join(str(o.get("id")) for o in others[:3])
    more = "" if len(others) <= 3 else f" and {len(others) - 3} more"
    return (f"{len(others)} complaint(s) about {c.asset} are still open: "
            f"{ids}{more}")


TEMPLATES: dict[str, Callable[[Claim, dict], str | None]] = {
    "needs_evidence": needs_evidence,
    "needs_time": needs_time,
    "evidence_on_site": evidence_on_site,
    "not_while_open": not_while_open,
}

REQUIRED = {
    "needs_evidence": (),
    "needs_time": ("minutes",),
    "evidence_on_site": ("metres",),
    "not_while_open": (),
}


def fires(template: str, params: dict, claim: Claim) -> str | None:
    fn = TEMPLATES.get(template)
    if fn is None:
        return None
    try:
        return fn(claim, params or {})
    except Exception:
        # A broken check abstains. It never blocks a closure by falling over,
        # because a gate that fires when it is confused fires on everything.
        return None


def valid(template: str, params: dict) -> bool:
    if template not in TEMPLATES:
        return False
    return all(k in (params or {}) for k in REQUIRED[template])


def render(template: str, params: dict) -> str:
    """The rule in its machine form, so nobody has to trust a summary."""
    p = params or {}
    kind = p.get("kind", "any")
    if template == "needs_evidence":
        return f"needs_evidence( {kind} : {p.get('evidence', 'photo_after')} )"
    if template == "needs_time":
        return f"needs_time( {kind} : >= {p.get('minutes')} min )"
    if template == "evidence_on_site":
        return f"evidence_on_site( <= {p.get('metres')} m )"
    if template == "not_while_open":
        return f"not_while_open( same asset, >= {p.get('at_least', 1)} )"
    return template
