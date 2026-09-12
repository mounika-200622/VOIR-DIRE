# VOID DIRE — context for anyone (or any agent) picking this up

Read this before touching anything.

## 1. What this repository is

Read [README.md](README.md) first; it is the whole pitch. This file is the
operating manual underneath it.

The one-line version: a coding agent forgets a lesson the moment the
conversation ends. Void Dire turns a confirmed failure — a rejected diff, a
failing check, a test that flipped from green to red — into a **binding
check**: deterministic, executable, cited to the run that established it. Not
a paragraph pasted into the system prompt, which a model is free to skim past
under pressure, but a rule that fires on the working tree and stops the write
before it lands.

## 2. The one idea that makes it different — EMPANELMENT

A tool that refuses things gets switched off the first time it refuses the
wrong thing, and everything it ever learned goes with it. So here a rule
**earns** the right to block. Before it can refuse anything it is replayed
against the repository's own history and must pass two tests:

1. **it fires on the case that produced it** — a rule that cannot catch its
   own failure will not catch the next one;
2. **it stays silent across every past successful run** — a rule that would
   have blocked work that already shipped is a rule that wastes the next
   agent's turn for nothing.

Fail either → demoted to **persuasive** (prose in the prompt, cannot block).
Pass both → **binding**, and the receipt is printed publicly:

```
BINDING   co_change( models/*.py -> migrations/** )
          tested: 1/1 fired on its own case, 0/5 false on past successes
```

**OVERRULING:** three overrides that succeed anyway retire a binding holding
(`overrule.COUNTER_THRESHOLD = 3`), published on the overruled page with the
citations that killed it. If you remember one thing: **binding vs persuasive
splits on certainty, not on severity.**

## 3. Hard constraints — do not violate these

- **No model in a decision path.** `gate.evaluate` is 100% deterministic.
  A model, when reachable, only fills the blanks of a typed template when
  *compiling* a case — it never writes a checker and it is never consulted
  when deciding whether to block a write. Take the model away and the
  deterministic fallback in `mine.py` / `compiler.py` takes over.
- **Fail open.** A broken check abstains (`templates.fires` swallows its own
  exceptions). It never refuses because it crashed, and the opencode plugin
  never stalls the agent because the service is slow or down.
- **`self_disarm` stays binding.** The agent is not allowed to edit
  `.voiddire/`, `.git/hooks/`, `.opencode/plugins/`, or its own permissions
  config. This has actually happened here twice — once an
  agent wrote outside its own worktree into the seed corpus, once a plugin
  file went missing and every benchmark arm silently became a bare agent
  still printing numbers that looked like results.
- **Path containment.** `workspace.restore` refuses to write onto or inside a
  seed. `change.py`'s `IGNORED` tuple keeps the ledger's own directory out of
  every diff it reads. `base / path` silently discards `base` when `path` is
  absolute — that bug contaminated the corpus twice;
  every path that touches a seed goes through containment now.
- **Subprocess deadlines, always.** `shell.py` bounds every subprocess with a
  timeout and kills the process tree (`taskkill /PID n /T /F` on Windows,
  where a `shell=True` grandchild survives a plain kill and holds the stdout
  pipe open forever).
- **The `attempted` flag is derived from the artefact, never from the
  oracle.** An oracle that a do-nothing run already passes scores a
  do-nothing agent at 100%. `bench/run.py` refuses to write a report if more
  than 10% of runs never really ran.
- **Python 3.12, standard library only.** No Docker, no server, no API key,
  no embedding model for anything on the gate's decision path. One SQLite
  file per repository, four tables: `runs`, `cases`, `holdings`, `citations`.
- **Never force-push.**
- **Nobody edits the core** (`db`, `gate`, `panel`, `empanel`, `overrule`,
  `recall`, `change`, `templates`, `compiler`) except through an agreed
  change — the benchmark and the UI both assume that surface is frozen.

## 4. The API surface

