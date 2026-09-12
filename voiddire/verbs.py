"""The commands a person actually types.

Everything here is deliberately small. A solo developer will not read a manual,
will not run a daemon, and will uninstall anything that blocks them once for a
bad reason. So: learn from what is already here, let them write a rule in one
sentence, tell them why they were stopped, and let them switch a rule off.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .change import Change
from .db import Ledger, ledger_path
from . import empanel, mine, templates

# ---------------------------------------------------------------- init --------


def install_pack(repo: Path, led: Ledger | None = None,
                 skip: tuple[str, ...] = ()) -> list[dict]:
    """The failures every agent makes, installed before the first one happens.

    Unambiguous patterns bind; the rest inform. A person should not have to leak
    a key once to learn that the tool could have caught it.
    """
    from . import packs

    repo = Path(repo).resolve()
    # A caller that already has a ledger open passes it in - the demo keeps
    # one ledger for a workspace it rebuilds on every reset, and opening the
    # repo's own would install the pack somewhere nothing reads.
    owned = led is None
    led = led or Ledger(ledger_path(repo))
    existing = {(h["template"], json.dumps(h["params"], sort_keys=True))
                for h in led.holdings(repo=str(repo))}

    out = []
    for r in packs.applicable(repo) + packs.manifest_pairs(repo):
        if r["template"] in skip:
            continue
        if "params" in r:
            params = r["params"]
        elif "regex" in r:
            params = {"regex": r["regex"], "glob": r["glob"]}
        else:
            params = {"trigger": r["trigger"], "required": r["required"]}
        key = (r["template"], json.dumps(params, sort_keys=True))
        if key in existing:
            continue
        run_id = led.open_run(str(repo), f"voiddire pack: {r['key']}", arm="pack")
        led.close_run(run_id, "pass")
        case_id = led.file_case(run_id, str(repo), "pack", "high", r["says"], [],
                                json.dumps({"pack": r["key"]}))
        hid = led.establish(case_id, str(repo), r["template"], params, r["says"],
                            status="binding" if r["binding"] else "persuasive",
                            empanel={"pack": r["key"]})
        out.append({**r, "id": hid, "params": params})
    if owned:
        led.close()
    return out


def init(repo: Path, limit: int = 600) -> list[dict]:
    """Everything this repository can tell us before anything has gone wrong.

    Proposals land ADVISORY. Mined history is evidence about habits, not proof
    that breaking one causes harm, and the difference matters: advisory rules
    inform the agent, binding rules stop it.
    """
    repo = Path(repo).resolve()
    led = Ledger(ledger_path(repo))
    existing = {(h["template"], json.dumps(h["params"], sort_keys=True))
                for h in led.holdings(repo=str(repo))}

    out = []
    for r in mine.propose(repo, limit):
        key = (r["template"], json.dumps(r["params"], sort_keys=True))
        if key in existing:
            continue
        run_id = led.open_run(str(repo), "voiddire init", arm="init")
        led.close_run(run_id, "pass")
        case_id = led.file_case(run_id, str(repo), "mined", "low", r["says"], [],
                                json.dumps(r["evidence"]))
        hid = led.establish(case_id, str(repo), r["template"], r["params"], r["says"],
                            status="persuasive", empanel={"mined": r["evidence"]})
        out.append({**r, "id": hid})
    led.close()
    return out


def confirm(repo: Path, ids: list[int]) -> list[dict]:
    """Promote a mined rule to binding, after it survives the usual replay."""
    repo = Path(repo).resolve()
    led = Ledger(ledger_path(repo))
    done = []
    for hid in ids:
        h = next((x for x in led.holdings() if x["id"] == hid), None)
        if not h or h["template"] not in templates.TEMPLATES:
            continue
        origin = Change(repo=repo, touched=[], commands=None)
        _, receipt = empanel.empanel(led, str(repo), h["template"], h["params"], origin)
        # A mined rule has no failing case of its own to fire on, so the
        # fire-on-origin half of empanelment does not apply. What still applies,
        # and is the half that matters, is that it must not fire on past work.
        ok = not receipt.get("false_ids")
        led.set_status(hid, "binding" if ok else "persuasive",
                       {**receipt, "mined": True, "fire": "n/a (no failing case)"})
        done.append({"id": hid, "status": "binding" if ok else "persuasive",
                     "receipt": receipt})
    led.close()
    return done


# ---------------------------------------------------------------- rule --------

FORMS = (
    (re.compile(r"^(?P<a>[^\s]+)\s+needs\s+(?P<b>[^\s]+)$", re.I),
     lambda m: ("co_change", {"trigger": m["a"], "required": _glob(m["b"])},
                f"Changing {m['a']} means changing {m['b']} too.")),
    (re.compile(r"^never\s+(?:touch|edit)\s+(?P<g>[^\s]+)$", re.I),
     lambda m: ("forbidden_edit", {"glob": m["g"]}, f"Never edit {m['g']}.")),
    (re.compile(r"^after\s+(?P<g>[^\s]+)\s+run\s+(?P<cmd>.+)$", re.I),
     lambda m: ("required_command", {"glob": m["g"], "cmd": m["cmd"].strip()},
                f"After changing {m['g']}, `{m['cmd'].strip()}` has to pass.")),
)

HELP = "\n".join([
    '  voiddire rule "models/*.py needs migrations/"',
    '  voiddire rule "never touch package-lock.json"',
    '  voiddire rule "after src/*.py run pytest -q"',
])


def _glob(token: str) -> str:
    return f"{token.rstrip('/')}/**" if token.endswith("/") else token


def parse(sentence: str):
    for pattern, build in FORMS:
        m = pattern.match(sentence.strip())
        if m:
            return build(m)
    return None


def rule(repo: Path, sentence: str) -> dict | None:
    """A rule you wrote yourself.

    You know your own repository, so this needs no failure first. It is still
    replayed against past work - a rule that would have blocked something that
    already succeeded is worth catching before it bites, whoever wrote it.
    """
    parsed = parse(sentence)
    if not parsed:
        return None
    template, params, says = parsed
    repo = Path(repo).resolve()
    led = Ledger(ledger_path(repo))

    run_id = led.open_run(str(repo), f"taught: {sentence}", arm="taught")
    led.close_run(run_id, "fail")
    case_id = led.file_case(run_id, str(repo), "taught", "high", sentence, [],
                            json.dumps({"sentence": sentence}))
    origin = Change(repo=repo, touched=[], commands=None)
    _, receipt = empanel.empanel(led, str(repo), template, params, origin)
    ok = not receipt.get("false_ids")
    status_ = "binding" if ok else "persuasive"
    hid = led.establish(case_id, str(repo), template, params, says, status=status_,
                        empanel={**receipt, "taught": True, "fire": "n/a (you wrote it)"})
    led.close()
    return {"id": hid, "template": template, "params": params, "says": says,
            "status": status_, "receipt": receipt}


# ----------------------------------------------------------------- why --------


def why(repo: Path, path: str) -> list[dict]:
    """Which rules apply to this file, and where each came from."""
    repo = Path(repo).resolve()
    led = Ledger(ledger_path(repo))
    rel = path.replace("\\", "/")
    try:
        rel = Path(path).resolve().relative_to(repo).as_posix()
    except (ValueError, OSError):
        pass

    out = []
    for h in led.holdings(repo=str(repo)):
        p = h["params"]
        globs = [g for g in (p.get("trigger"), p.get("glob"), p.get("required")) if g]
        if any(templates._hits([rel], g) for g in globs):
            case = led.case(h["case_id"]) or {}
            out.append({**h, "source": case.get("source", "?"),
                        "reason": case.get("summary", "")})
    led.close()
    return out


# ------------------------------------------------------------- off / on -------


def mute(repo: Path, hid: int, on: bool = False) -> dict | None:
    """Switch a rule off without deleting the case that produced it.

    The escape hatch matters more than it looks: a tool that blocks you once for
    a bad reason and gives you no way out gets uninstalled, and every rule it
    ever learned goes with it.
    """
    repo = Path(repo).resolve()
    led = Ledger(ledger_path(repo))
    h = next((x for x in led.holdings() if x["id"] == hid), None)
    if not h:
        led.close()
        return None
    if on:
        back = h["empanel"].get("muted_from", "persuasive")
        led.set_status(hid, back,
                       {k: v for k, v in h["empanel"].items() if k != "muted_from"})
        result = {"id": hid, "status": back}
    else:
        led.set_status(hid, "muted", {**h["empanel"], "muted_from": h["status"]})
        result = {"id": hid, "status": "muted", "was": h["status"]}
    led.close()
    return result


# ---------------------------------------------------------------- status ------


def status(repo: Path, days: int = 7) -> dict:
    repo = Path(repo).resolve()
    led = Ledger(ledger_path(repo))
    since = time.time() - days * 86400
    holdings = led.holdings(repo=str(repo))
    stopped, overridden = 0, 0
    for h in holdings:
        for c in led.citations(h["id"]):
            if c["at"] < since:
                continue
            if c["outcome"] == "blocked" or c["outcome"].startswith("complied"):
                stopped += 1
            elif c["outcome"].startswith("overridden"):
                overridden += 1
    counts = led.counts(str(repo))
    led.close()
    return {"days": days, "stopped": stopped, "overridden": overridden,
            "binding": counts["binding"], "advisory": counts["persuasive"],
            "muted": sum(1 for h in holdings if h["status"] == "muted"),
            "overruled": counts["overruled"], "cases": counts["cases"]}


# ----------------------------------------------------------------- hook -------

# `python -m voiddire` only resolves from a checkout of this repository. The
# hook runs in the user's repository, so it calls the installed console script
# and keeps the module form as a fallback for a checkout that was never
# installed.
HOOK = (
    "#!/bin/sh\n"
    "# installed by `voiddire hook`\n"
    "if command -v voiddire >/dev/null 2>&1; then\n"
    "  exec voiddire gate .\n"
    "fi\n"
    "exec python -m voiddire gate .\n"
)


def hook(repo: Path) -> Path | None:
    hooks = Path(repo).resolve() / ".git" / "hooks"
    if not hooks.is_dir():
        return None
    target = hooks / "pre-commit"
    target.write_text(HOOK, encoding="utf-8")
    try:
        target.chmod(0o755)
    except OSError:
        pass
    return target


# -------------------------------------------------------------- opencode ------

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin" / "voiddire.ts"


def opencode(repo: Path, mode: str = "enforce") -> dict:
    """Install the plugin into a repository so opencode actually stops a write.

    `watch` sees everything and stops nothing - it reads git after the fact.
    This is the other half: the plugin throws in tool.execute.before, which
    aborts the tool call before the bytes land, and the halt card goes back to
    the model as the error. Every decision comes from `voiddire serve`; the
    plugin is plumbing with a timeout and it fails open.
    """
    import json as _json
    import shutil as _shutil

    repo = Path(repo).resolve()
    if not PLUGIN.is_file():
        raise FileNotFoundError(f"the plugin is missing from this checkout: {PLUGIN}")

    plugins = repo / ".opencode" / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    dest = plugins / "voiddire.ts"
    _shutil.copy2(PLUGIN, dest)

    # Merge rather than overwrite: a repository that already configures its own
    # agent should not lose that configuration to a plugin install.
    cfg_path = repo / "opencode.json"
    cfg: dict = {}
    if cfg_path.is_file():
        try:
            cfg = _json.loads(cfg_path.read_text(encoding="utf-8"))
        except ValueError:
            cfg = {}
    cfg.setdefault("$schema", "https://opencode.ai/config.json")
    perm = cfg.setdefault("permission", {})
    # `edit: allow` on its own permits editing any absolute path, and with bash
    # the agent can walk out of the repository entirely. It has done exactly
    # that here once, writing into the seed corpus while the recorder watched
    # an untouched workspace.
    perm.setdefault("external_directory", "deny")
    cfg_path.write_text(_json.dumps(cfg, indent=2) + chr(10), encoding="utf-8")

    return {"plugin": dest, "config": cfg_path, "mode": mode}


# ---------------------------------------------------------- claude code -------

# Shipped as a constant rather than a file so there is nothing to package and
# nothing to go missing. It swallows its own import error: a repository whose
# hooks outlive the install should be silent, not broken.
CLAUDE_HOOK = (
    "import sys\n"
    "# installed by `voiddire claude`\n"
    "try:\n"
    "    from voiddire import claude_hook\n"
    "except Exception:\n"
    "    sys.exit(0)\n"
    "sys.exit(claude_hook.main(sys.argv[1:]))\n"
)

MARK = "voiddire_gate.py"          # identity for an idempotent merge
MATCHER = {"PreToolUse": "Write|Edit|MultiEdit|NotebookEdit",
           "UserPromptSubmit": ""}


def _merge_hook(cfg: dict, event: str, command: str) -> None:
    """Register one hook without trampling anything already there.

    Purge-then-append keyed on MARK, so re-running with a different --mode
    replaces our entry rather than stacking a second one, and a repository that
    already runs its own formatter on PostToolUse keeps it.
    """
    groups = cfg.setdefault("hooks", {}).setdefault(event, [])
    for g in groups:
        g["hooks"] = [h for h in g.get("hooks", [])
                      if MARK not in str(h.get("command", ""))]
    groups[:] = [g for g in groups if g.get("hooks")]

    want = MATCHER[event]
    g = next((g for g in groups if g.get("matcher", "") == want), None)
    if g is None:
        g = {"matcher": want, "hooks": []}
        groups.append(g)
    g["hooks"].append({"type": "command", "command": command, "timeout": 5})


def claude(repo: Path, mode: str = "enforce") -> dict:
    """Install the hook so Claude Code actually stops a write.

    Same enforcement as the opencode plugin, in the harness most people are
    using. PreToolUse denies the write before the bytes land and hands back the
    card; UserPromptSubmit puts the rules in front of the model before it starts,
    which is the half that costs a sentence instead of a whole turn.
    """
    import json as _json
    import sys as _sys

    repo = Path(repo).resolve()
    hooks_dir = repo / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    shim = hooks_dir / MARK
    shim.write_text(CLAUDE_HOOK, encoding="utf-8")

    cfg_path = repo / ".claude" / "settings.json"
    cfg: dict = {}
    if cfg_path.is_file():
        try:
            cfg = _json.loads(cfg_path.read_text(encoding="utf-8"))
        except ValueError:
            cfg = {}

    for event in MATCHER:
        cmd = (f'"{_sys.executable}" '
               f'"${{CLAUDE_PROJECT_DIR}}/.claude/hooks/{MARK}" '
               f'--event {event} --mode {mode}')
        _merge_hook(cfg, event, cmd)

    cfg_path.write_text(_json.dumps(cfg, indent=2) + chr(10), encoding="utf-8")
    return {"hook": shim, "config": cfg_path, "mode": mode}
