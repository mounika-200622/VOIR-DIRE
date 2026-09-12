"""The seeded wards have to actually contain the mistakes they are named after.

A ward whose assets are called ASSET-TRAP1..4 but whose closures all carry a
photo and all took two days is a ward where nothing is wrong. The gate finds
nothing, the dashboard shows nothing, and the benchmark measures nothing - and
every one of those looks like the gate failing rather than the data being
empty.

So the corpus gets a contract, checked the same way the code is. This is a
statement of what seeds/ward-demo needs to contain, not a complaint that it
does not yet.
"""
import json
import pathlib
import sys
from datetime import datetime

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WARD = ROOT / "seeds" / "ward-demo"
STAMP = "%Y-%m-%dT%H:%M:%SZ"

pytestmark = pytest.mark.skipif(
    not (WARD / "data" / "complaints.json").is_file(),
    reason="seeds/ward-demo has no data yet")


def load():
    d = WARD / "data"
    return (json.loads((d / "complaints.json").read_text(encoding="utf-8")),
            json.loads((d / "closures.json").read_text(encoding="utf-8")))


def when(s):
    return datetime.strptime(s, STAMP)


def test_some_closure_has_no_evidence():
    _, closures = load()
    bare = [c["complaint_id"] for c in closures if not c.get("evidence")]
    assert bare, ("no closure in ward-demo is missing its evidence, so the "
                  "commonest failure in the whole dataset cannot be "
                  "demonstrated. At least one closure needs \"evidence\": []")


def test_some_closure_is_too_fast():
    complaints, closures = load()
    by_id = {c["id"]: c for c in complaints}
    fast = []
    for c in closures:
        m = by_id.get(c["complaint_id"])
        if not m or not m.get("assigned_at"):
            continue
        mins = (when(c["closed_at"]) - when(m["assigned_at"])).total_seconds() / 60
        if mins < 10:
            fast.append((c["complaint_id"], round(mins)))
    assert fast, ("no closure was filed suspiciously fast. One should be closed "
                  "within a few minutes of assignment - a pothole is not "
                  "repaired in four minutes")


def test_some_evidence_is_from_somewhere_else():
    complaints, closures = load()
    by_id = {c["id"]: c for c in complaints}
    far = []
    for c in closures:
        m = by_id.get(c["complaint_id"])
        if not m:
            continue
        loc = m.get("location") or {}
        for ev in c.get("evidence", []):
            if ev.get("type") != "photo_after" or ev.get("lat") is None:
                continue
            dlat = (ev["lat"] - loc.get("lat", 0)) * 111_320
            dlon = (ev["lon"] - loc.get("lon", 0)) * 111_320 * 0.68
            if (dlat ** 2 + dlon ** 2) ** 0.5 > 300:
                far.append(c["complaint_id"])
    assert far, ("every after-photo is at the reported location, so the check "
                 "that matters most - is this evidence or is it paperwork - "
                 "has nothing to catch. One photo should be a few hundred "
                 "metres away")


def test_some_asset_is_closed_while_others_stay_open():
    complaints, closures = load()
    closed = {c["complaint_id"] for c in closures}
    by_asset: dict[str, list] = {}
    for c in complaints:
        by_asset.setdefault(c.get("asset_id", ""), []).append(c)
    orphaned = [a for a, group in by_asset.items()
                if len(group) > 1
                and any(c["id"] in closed for c in group)
                and any(c["id"] not in closed for c in group)]
    assert orphaned, ("no asset has one complaint closed while others stay "
                      "open, so the duplicate check has nothing to catch")


def test_there_are_control_closures_that_are_entirely_fine():
    """Without these there is no way to measure a false alarm."""
    complaints, closures = load()
    by_id = {c["id"]: c for c in complaints}
    clean = 0
    for c in closures:
        m = by_id.get(c["complaint_id"])
        if not m or not c.get("evidence"):
            continue
        if any(e.get("type") == "photo_after" for e in c["evidence"]):
            clean += 1
    assert clean >= 6, f"only {clean} obviously-good closures; need at least 6"
