# VOIR DIRE — context for anyone (or any agent) picking this up

Read this before touching anything. It is the whole argument, the whole API,
and the list of ways this has already gone wrong.

---

## 1. What the project is

A civic ledger closes complaints. Nobody checks whether the work was done.
Voir dire sits in front of the "RESOLVED" button and **refuses a closure whose
evidence does not exist**, naming what to attach.

```
$ python -m voirdire gate seeds/ward-demo 11

  REFUSED   BINDING RULE No 1
  Closing a pothole needs a photo of the finished work.
  needs_evidence( pothole : photo_after )
  no photo_after on complaint 11; nothing attached
  DO THIS NEXT:  photograph the finished work at opp. 3rd Cross bus stop and attach it
```

The landmark is read off the citizen's own complaint. Nothing is templated prose.

## 2. The one idea that makes it different — EMPANELMENT

Every comparable tool stays **advisory**, because a tool that refuses the wrong
thing gets switched off, and everything it learned goes with it.

So here a rule **earns** the right to refuse. Before it can block anything it is
replayed against the ward's own record and must pass two tests:

1. **fires on the closure that produced it** — a rule that cannot catch its own
   case will not catch the next one;
2. **stays silent on every closure that held** — a rule that would have refused
   genuinely-finished work sends a crew back to a fixed road.

Fail either → demoted to **advisory** (still speaks, cannot stop anyone).
Pass both → **binding**. The receipt is printed publicly:

```
  BINDING   needs_evidence( pothole : photo_after )
            tested: 1/1 fired on its own case, 0/4 wrong on closures that held
```

**OVERRULING:** 3 overrides that succeed anyway retire a rule
(`overrule.COUNTER_THRESHOLD = 3`). Rules die in public too.

If you remember one thing: **binding vs advisory splits on certainty, not on
severity.**

## 3. Hard constraints — do not violate these

- **`history.py` must never be reachable from the gate.** It knows how a
  closure actually turned out. It exists for exactly two purposes: making a
  case out of a closure that came back, and testing a proposed rule against
  ones that held. If the gate could see it, the benchmark would measure
  nothing — the thing would be marking its own homework. Teammate code in
  `voir-dire/` has `store.is_invalid_closure()`; that is the **oracle's ground
  truth**. The gate calling it is the single worst thing you can do to this
  project.
- **No model in a decision path.** The gate is 100% deterministic. Templates
  are typed check shapes; a model may only fill blanks, never write code. You
  cannot ship a wall a language model can talk its way past.
- **Fail open.** A broken check abstains. It never refuses because it crashed.
- **Python 3.12, standard library only.** No Docker, no server, no API key, no
  embedding model. One SQLite file per ward.
- **Never force-push.** The remote already carried a teammate's work
  (`f671472 Add ward demo dashboard`) and our stage 1 sits on top of it.
- **Nobody edits `voirdire/` core** (`db`, `gate`, `panel`, `empanel`,
  `overrule`, `claim`, `templates`, `history`) except through an agreed change.
  Everything else composes on top.

## 4. The API surface — the whole thing

```python
gate.on(led, ward, claim) -> list[Verdict]        # [] means allowed
        # Verdict: .holding_id .says .rule .reason .template

panel.sit(led, str(ward.resolve()), claim) -> Sitting
        # .seats: holding_id, says, verdict, domain, next   (binding + advisory)

history.came_back(ward) -> list[Claim]            # NEVER call from the gate
history.held(ward)      -> list[Claim]
history.label(ward)     -> list[tuple[Claim, bool]]

learn.learn_ward(led, ward) -> list[dict]         # propose -> empanel -> file
templates.fires(name, params, claim) -> str | None
templates.valid(name, params) -> bool
templates.render(name, params) -> str
nextstep.suggest(template, params, claim) -> str | None

overrule.record_outcome(led, run_id, holding_id, complied: bool, passed: bool)
overrule.sweep(led, ward_str)

Claim.load_all(ward) / Claim.one(ward, id) / Claim.proposed(ward, id, evidence, closed_at)
        # .evidence(kind) .minutes_to_close() .metres_from_site(ev) .open_on_same_asset()

Ledger(db.ledger_path(ward))                      # <ward>/.voirdire/ledger.db
        open_run close_run file_case establish set_status cite
        holdings cases case citations counts wipe close
```

