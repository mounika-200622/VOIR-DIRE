# Brief B — the proof

**You own the number.** If the number is wrong, or dishonest, or measures
nothing, the project is a demo with good typography. Everything Person A builds
rests on your table.

Read [`CLAUDE.md`](../CLAUDE.md) end to end before you write a line. This file
assumes you have.

**Your files, and only these:**

```
voirdire/bench/          (new, yours - runner, report, arms)
web/*.html               (five pages)
voirdire/board.py        (new, yours)
pyproject.toml           (packaging)
```

**Do not touch:** `voirdire/db.py`, `gate.py`, `panel.py`, `empanel.py`,
`overrule.py`, `claim.py`, `templates.py`, `history.py`, `learn.py`,
`nextstep.py`, and **anything under `seeds/`**. The seeds are Person A's.
If you need a trap that does not exist, ask for it — do not add it yourself, or
the benchmark is measuring a corpus you tuned to it.

---

# B1 — the two-arm benchmark

## The claim you are testing

> Closures that go through the gate come back less often than closures that do
> not.

That is it. One sentence, one number.

## The design

| arm | what happens |
|---|---|
| **A — control** | replay the ward's closures as they were actually filed. Gate off. |
| **B — gated** | replay the same closures through `gate.on`. A refused closure is not filed; it is re-filed with the evidence the gate demanded, then re-judged. |

Same ward, same closures, same order, same seed. The only difference is the
gate.

**The headline number: repeat-complaint rate per arm** — of the closures filed,
how many had the same `asset_id` reported again afterwards.

**Secondary, all required in the report:**

- refusals (how many closures the gate stopped)
- **false refusals** — refusals on closures that in fact held. This is the
  number a sceptic asks for. Report it first among the secondaries.
- overrides, and how many of those succeeded anyway
- advisory-only mentions (fired but did not block)
- rules that were binding vs advisory at the end of each run
- wall-clock per evaluation

## Where ground truth comes from — and only from there

```python
from voirdire import history
history.held(ward)       # closures that stayed closed
history.came_back(ward)  # closures that did not
history.label(ward)      # [(claim, held_bool), ...]
```

**The gate never sees this. Not once. Not indirectly.** Your runner may import
`history`; the code path that decides a refusal may not. Keep them in separate
functions and comment the boundary. If the gate can see the answer, the
benchmark measures nothing and every number in it is a lie you will have to
retract in front of a judge.

### There are two definitions of "came back" in this repo. Pick one and say so.

- `voirdire/history.py` — a closure came back if **the same asset was reported
  again after it was closed**. Full stop.
- `seeds/ward-demo/store.py:get_complaints()` — marks `REOPENED` only if the
  closure was **invalid AND** reported again.

These disagree, and the second one bakes the answer into the label. **Use
`history.py`.** Write one paragraph in the report saying which definition you
used and why, because the dashboard uses the other one and someone will notice.

## Five rules that are not negotiable

Each of these is a specific way the previous build produced a confident,
completely meaningless number.

**1. Every row carries an `attempted` flag, derived from the artefact.**

An oracle that a do-nothing run already passes reports 100%. The previous build
scored a model that read three files and stopped at **100% pass in all three
arms**. Do not derive "attempted" from the oracle. Derive it from the thing
that should have changed — did the closure actually get filed, did the evidence
actually get attached.

**2. The report refuses to be written if too many runs were vacuous.**

Hard gate, over 10% and it raises rather than writes. A rate limit once scored
**90 empty runs as passes** and the report was published before anyone noticed.

```python
if vacuous / total > 0.10:
    raise SystemExit(f"refusing to write a report: {vacuous}/{total} runs never really ran")
```

**3. Publish the regressions.**

Cases where the gate made things worse go in the table next to the wins. The
previous build shipped **9 regressions alongside 34 wins** and it made the
result more credible, not less. A table with no losses reads as a pitch.

**4. Deterministic and seeded.**

No wall clock in a decision, no `set` iteration order in output, no
`datetime.utcnow()` anywhere that reaches a number. Run it twice; diff the two
reports; they must be byte-identical. Make that a test.

**5. No model anywhere.**

The gate is deterministic, so the benchmark needs no provider, no key, no
network. If you find yourself adding a `--model` flag, stop and re-read
CLAUDE.md §3.

## Practical shape

```bash
python -m voirdire bench seeds/ward-demo                  # one ward, both arms
python -m voirdire bench seeds/ --all --seed 7 --out web/report.json
```

Use a **fresh ledger per arm** — `Ledger(tmp / "arm-a.db")` — never the ward's
own. Two arms sharing a ledger means arm B's rules leak into arm A and the
comparison is void. `led.wipe()` exists for reuse without deleting the file
(Windows holds locks on open SQLite files; deleting mid-run fails).

