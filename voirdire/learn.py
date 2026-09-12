"""Turning a closure that came back into a rule that stops the next one.

There is no model here and there does not need to be one. A closure that
failed has a small number of visible things wrong with it - nothing attached,
closed in four minutes, a photo from the next street, three open complaints on
the same asset - and each of those is one of the four shapes in templates.py
with its blanks filled from this ward's own numbers.

The thresholds are the important part. They are not chosen; they are measured.
"how long has this kind of job actually taken here, when it stuck?" is a
question the ward's records answer, and a rule built that way can be argued
with using the same records.
"""
from __future__ import annotations

import json
from pathlib import Path

from .claim import Claim
from .db import Ledger
from . import empanel, history, templates


def _typical_minutes(ward: Path, kind: str) -> float | None:
    """The quickest this kind of job has ever taken and still held.

    Anything faster than every honest repair on record is worth a question. If
    the ward has no history for this kind of work, we have no business setting
    a threshold and return nothing.
    """
    times = []
    for claim in history.held(ward):
        if kind and claim.kind != kind:
            continue
        mins = claim.minutes_to_close()
        if mins is not None:
            times.append(mins)
    if len(times) < 3:
        return None
    return max(5.0, round(min(times) * 0.5))


def propose(ward: Path, claim: Claim) -> list[tuple[str, dict, str]]:
    """What this failed closure suggests, as (template, params, says)."""
    out: list[tuple[str, dict, str]] = []
    kind = claim.kind

    if not claim.evidence("photo_after"):
        out.append(("needs_evidence", {"kind": kind, "evidence": "photo_after"},
                    f"Closing a {kind} needs a photo of the finished work."))

    floor = _typical_minutes(ward, kind)
    mins = claim.minutes_to_close()
    if floor is not None and mins is not None and mins < floor:
        out.append(("needs_time", {"kind": kind, "minutes": floor},
                    f"A {kind} is not finished in under {floor:.0f} minutes."))

    shots = claim.evidence("photo_after")
    if shots:
        far = [d for d in (claim.metres_from_site(e) for e in shots) if d is not None]
        if far and min(far) > 120:
            out.append(("evidence_on_site", {"metres": 120},
                        "The photo has to be taken where the complaint was."))

    if claim.open_on_same_asset():
        out.append(("not_while_open", {"at_least": 1},
                    "Do not close one complaint while the same asset has others open."))
    return out


def file_case(led: Ledger, ward: Path, claim: Claim) -> list[dict]:
    """Record what went wrong, and try to make rules out of it.

    Every proposal goes through empanelment before it gets any authority, so
    this cannot quietly hand a rule the power to refuse things.
    """
    ward = Path(ward)
    scope = str(ward.resolve())
    filed: list[dict] = []

    run_id = led.open_run(scope, f"closure {claim.id} came back", arm="live")
    led.close_run(run_id, "fail")
    case_id = led.file_case(
        run_id, scope, "reopened", "high",
        f"complaint {claim.id} was closed, then reported again",
        [claim.asset], json.dumps({"complaint_id": claim.id}))

    for template, params, says in propose(ward, claim):
        status, receipt = empanel.empanel(led, scope, template, params, claim)
        hid = led.establish(case_id, scope, template, params, says,
                            status=status, empanel=receipt)
        filed.append({"id": hid, "template": template, "params": params,
                      "says": says, "status": status, "empanel": receipt,
                      "rule": templates.render(template, params)})
    return filed


def learn_ward(led: Ledger, ward: Path) -> list[dict]:
    """Read everything that already went wrong here, and rule on it."""
    out = []
    for claim in history.came_back(Path(ward)):
        out += file_case(led, ward, claim)
    return out
