"""A rule is not allowed to refuse anything until it has been tested.

This is the file the whole project turns on. Anyone can write a rule that
blocks things; the hard part is earning the right to block, and the only
honest way to earn it is to show the rule works on evidence that already
exists.

So before a rule can refuse a closure it is replayed against the ward's own
records. It must do two things:

  1. fire on the closure that produced it - a rule that cannot catch its own
     case will not catch the next one;
  2. stay silent on every closure that HELD - because a rule that would have
     refused a repair that was genuinely finished is a rule that sends a crew
     back to a road that is already fixed.

Fail either and it is demoted to advice. It still speaks. It cannot stop
anyone. That distinction is what makes it safe to leave switched on, and it is
the reason a tool that refuses things does not get uninstalled in week two.
"""
from __future__ import annotations

import json
from pathlib import Path

from .claim import Claim
from .db import Ledger
from . import history, templates


def _origin_id(case: dict) -> int:
    """Which complaint this case was filed about.

    file_case() writes it into `detail` as JSON. It is not a column because a
    case in the code version of this system points at files, not at a row - and
    the ledger schema is shared with that one deliberately.
    """
    try:
        return int(json.loads(case.get("detail") or "{}").get("complaint_id") or 0)
    except (ValueError, TypeError):
        return 0


def empanel(led: Ledger, ward: str, template: str, params: dict,
            origin: Claim, sample: int = 60) -> tuple[str, dict]:
    """Return (status, receipt). Status is 'binding' or 'persuasive'."""
    if not templates.valid(template, params):
        return "persuasive", {"error": "rule is missing a value it needs"}

    fired_on_origin = templates.fires(template, params, origin) is not None

    wrongly: list[int] = []
    tested = 0
    for past in history.held(Path(ward))[:sample]:
        if past.id == origin.id:
            continue
        tested += 1
        if templates.fires(template, params, past) is not None:
            wrongly.append(past.id)

    receipt = {
        "fire": f"{int(fired_on_origin)}/1",
        "false": f"{len(wrongly)}/{tested}",
        "false_ids": wrongly[:5],
        "tested": tested,
    }

    if not tested:
        # Nothing to be wrong about yet. Advice, until the ward has a history.
        receipt["note"] = "no closure has held long enough to test against yet"
        return "persuasive", receipt
    if fired_on_origin and not wrongly:
        return "binding", receipt
    return "persuasive", receipt


def reconsider(led: Ledger, ward: str) -> list[int]:
    """Advisory rules get another chance as the record grows.

    A rule demoted because there was nothing to test it against is not wrong,
    it is untested. Every closure that holds is new evidence, so the ones
    waiting are retried rather than left in advice forever.
    """
    promoted = []
    for h in led.holdings(ward=ward, status="persuasive"):
        if h["template"] not in templates.TEMPLATES:
            continue
        case = led.case(h["case_id"])
        if not case:
            continue
        origin = Claim.one(Path(ward), _origin_id(case))
        if origin is None:
            continue
        status, receipt = empanel(led, ward, h["template"], h["params"], origin)
        if status == "binding":
            led.set_status(h["id"], "binding", receipt)
            promoted.append(h["id"])
    return promoted
