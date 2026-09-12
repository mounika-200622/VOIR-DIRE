"""What to do about it.

Refusing something is the easy half and the useless half. A clerk told "this
closure is invalid" is a clerk who files it again tomorrow with the same
problem; a clerk told "photograph the pit outside the 3rd Cross bus stop and
attach it" has been given their afternoon back.

Every line here is built out of the ward's own record - the landmark the
citizen wrote down, the coordinates they reported, the complaint numbers
already sitting open on that asset. Nothing is a template with a blank in it,
because a generic instruction is just a refusal with more words.
"""
from __future__ import annotations

from .claim import Claim


def _where(claim: Claim) -> str:
    loc = claim.complaint.get("location") or {}
    mark = loc.get("landmark")
    if mark:
        return str(mark)
    lat, lon = loc.get("lat"), loc.get("lon")
    if lat is not None and lon is not None:
        return f"{lat:.4f}, {lon:.4f}"
    return "the reported location"


def suggest(template: str, params: dict, claim: Claim) -> str | None:
    p = params or {}

    if template == "needs_evidence":
        want = p.get("evidence", "photo_after")
        if want == "photo_after":
            return f"photograph the finished work at {_where(claim)} and attach it"
        return f"attach the {want.replace('_', ' ')} for complaint {claim.id}"

    if template == "needs_time":
        mins = float(p.get("minutes", 5))
        done = claim.minutes_to_close()
        if done is not None:
            return (f"this was marked done {done:.0f} minutes after assignment; "
                    f"confirm the work is finished before closing")
        return f"record when the crew was assigned, then close after {mins:.0f} minutes"

    if template == "evidence_on_site":
        limit = float(p.get("metres", 120))
        shots = claim.evidence(p.get("evidence", "photo_after"))
        far = [d for d in (claim.metres_from_site(e) for e in shots) if d is not None]
        if far:
            return (f"the photo is {min(far):.0f}m away; take one within "
                    f"{limit:.0f}m of {_where(claim)}")
        return f"take the photo at {_where(claim)} with location switched on"

    if template == "not_while_open":
        others = claim.open_on_same_asset()
        if others:
            ids = ", ".join(str(o.get("id")) for o in others[:4])
            return (f"complaint(s) {ids} are the same {claim.kind or 'asset'}; "
                    f"link them to {claim.asset} and close them together")
        return f"check what else is open on {claim.asset} before closing"

    return None