Write `web/report.json` for the pages, and print a plain table to stdout for
the terminal.

## Done when

- `python -m voirdire bench seeds/ward-demo` prints both arms and writes a
  report a stranger could check.
- Two consecutive runs produce identical output.
- The report contains false refusals and regressions, not just wins.
- A test proves the gate path never imports `history` or `store`.
- Deleting all the traps from a copy of the corpus makes the difference between
  the arms go to zero. If it does not, you are measuring something else.

---

# B2 — the five pages

Static HTML over the ledger. Light, plain, readable, no framework, no build
step, no CDN. They must open from `file://` with the wi-fi off.

| page | shows |
|---|---|
| `docket.html` | every rule, its receipt, binding or advisory, sortable |
| `case.html` | one closure that came back, and the rule it produced |
| `refusal.html` | a single refusal in full, with its next step |
| `overruled.html` | rules retired by three successful overrides |
| `numbers.html` | the benchmark table, regressions included |

**How they get their data:** a small `voirdire/board.py` reads the ledger and
writes `web/data.json`; the pages `fetch` it. No page imports the gate; no page
runs Python.

**Requirements:**

- Every rule shown anywhere carries its receipt. A rule on screen without
  `fired n/n, wrong 0/n` next to it is the thing this project exists to
  replace.
- Binding and advisory must be visually distinct at a glance, and the page must
  say what the difference means in one sentence somewhere.
- `overruled.html` is not an error page. A retired rule is the system working
  correctly and should read that way.
- `numbers.html` shows the losses. Same table, same weight, not a footnote.

**Two things that went wrong on the previous build's pages:**

- A descendant selector (`.row i`) matched more than intended and blew one
  element up to 52px. Scope your selectors to direct children.
- Generated bitmap text with characters missing from the font rendered `HALT`
  as `L`. If you generate any image, verify every glyph you use exists.

---

# B3 — board and packaging

- **`voirdire/board.py`** — the one-screen summary a reviewer sees first:
  wards, cases, binding vs advisory counts, the headline number, last refusal.
  Also the thing that writes `web/data.json`.
- **`python -m voirdire`** with no arguments prints the verbs and one example
  each. It currently errors, because the subparser is `required=True`.
- **`pyproject.toml`** — `pip install -e .`, console script `voirdire`, Python
  3.12, **zero dependencies**. If a dependency appears, something has gone
  wrong; check it is not being pulled in by a test helper.
- **README stays honest.** Whatever is not done stays in the "not done"
  section. Do not quietly delete a line because the demo is soon.

**The acceptance test:** a clean clone on a machine with nothing but Python
3.12 —

```bash
git clone https://github.com/mounika-200622/VOIR-DIRE && cd VOIR-DIRE
pip install -e .
python -m pytest -q
python -m voirdire learn seeds/ward-demo
python -m voirdire bench seeds/ward-demo
```

— all five commands work, no network. Actually do this, on a different machine
or a fresh virtualenv. "Works on mine" has failed at every hackathon anyone has
ever been to.

---

# Working agreement

**The only thing you and Person A share is the ledger** at
`<ward>/.voirdire/ledger.db`. Read it through `Ledger`. Never import each
other's modules; never edit each other's files.

`seeds/` is Person A's. Read it, run against it, never write to it. If a trap
you need is missing, ask.

**Merge discipline:**

- Never `git push --force`. The remote carries a teammate's dashboard commit.
- Small commits, one idea each.
- Anything touching `voirdire/` core gets raised before it is written.
- `python -m pytest -q` green before every push. If it is red, say which test
  and why, in the message.

---

# Go and read PRECEDENT first

**https://github.com/santoshcheethiralame-dot/PRECEDENT**

This is the same engine pointed at coding agents, and it is **finished**. Every
single thing in this brief exists there in working form. You will save days.

Specifically:

- **`precedent/bench/`** — a finished multi-arm harness with `attempted`,
  `vacuous`, the refuse-to-report guard, and the report writer. Read
  `run.py` and `tasks.py` before you design yours.
- **Its commit history** is a written record of **four separate attempts that
  produced fake results before one produced a real one**: a hang, a fake 100%,
  a rate limit scored as passes, and a model too weak to attempt the task. Each
  fix is in a commit message.
- **`web/`** — six working pages, including the chart and the overruled page.
- **`docs/SCRIPT.md`** — every feature in plain language, long form. Start from
  its tone for anything a reviewer will read.
- **The numbers to aim at**, from 300 runs: pass 53.3% to 70.0%,
  repeat-failure 58.1% to 31.0%, false positives 0.0%, 68 blocks, and — the
  important part — **9 regressions published next to 34 wins**.

**What not to copy:** `packs.py`, the harness, the opencode plugin, anything
about repositories or shells. That is the domain-specific half and none of it
transfers.
