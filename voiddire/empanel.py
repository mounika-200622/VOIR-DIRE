"""A holding is not binding until it has been tested against history.

It MUST fire on the case that produced it, and it MUST NOT fire on the stored
working trees of past successful runs. Fail either and it is demoted to
persuasive authority, where being wrong costs nothing.
"""
from __future__ import annotations

from pathlib import Path

from .change import Change
from .db import Ledger
from . import artifacts, templates


def empanel(led: Ledger, repo: str, template: str, params: dict,
            origin: Change, sample: int = 40) -> tuple[str, dict]:
    """Return (status, receipt)."""
    if not templates.valid(template, params):
        return "persuasive", {"error": "template parameters incomplete"}

    fired_on_origin = templates.fires(template, params, origin) is not None

    false_positives: list[int] = []
    tested = 0
    for run in led.successful_runs(repo, limit=sample):
        past = artifacts.load(Path(repo), run["id"])
        if past is None:
            continue
        tested += 1
        if templates.fires(template, params, past) is not None:
            false_positives.append(run["id"])

    receipt = {
        "fire": f"{int(fired_on_origin)}/1",
        "false": f"{len(false_positives)}/{tested}",
        "false_ids": false_positives[:5],
        "tested": tested,
    }
    if not tested:
        receipt["note"] = "no successful run to test against yet"
        return "persuasive", receipt
    if fired_on_origin and not false_positives:
        return "binding", receipt
    return "persuasive", receipt


def reconsider(led: Ledger, repo: str) -> list[int]:
    """New evidence arrives with every passing run. Advisory holdings get retried."""
    promoted = []
    for h in led.holdings(repo=repo, status="persuasive"):
        if h["template"] not in templates.TEMPLATES:
            continue
        case = led.case(h["case_id"])
        origin = artifacts.load(Path(repo), case["run_id"]) if case else None
        if origin is None:
            continue
        status, receipt = empanel(led, repo, h["template"], h["params"], origin)
        if status == "binding":
            led.set_status(h["id"], "binding", receipt)
            promoted.append(h["id"])
    return promoted
