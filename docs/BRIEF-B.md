# Brief B — the proof

You own the number. Read `CLAUDE.md` first; it has the argument, the API and
the constraints. Do not edit `voirdire/` core.

Your files: `voirdire/bench/`, `web/*.html`, `voirdire/board.py`.

---

## B1 — the two-arm benchmark

The claim is "fewer complaints come back." Measure it.

- **Arm A (control):** replay a ward's closures with the gate off.
- **Arm B (gated):** replay the same closures through `gate.on`. A refused
  closure is not filed; it is filed later with the evidence the gate demanded.

The headline number is the **repeat-complaint rate** — closures that came back
— per arm. Secondary: refusals, false refusals (a refusal on a closure that
in fact held), overrides, advisory-only mentions.

Non-negotiable, all learned the hard way on the previous build:

- **Ground truth comes from `history.py` only, and the gate never sees it.**
- **Every row carries an `attempted` flag.** A benchmark whose oracle a
  do-nothing run already passes reports 100% and means nothing. This happened.
- **Refuse to write the report** if more than 10% of runs never really ran.
- **Publish the regressions.** Cases where the gate made things worse go in the
  table next to the wins. That is the difference between a result and a pitch,
  and reviewers notice.
- Deterministic and seeded. Same input, same number, every time.

**Done when:** `python -m voirdire bench seeds/ward-demo` prints both arms and
writes a report a stranger could check.

## B2 — the five pages

Static HTML over the ledger. Light, plain, no framework, no build step.

| page | shows |
|---|---|
| docket | every rule, its receipt, binding or advisory |
| case | one closure that came back and the rule it produced |
| refusal | a single refusal in full, with the next step |
| overruled | rules retired by three successful overrides |
| numbers | the benchmark table, regressions included |

Each page reads the ledger. None of them import the gate.

## B3 — board and packaging

- `voirdire/board.py` — the one-screen summary the reviewer sees first.
- `python -m voirdire` with no arguments prints the verbs.
- README stays honest about what is not done.
- `pip install -e .` and `python -m pytest -q` from a clean clone, on a machine
  with nothing but Python 3.12.

---

## The integration point

You and A share exactly one thing: **the ledger**
(`<ward>/.voirdire/ledger.db`). Read it with `Ledger(...)`. Do not import each
other's modules. A owns the data in `seeds/`; if you need a trap that does not
exist, ask — do not edit the seeds yourself, or the benchmark will be measuring
a corpus you tuned to it.

## Merge discipline

Never force-push. Small commits. If a change has to touch `voirdire/` core,
raise it before writing it — every other module assumes that surface is stable.