```python
gate.evaluate(led, repo, change, borrowed=[]) -> list[Verdict]   # [] means clear
gate.check(repo, led=None) -> (list[Verdict], Change)

panel.sit(led, repo, change) -> Sitting          # every rule, fired or not
        # .seats: holding_id, template, domain, says, status, verdict, reason, next, took_ms

Change.from_git(repo) -> Change                  # uncommitted work, staged+unstaged+untracked
Change.since(repo, before, commands=None) -> Change
Change.from_edits(repo, edits) -> Change
        # .touched .added .removed .commands .text(path) .run(cmd)

empanel.empanel(led, repo, template, params, origin) -> (status, receipt)
overrule.record_outcome(led, run_id, holding_id, complied, passed)
overrule.sweep(led, repo=None) -> list[int]      # ids demoted this sweep

record.file_case(led, run_id, repo, case, change, use_model=True, share=True) -> dict
mine.propose(repo) -> list[dict]                 # git-history mining, behind `voiddire init`
recall.briefing(led, repo, task) -> str          # every binding rule named, advisory ranked

Ledger(db.ledger_path(repo))                     # <repo>/.voiddire/ledger.db
        open_run close_run file_case establish set_status cite
        holdings cases case citations counts wipe close
```

**The ledger is the only integration point.** The CLI, the opencode plugin,
the board, and the benchmark all read it. Nothing calls anything else's
internals directly.

## 5. What it checks

Twelve templates across seven domains — see [README.md](README.md#what-it-checks)
for the full table. The two structural facts worth repeating here:

- Thresholds and pairings are **measured from the repository's own history**,
  never chosen by hand (`mine.py`, `compiler.py`).
- Only `structure` and `security` templates ship binding by default in the
  pack (`packs.py`); `hygiene` and `tests` ship advisory on purpose, because a
  tool that blocks a legitimate refactor gets uninstalled within the hour.

## 6. Current state

`python -m pytest -q` → **247 collected**, green aside from
environment-dependent skips (no reachable model, no `sleeper` sibling
installed, no opencode runtime for the live-harness tests — all skip cleanly
rather than failing). The benchmark, the opencode plugin, the office UI
(desk/cabinet/card/chart/tape/withdrawn drawer), and `init`'s git-history
miner are all in and tested. The 300-run evidence behind every number in the
README is committed under `bench/` — `report.json`, `compliance.json` and the
rest — so any claim on the page can be checked against the file that produced
it without running anything.

**Not proven, stated here rather than found by someone else:** the benchmark
agent is synthetic; arm B (prose-only) has not been run against a real model;
nine tasks regressed; `blast_radius` and `no_quadratic` have no trap class in
the benchmark. See `README.md`'s "What is not proven" section — do not quietly
drop it because a demo is soon.

## 7. Failure modes that already happened

Every one of these cost hours to find and is now guarded by a
test or an assertion, not just a memory:

1. **The system reported success while doing nothing.** A do-nothing agent
   scored 100% because the oracle only asked whether the repo was
   *consistent*, and an untouched repo is consistent. Fixed by deriving
   `attempted` from the artefact.
2. **Recall returned an empty briefing**, three separate times. Bag-of-words
   similarity scored the obviously-relevant rule at exactly zero against the
   task text. Fix: stop filtering binding rules by similarity — name every one.
3. **Seed contamination**, twice. `base / path` silently discards `base` when
   `path` is absolute, so an agent wrote into the pristine seed corpus.
4. **A subprocess with no timeout froze the run** — the seeded web server
   never exits on its own. On Windows, `shell=True` grandchildren survive a
   plain kill and hold the stdout pipe open.
5. **A rate limit scored 90 empty runs as passes.** The benchmark now refuses
   to publish a report when more than 10% of runs never reached the model.
6. **A bytecode-cache bug scored a failing run as a pass.** A `.pyc` records
   source mtime to one-second granularity; writing a module and importing it
   inside the same wall-clock second let Python serve the stale version.
   Every benchmark subprocess now sets `PYTHONDONTWRITEBYTECODE`.

## 8. The other documents

- `docs/SCRIPT.md` — every feature in plain language, long form. If you are
  writing anything a reviewer will read, start from its tone.
- `docs/DESIGN.md` — the design law for the records-office UI: the palette,
  the stepped-motion rule, and why the clerk has a screen instead of a face.
- `docs/PAGES.md` — the build spec for each page: its furniture, its exact
  data binding, and what "done" means for it.
- `docs/DEMO.md` — the run sheet for presenting this. Ports and expected
  output are literal; if a line does not appear, stop rather than talk over it.

**The name is the argument.** Voir dire is the examination a juror sits
through before being allowed to judge anything — that is empanelment. Void is
the other half: an untested holding never binds, and a binding one that keeps
being wrong is voided in public, on its own page, with the citations that
overturned it.
