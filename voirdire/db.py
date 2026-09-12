"""The ledger. One SQLite file, four tables, no services."""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id        INTEGER PRIMARY KEY,
    ward      TEXT NOT NULL,
    task      TEXT NOT NULL,
    arm       TEXT NOT NULL DEFAULT 'live',
    model     TEXT,
    seed      INTEGER,
    result    TEXT,                      -- pass | fail | blocked
    started   REAL NOT NULL,
    ended     REAL
);

CREATE TABLE IF NOT EXISTS cases (
    id         INTEGER PRIMARY KEY,
    run_id     INTEGER NOT NULL REFERENCES runs(id),
    ward       TEXT NOT NULL,
    source     TEXT NOT NULL,            -- human_reject | command_fail | churn | revert | test_flip
    confidence TEXT NOT NULL,            -- high | low
    summary    TEXT NOT NULL,            -- the failure in one sentence
    touched    TEXT NOT NULL DEFAULT '[]',
    detail     TEXT NOT NULL DEFAULT '',
    filed      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS holdings (
    id        INTEGER PRIMARY KEY,
    case_id   INTEGER NOT NULL REFERENCES cases(id),
    template  TEXT NOT NULL,
    params    TEXT NOT NULL,             -- json
    scope     TEXT NOT NULL DEFAULT 'ward',   -- ward | global
    ward      TEXT NOT NULL,
    status    TEXT NOT NULL,             -- binding | persuasive | overruled | retired
    says      TEXT NOT NULL,             -- the one human sentence
    empanel   TEXT NOT NULL DEFAULT '{}',-- json receipt
    established REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS citations (
    id         INTEGER PRIMARY KEY,
    run_id     INTEGER NOT NULL REFERENCES runs(id),
    holding_id INTEGER NOT NULL REFERENCES holdings(id),
    outcome    TEXT NOT NULL,            -- complied_pass | complied_fail | overridden_pass | overridden_fail
    at         REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_holdings_status ON holdings(status);
CREATE INDEX IF NOT EXISTS ix_citations_holding ON citations(holding_id);
"""


def ledger_path(ward: Path, glob: bool = False) -> Path:
    if glob:
        return Path.home() / ".precedent" / "global.db"
    return Path(ward) / ".precedent" / "ledger.db"


class Ledger:
    """Thin wrapper. Rows come back as dicts because that is all anyone wants."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        self.con.commit()

    # -- writes -------------------------------------------------------------
    def open_run(self, ward: str, task: str, arm: str = "live", model: str = "", seed: int = 0) -> int:
        cur = self.con.execute(
            "INSERT INTO runs(ward, task, arm, model, seed, started) VALUES (?,?,?,?,?,?)",
            (ward, task, arm, model, seed, time.time()),
        )
        self.con.commit()
        return cur.lastrowid

    def close_run(self, run_id: int, result: str) -> None:
        self.con.execute("UPDATE runs SET result=?, ended=? WHERE id=?", (result, time.time(), run_id))
        self.con.commit()

    def file_case(self, run_id: int, ward: str, source: str, confidence: str,
                  summary: str, touched: list[str], detail: str = "") -> int:
        cur = self.con.execute(
            "INSERT INTO cases(run_id, ward, source, confidence, summary, touched, detail, filed)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (run_id, ward, source, confidence, summary, json.dumps(touched), detail, time.time()),
        )
        self.con.commit()
        return cur.lastrowid

    def establish(self, case_id: int, ward: str, template: str, params: dict, says: str,
                  status: str = "persuasive", scope: str = "ward", empanel: dict | None = None) -> int:
        cur = self.con.execute(
            "INSERT INTO holdings(case_id, template, params, scope, ward, status, says, empanel, established)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (case_id, template, json.dumps(params), scope, ward, status, says,
             json.dumps(empanel or {}), time.time()),
        )
        self.con.commit()
        return cur.lastrowid

    def set_status(self, holding_id: int, status: str, empanel: dict | None = None) -> None:
        if empanel is None:
            self.con.execute("UPDATE holdings SET status=? WHERE id=?", (status, holding_id))
        else:
            self.con.execute("UPDATE holdings SET status=?, empanel=? WHERE id=?",
                             (status, json.dumps(empanel), holding_id))
        self.con.commit()

    def update_holding(self, holding_id: int, template: str, params: dict,
                       says: str, status: str, empanel: dict) -> None:
        self.con.execute(
            "UPDATE holdings SET template=?, params=?, says=?, status=?, empanel=? WHERE id=?",
            (template, json.dumps(params), says, status, json.dumps(empanel), holding_id))
        self.con.commit()

    def cite(self, run_id: int, holding_id: int, outcome: str) -> None:
        self.con.execute("INSERT INTO citations(run_id, holding_id, outcome, at) VALUES (?,?,?,?)",
                         (run_id, holding_id, outcome, time.time()))
        self.con.commit()

    # -- reads --------------------------------------------------------------
    def holdings(self, ward: str | None = None, status: str | None = None) -> list[dict]:
        q = "SELECT * FROM holdings WHERE 1=1"
        args: list = []
        if status:
            q += " AND status=?"
            args.append(status)
        if ward:
            q += " AND (scope='global' OR ward=?)"
            args.append(ward)
        rows = [dict(r) for r in self.con.execute(q + " ORDER BY id", args)]
        for r in rows:
            r["params"] = json.loads(r["params"])
            r["empanel"] = json.loads(r["empanel"])
        return rows

    def cases(self, ward: str | None = None) -> list[dict]:
        q = "SELECT * FROM cases"
        args: list = []
        if ward:
            q += " WHERE ward=?"
            args.append(ward)
        rows = [dict(r) for r in self.con.execute(q + " ORDER BY id DESC", args)]
        for r in rows:
            r["touched"] = json.loads(r["touched"])
        return rows

    def case(self, case_id: int) -> dict | None:
        r = self.con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["touched"] = json.loads(d["touched"])
        return d

    def citations(self, holding_id: int) -> list[dict]:
        return [dict(r) for r in
                self.con.execute("SELECT * FROM citations WHERE holding_id=? ORDER BY id", (holding_id,))]

    def successful_runs(self, ward: str, limit: int = 40) -> list[dict]:
        return [dict(r) for r in self.con.execute(
            "SELECT * FROM runs WHERE ward=? AND result='pass' ORDER BY id DESC LIMIT ?", (ward, limit))]

    def counts(self, ward: str | None = None) -> dict:
        h = self.holdings(ward=ward)
        return {
            "cases": len(self.cases(ward=ward)),
            "binding": sum(1 for x in h if x["status"] == "binding"),
            "persuasive": sum(1 for x in h if x["status"] == "persuasive"),
            "overruled": sum(1 for x in h if x["status"] == "overruled"),
        }

    def wipe(self) -> None:
        """Start the story again without touching the file. Windows keeps locks."""
        for t in ("citations", "holdings", "cases", "runs"):
            self.con.execute(f"DELETE FROM {t}")
        self.con.commit()

    def close(self) -> None:
        self.con.close()
