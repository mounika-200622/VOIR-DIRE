from pathlib import Path

from voiddire import artifacts, empanel
from voiddire.change import Change
from voiddire.db import Ledger


def led(tmp_path):
    return Ledger(tmp_path / ".voiddire" / "ledger.db")


def test_a_holding_that_does_not_fire_on_its_own_case_is_not_binding(tmp_path):
    L = led(tmp_path)
    origin = Change(repo=tmp_path, touched=["models/a.py", "migrations/1.py"])
    status, receipt = empanel.empanel(L, str(tmp_path), "co_change",
                                      {"trigger": "models/*.py", "required": "migrations/**"}, origin)
    assert status == "persuasive"
    assert receipt["fire"] == "0/1"


def test_a_holding_that_fires_on_past_successes_is_not_binding(tmp_path):
    L = led(tmp_path)
    repo = str(tmp_path)
    # a past run that passed while touching models/ and no migration
    rid = L.open_run(repo, "past task")
    L.close_run(rid, "pass")
    artifacts.save(tmp_path, rid, Change(repo=tmp_path, touched=["models/old.py"]))

    origin = Change(repo=tmp_path, touched=["models/a.py"])
    status, receipt = empanel.empanel(L, repo, "co_change",
                                      {"trigger": "models/*.py", "required": "migrations/**"}, origin)
    assert status == "persuasive"
    assert receipt["false"].startswith("1/")


def test_a_clean_holding_is_binding(tmp_path):
    L = led(tmp_path)
    repo = str(tmp_path)
    rid = L.open_run(repo, "past task")
    L.close_run(rid, "pass")
    artifacts.save(tmp_path, rid, Change(repo=tmp_path, touched=["docs/readme.md"]))

    origin = Change(repo=tmp_path, touched=["models/a.py"])
    status, receipt = empanel.empanel(L, repo, "co_change",
                                      {"trigger": "models/*.py", "required": "migrations/**"}, origin)
    assert status == "binding"
    assert receipt == {"fire": "1/1", "false": "0/1", "false_ids": [], "tested": 1}


def test_with_no_history_a_holding_is_only_advisory(tmp_path):
    L = led(tmp_path)
    origin = Change(repo=tmp_path, touched=["models/a.py"])
    status, receipt = empanel.empanel(L, str(tmp_path), "co_change",
                                      {"trigger": "models/*.py", "required": "migrations/**"}, origin)
    assert status == "persuasive", "binding is a claim that it was tested"
    assert receipt["tested"] == 0 and "note" in receipt


def test_a_passing_run_can_promote_an_advisory_holding(tmp_path):
    L = led(tmp_path)
    repo = str(tmp_path)

    failing = L.open_run(repo, "add a field")
    L.close_run(failing, "fail")
    artifacts.save(tmp_path, failing, Change(repo=tmp_path, touched=["models/a.py"]))
    cid = L.file_case(failing, repo, "command_fail", "high", "the app went down", ["models/a.py"])
    hid = L.establish(cid, repo, "co_change",
                      {"trigger": "models/*.py", "required": "migrations/**"},
                      "changing models means changing migrations", status="persuasive")

    assert empanel.reconsider(L, repo) == [], "nothing has been proven yet"

    passing = L.open_run(repo, "unrelated work")
    L.close_run(passing, "pass")
    artifacts.save(tmp_path, passing, Change(repo=tmp_path, touched=["static/index.html"]))

    assert empanel.reconsider(L, repo) == [hid]
    assert L.holdings(repo=repo, status="binding")[0]["id"] == hid
