"""The panel is what a person watches, and it has to show a rule staying silent.

A screen that only ever renders refusals cannot render a closure being cleared,
and a clerk who only sees the tool when it says no will believe it says no to
everything. So every rule gets a seat whether it fires or not.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from voirdire import empanel, learn, panel                            # noqa: E402
from voirdire.claim import Claim                                       # noqa: E402
from voirdire.db import Ledger                                         # noqa: E402

import ward as fixture                                                 # noqa: E402


@pytest.fixture
def w(tmp_path):
    return fixture.build(tmp_path)


@pytest.fixture
def led(tmp_path):
    led = Ledger(tmp_path / "ledger.db")
    yield led
    led.close()


def test_a_cleared_closure_still_shows_every_rule(w, led):
    learn.learn_ward(led, w)
    good = Claim.proposed(
        w, 11,
        evidence=[{"type": "photo_after", "file": "x.txt",
                   "lat": 12.9351, "lon": 77.6241}],
        closed_at="2026-07-30T10:00:00Z")
    sitting = panel.sit(led, str(w.resolve()), good)
    assert not sitting.halted
    assert sitting.seats, "a cleared closure must still show the rules that cleared it"
    assert all(s.verdict == panel.CLEAR for s in sitting.seats)


def test_a_refusal_carries_its_instruction(w, led):
    learn.learn_ward(led, w)
    bare = Claim.proposed(w, 11, evidence=[], closed_at="2026-07-30T10:00:00Z")
    sitting = panel.sit(led, str(w.resolve()), bare)
    halts = [s for s in sitting.seats if s.verdict == panel.HALT]
    assert halts, "nothing attached should halt"
    assert all(s.next for s in halts), "a refusal with no next step is half a tool"
    assert "3rd Cross" in halts[0].next


def test_the_panel_names_what_it_looked_at(w, led):
    learn.learn_ward(led, w)
    c = Claim.proposed(w, 11, evidence=[], closed_at="2026-07-30T10:00:00Z")
    sitting = panel.sit(led, str(w.resolve()), c)
    assert "A-BARE" in sitting.touched and "complaint 11" in sitting.touched


def test_an_untested_rule_is_retried_as_the_record_grows(w, led):
    """reconsider() has to be able to find the closure a case came from.

    It reads the complaint id back out of the case detail. When that broke, it
    silently promoted nothing, forever, and looked exactly like a project where
    no advisory rule had ever earned promotion.
    """
    learn.learn_ward(led, w)
    advisory = [h for h in led.holdings(ward=str(w.resolve()))
                if h["status"] == "persuasive"]
    for h in advisory:
        case = led.case(h["case_id"])
        assert empanel._origin_id(case), "the case must remember its complaint"
        assert Claim.one(w, empanel._origin_id(case)) is not None
    assert empanel.reconsider(led, str(w.resolve())) is not None
