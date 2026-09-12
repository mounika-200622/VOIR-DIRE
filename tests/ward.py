"""A tiny ward, built in a temp directory, with the traps actually planted.

The seeded wards under seeds/ are the benchmark corpus and belong to whoever is
building them. Tests need a ward whose contents they control exactly, so they
build their own: four closures that held, and four that came back for four
different reasons.
"""
from __future__ import annotations

import json
from pathlib import Path

STAMP = "%Y-%m-%dT%H:%M:%SZ"


def _c(i, asset, reported, assigned, kind="pothole", lat=12.9350, lon=77.6240,
       landmark="opp. 3rd Cross bus stop"):
    return {"id": i, "kind": kind, "asset_id": asset, "ward": 12,
            "location": {"lat": lat, "lon": lon, "landmark": landmark},
            "reported_at": reported, "assigned_at": assigned,
            "photos": [f"before_{i}.txt"], "severity": "high"}


def build(root: Path) -> Path:
    """Write a ward and return its path."""
    ward = Path(root) / "ward-test"
    (ward / "data").mkdir(parents=True, exist_ok=True)

    good_photo = {"type": "photo_after", "file": "after.txt",
                  "lat": 12.9351, "lon": 77.6241}

    complaints = [
        # --- four that were closed properly and stayed closed ------------
        _c(1, "A-OK1", "2026-07-01T09:00:00Z", "2026-07-01T10:00:00Z"),
        _c(2, "A-OK2", "2026-07-02T09:00:00Z", "2026-07-02T10:00:00Z"),
        _c(3, "A-OK3", "2026-07-03T09:00:00Z", "2026-07-03T10:00:00Z"),
        _c(4, "A-OK4", "2026-07-04T09:00:00Z", "2026-07-04T10:00:00Z"),

        # --- closed with nothing attached, and it came back --------------
        _c(10, "A-BARE", "2026-07-05T09:00:00Z", "2026-07-05T10:00:00Z"),
        _c(11, "A-BARE", "2026-07-26T09:00:00Z", "2026-07-26T10:00:00Z"),

        # --- closed four minutes after assignment, and it came back ------
        _c(20, "A-FAST", "2026-07-06T09:00:00Z", "2026-07-06T10:00:00Z"),
        _c(21, "A-FAST", "2026-07-27T09:00:00Z", "2026-07-27T10:00:00Z"),

        # --- photo taken 900m away, and it came back --------------------
        _c(30, "A-AWAY", "2026-07-07T09:00:00Z", "2026-07-07T10:00:00Z"),
        _c(31, "A-AWAY", "2026-07-28T09:00:00Z", "2026-07-28T10:00:00Z"),

        # --- one of four on the same asset closed, three left open ------
        _c(40, "A-DUPE", "2026-07-08T09:00:00Z", "2026-07-08T10:00:00Z"),
        _c(41, "A-DUPE", "2026-07-08T11:00:00Z", "2026-07-08T12:00:00Z"),
        _c(42, "A-DUPE", "2026-07-08T13:00:00Z", "2026-07-08T14:00:00Z"),
        _c(43, "A-DUPE", "2026-07-29T09:00:00Z", "2026-07-29T10:00:00Z"),
    ]

    closures = [
        {"complaint_id": 1, "closed_at": "2026-07-02T14:00:00Z", "closed_by": "crew-1",
         "evidence": [dict(good_photo), {"type": "work_order", "ref": "WO-1"}]},
        {"complaint_id": 2, "closed_at": "2026-07-03T14:00:00Z", "closed_by": "crew-1",
         "evidence": [dict(good_photo)]},
        {"complaint_id": 3, "closed_at": "2026-07-04T14:00:00Z", "closed_by": "crew-2",
         "evidence": [dict(good_photo)]},
        {"complaint_id": 4, "closed_at": "2026-07-05T14:00:00Z", "closed_by": "crew-2",
         "evidence": [dict(good_photo)]},

        # nothing attached
        {"complaint_id": 10, "closed_at": "2026-07-06T14:00:00Z", "closed_by": "crew-3",
         "evidence": [], "note": "attended"},
        # four minutes
        {"complaint_id": 20, "closed_at": "2026-07-06T10:04:00Z", "closed_by": "crew-3",
         "evidence": [dict(good_photo)]},
        # photo from the next neighbourhood
        {"complaint_id": 30, "closed_at": "2026-07-08T14:00:00Z", "closed_by": "crew-4",
         "evidence": [{"type": "photo_after", "file": "after_30.txt",
                       "lat": 12.9430, "lon": 77.6240}]},
        # closed while 41 and 42 are still open on the same asset
        {"complaint_id": 40, "closed_at": "2026-07-09T14:00:00Z", "closed_by": "crew-4",
         "evidence": [dict(good_photo)]},
    ]

    (ward / "data" / "complaints.json").write_text(
        json.dumps(complaints, indent=2), encoding="utf-8")
    (ward / "data" / "closures.json").write_text(
        json.dumps(closures, indent=2), encoding="utf-8")
    return ward