**The ledger is the only integration point.** Dashboard, benchmark, board and
CLI all read it. Nothing calls anything else's internals.

## 5. The four checks

| template | catches |
|---|---|
| `needs_evidence` | closed with nothing attached |
| `needs_time` | closed faster than this work has ever taken here |
| `evidence_on_site` | the after-photo was taken somewhere else |
| `not_while_open` | closed while the same asset has other complaints open |

Thresholds are **measured from the ward's own record** (`learn._typical_minutes`),
never chosen by hand. That is what makes a rule arguable with the same records.

## 6. Current state (12 Sep 2026)

- Stage 1 is in: ledger, claim, four checks, empanelment, gate, learning,
  instruction line. `python -m pytest -q` → **14 passed, 3 failed on purpose**.
- The 3 failures are `tests/test_ward_traps.py`, a **contract for the corpus**.
  `seeds/ward-demo` has the structure but not the traps — every closure carries
  a photo and took 48 hours, so there is nothing to catch. Each failing test
  names exactly what the data needs. Do not delete them to get green.
- `tests/ward.py` builds a correct fixture ward (4 held, 4 came back: bare,
  fast, away, dupe). Copy its shape when planting seed traps.
- Not done: stage 2 (dashboard refuses + split-screen demo), stage 3 (two-arm
  benchmark measuring repeat-complaint rate).

## 7. Failure modes that already happened — on the previous build

These are not hypotheticals. Every one cost hours.

1. **The system reported success while doing nothing.** An oracle that a
   pristine repo already passes scores a do-nothing agent at 100%. Any
   benchmark row needs an `attempted` flag derived from the artefact, and the
   report must refuse to be written if too many runs were vacuous.
2. **Recall returned an empty briefing** three separate times. Bag-of-words
   similarity scored the obviously-relevant rule at exactly zero. Fix was to
   stop filtering: name every binding rule.
3. **Seed contamination.** `base / path` silently discards the base when `path`
   is absolute, so an agent wrote into the pristine seeds. Contain every path.
4. **Subprocess with no timeout froze everything**, and on Windows
   `shell=True` grandchildren survive a kill and hold the stdout pipe. Kill the
   tree (`taskkill /PID n /T /F`).
5. **A rate limit scored 90 empty runs as passes.** Back off, and never let an
   unreachable provider look like a pass.

## 8. Naming

`voir-dire/` (hyphen) can never be a Python package — teammate dashboard code
lives there. Our package is `voirdire/`.

---

## 9. Where this came from — read it when you are stuck

**https://github.com/santoshcheethiralame-dot/PRECEDENT**

Voir dire is a port. Precedent is the same engine pointed at coding agents: a
failure a coding agent repeated becomes a deterministic check that refuses the
next commit that repeats it. `db.py`, `empanel.py`, `gate.py`, `panel.py`,
`overrule.py` and `recall.py` here are that code with `repo` renamed to `ward`
and `Change` rebound to `Claim`. Roughly 2,300 lines are shared; the templates,
the harness and the demo are the only parts that ever knew they were looking at
source code.

**Go and read it when:**

- you need the reasoning behind something in `voirdire/` core — it was argued
  out over there first, usually in a commit message;
- you are building the benchmark (Brief B). Precedent has a finished two-arm
  harness, an arm A/B/C structure, and a written record of four separate
  attempts that produced fake results before one produced a real one;
- you are building the pages (Brief B) — six of them exist there already;
- you want the honest numbers a result should look like. Precedent's, over 300
  runs: pass 53.3% → 70.0%, repeat-failure 58.1% → 31.0%, false positives 0.0%,
  and **9 regressions published alongside 34 wins**;
- you hit a bug that smells like one of the five in §7. All five have a fix
  committed there.

Also there: `docs/SCRIPT.md` — every feature explained in plain language, long
form. If you are writing anything a reviewer will read, start from its tone.

**What not to copy:** the templates (`packs.py`), the harness, and anything
about opencode. Those are the domain-specific half and none of it transfers.
