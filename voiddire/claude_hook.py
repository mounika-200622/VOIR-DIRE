"""VOID DIRE as a Claude Code hook - the other harness that can actually refuse.

`watch` reads git and reports; it cannot stop anything. The opencode plugin
stops a write by throwing in tool.execute.before. This is the same enforcement
for Claude Code, which reaches far more people: a PreToolUse hook that inspects
the write *before* it lands and denies it, handing the halt card back to the
model as the reason.

Two events, both registered by `voiddire claude`:

  PreToolUse         a write is about to happen -> allow, or deny with the card
  UserPromptSubmit   the turn is starting -> put the rules in front of the model

The second one matters more than it looks. Being blocked costs a whole turn and
the model has to work out why; being told costs a sentence and it complies the
first time. Our own numbers say the gate is not the mechanism - the instruction
is.

Nothing here decides anything. Every verdict comes from the same
`serve.gate_check` the plugin and the watcher call, so a rule cannot mean one
thing in one harness and something else in another.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

# Tools that put bytes on disk. Anything else is not a change we can judge, and
# gating a read is how a memory layer gets uninstalled in an afternoon.
WRITERS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

URL = os.environ.get("VOIDDIRE_URL", "http://127.0.0.1:4000")
MODE_ENV = "VOIDDIRE_MODE"


def pending_paths(tool_name: str, tool_input: dict) -> list[str]:
    """Which files this call is about to write.

    Claude Code names them in snake_case and differs per tool: `file_path` for
    Write/Edit/MultiEdit, `notebook_path` for NotebookEdit, and MultiEdit can
    carry a list of edits. Getting this wrong makes the gate silently useless -
    it would return "nothing pending" and allow every write.
    """
    if tool_name not in WRITERS:
        return []
    out: list[str] = []
    for key in ("file_path", "notebook_path"):
        v = (tool_input or {}).get(key)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    edits = (tool_input or {}).get("edits")
    if isinstance(edits, list):
        for e in edits:
            v = e.get("file_path") if isinstance(e, dict) else None
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
    return list(dict.fromkeys(out))


def _post(path: str, body: dict, timeout: float) -> dict | None:
    req = urllib.request.Request(
        f"{URL}{path}", data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def gate(repo: str, pending: list[str], timeout: float = 0.9) -> dict:
    """Ask the service if it is up, otherwise answer in-process.

    The service is preferred only so the desk page lights up while someone is
    watching it - the decision is identical either way. `serve.gate_check` is a
    pure function of (repo, pending) and needs no server, so there is no daemon
    to start and nothing to keep running.
    """
    try:
        got = _post("/v1/gate", {"repo": repo, "pending": pending}, timeout)
        if isinstance(got, dict) and "block" in got:
            return got
    except Exception:
        pass
    from . import serve
    return serve.gate_check(repo, pending)


def advise(repo: str, task: str, everything: bool, timeout: float = 0.9) -> str:
    try:
        got = _post("/v1/advise", {"repo": repo, "task": task,
                                   "everything": everything}, timeout)
        if isinstance(got, dict) and isinstance(got.get("text"), str):
            return got["text"]
    except Exception:
        pass
    from . import serve
    return serve.advise(repo, task, everything).get("text", "")


def _repo(payload: dict) -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()


def _deny(reason: str) -> tuple[int, str, str]:
    """Deny in both the shapes Claude Code accepts.

    The structured form on stdout is what current versions read; exit 2 with the
    reason on stderr is the older contract and still honoured. Emitting both
    costs nothing and means the gate does not quietly stop working when someone
    is on a different version.
    """
    out = json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}})
    return 2, out, reason


def pretooluse(payload: dict, mode: str) -> tuple[int, str, str]:
    if mode == "off":
        return 0, "", ""
    pending = pending_paths(payload.get("tool_name", ""), payload.get("tool_input") or {})
    if not pending:
        return 0, "", ""
    repo = _repo(payload)
    if not (Path(repo) / ".voiddire" / "ledger.db").is_file():
        return 0, "", ""            # nothing has been learned here yet
    got = gate(repo, pending)
    if not got.get("block") or not got.get("verdicts"):
        return 0, "", ""
    if mode == "advise":
        # Arm B: the model is told everything and stopped by nothing. This is
        # what every other memory layer in this space does.
        return 0, "", ""
    from . import render
    return _deny(render.agent_card(got["verdicts"]))


def userpromptsubmit(payload: dict, mode: str) -> tuple[int, str, str]:
    if mode == "off":
        return 0, "", ""
    repo = _repo(payload)
    if not (Path(repo) / ".voiddire" / "ledger.db").is_file():
        return 0, "", ""
    # In advise mode the binding rules are spoken rather than enforced, so the
    # two arms differ only in whether the model may ignore what it is told.
    text = advise(repo, payload.get("prompt", "") or "", everything=(mode == "advise"))
    if not text.strip():
        return 0, "", ""
    return 0, json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": text}}), ""


EVENTS = {"PreToolUse": pretooluse, "UserPromptSubmit": userpromptsubmit}


def main(argv: list[str] | None = None) -> int:
    """Fail open, structurally.

    Every path out of here returns 0 unless a binding holding actually fired.
    A memory layer that can wedge someone's agent by being broken is worse than
    no memory layer, so a crash, a malformed payload, a missing ledger and an
    unreachable service all mean "allow".
    """
    try:
        p = argparse.ArgumentParser(prog="voiddire-hook")
        p.add_argument("--event", default="PreToolUse", choices=sorted(EVENTS))
        p.add_argument("--mode", default="enforce")
        a = p.parse_args(argv)
        mode = (os.environ.get(MODE_ENV) or a.mode or "enforce").lower()

        payload = json.loads(sys.stdin.read() or "{}")
        code, out, err = EVENTS[a.event](payload, mode)
        if out:
            sys.stdout.write(out)
        if err:
            sys.stderr.write(err)
        return code
    except BaseException:
        return 0


if __name__ == "__main__":
    sys.exit(main())
