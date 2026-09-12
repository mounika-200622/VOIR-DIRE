"""The loop, end to end: a closure comes back, becomes a rule, and the rule
refuses the next closure that looks the same.

If any of these fail, the project does not work, whatever the demo shows.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from voirdire import gate, history, learn, nextstep, templates      # noqa: E402
from voirdire.claim import Claim                                     # noqa: E402
from voirdire.db import Ledger                                       # noqa: E402

import ward as fixture                                               # noqa: E402


@pytest.fixture
def w(tmp_path):
    return fixture.build(tmp_path)


@pytest.fixture
def led(tmp_path):
    led = Ledger(tmp_path / "ledger.db")
    yield led
    led.close()


# ---- what actually happened -------------------------------------------------

def test_history_separates_what_held_from_what_came_back(w):
    back = {c.id for c in history.came_back(w)}
    held = {c.id for c in history.held(w)}
    assert back == {10, 20, 30, 40}, "the four planted failures"
    assert {1, 2, 3, 4} <= held, "the four good closures held"
    assert not (back & held), "a closure cannot both hold and come back"


# ---- the four checks --------------------------------------------------------

def test_nothing_attached_is_caught(w):
    c = Claim.one(w, 10)
    assert templates.fires("needs_evidence", {"evidence": "photo_after"}, c)


def test_a_good_closure_trips_nothing(w):
    c = Claim.one(w, 1)
    for name in templates.TEMPLATES:
        params = {"minutes": 30, "metres": 120}
        assert templates.fires(name, params, c) is None, f"{name} fired on a good closure"


def test_four_minutes_is_caught(w):
    c = Claim.one(w, 20)
    assert templates.fires("needs_time", {"minutes": 30}, c)


def test_a_photo_from_elsewhere_is_caught(w):
    c = Claim.one(w, 30)
    reason = templates.fires("evidence_on_site", {"metres": 120}, c)
    assert reason and "m from where" in reason


def test_closing_one_of_four_is_caught(w):
    c = Claim.one(w, 40)
    reason = templates.fires("not_while_open", {"at_least": 1}, c)
    assert reason and "still open" in reason


# ---- the part that makes blocking defensible --------------------------------

def test_a_rule_that_would_have_refused_a_good_closure_cannot_bind(w, led):
    """The whole safety argument in one test.

    A rule demanding a work_order on every closure would have refused three of
    the four closures that genuinely held. It must come out advisory.
    """
    from voirdire import empanel
    origin = Claim.one(w, 10)
    status, receipt = empanel.empanel(
        led, str(w.resolve()), "needs_evidence",
        {"evidence": "work_order"}, origin)
    assert status == "persuasive", receipt
    assert receipt["false_ids"], "it should name the closures it would have blocked"


def test_a_rule_that_only_catches_the_failure_binds(w, led):
    from voirdire import empanel
    origin = Claim.one(w, 10)
    status, receipt = empanel.empanel(
        led, str(w.resolve()), "needs_evidence",
        {"evidence": "photo_after"}, origin)
    assert status == "binding", receipt
    assert receipt["fire"] == "1/1"
    assert receipt["false"].startswith("0/")


# ---- the loop ---------------------------------------------------------------

def test_learning_then_refusing(w, led):
    filed = learn.learn_ward(led, w)
    assert filed, "four failed closures should produce rules"
    binding = [f for f in filed if f["status"] == "binding"]
    assert binding, "at least one rule should earn the right to refuse"

    # A clerk now tries to close a fresh complaint with nothing attached.
    proposed = Claim.proposed(w, 11, evidence=[], closed_at="2026-07-30T10:00:00Z")
    refused = gate.on(led, w, proposed)
    assert refused, "the gate should refuse a closure with no evidence"
    assert any("photo_after" in v.reason for v in refused)


def test_a_proper_closure_is_allowed_through(w, led):
    learn.learn_ward(led, w)
    proposed = Claim.proposed(
        w, 11,
        evidence=[{"type": "photo_after", "file": "x.txt",
                   "lat": 12.9351, "lon": 77.6241}],
        closed_at="2026-07-30T10:00:00Z")
    assert gate.on(led, w, proposed) == [], "a good closure must not be refused"


# ---- and it says what to do -------------------------------------------------

def test_the_instruction_names_the_actual_place(w):
    c = Claim.one(w, 10)
    said = nextstep.suggest("needs_evidence", {"evidence": "photo_after"}, c)
    assert "3rd Cross" in said, "the landmark comes from the complaint, not a template"


def test_the_duplicate_instruction_names_the_open_complaints(w):
    c = Claim.one(w, 40)
    said = nextstep.suggest("not_while_open", {"at_least": 1}, c)
    assert "41" in said and "42" in said
