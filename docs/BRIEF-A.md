# Brief A — the product

**You own everything a judge watches happen.** The data, the dashboard, the
demo, the offline ward view.

Read [`CLAUDE.md`](../CLAUDE.md) end to end before you write a line. It has the
argument, the whole API, and the constraints. This file assumes you have.

**Your files, and only these:**

```
seeds/ward-demo/  seeds/ward-water/  seeds/ward-lights/   (data)
voir-dire/                                                (dashboard - currently empty)
voirdire/demo.py                                          (new, yours)
voirdire/__main__.py                                      (the `ward` verb only)
```

**Do not touch:** `voirdire/db.py`, `gate.py`, `panel.py`, `empanel.py`,
`overrule.py`, `claim.py`, `templates.py`, `history.py`, `learn.py`,
`nextstep.py`. If you think one of them is wrong, say so before changing it —
Person B's benchmark assumes that surface is frozen.

---

# A0 — plant the traps

**Everything else is blocked on this. Do it first. Budget a full day.**

## Why this exists

`seeds/ward-demo` has 44 complaints and 34 closures. Every single closure
carries a photo, at the reported location, filed 48 hours after assignment.
The assets are named `ASSET-TRAP1..4`. **There are no traps in them.**

So today: the gate finds nothing, the dashboard shows nothing, the benchmark
measures nothing — and every one of those looks like *the gate failing* rather
than *the data being empty*. That confusion cost the previous build about six
hours. It is why the corpus gets a contract, checked the same way code is.

## The contract

`tests/test_ward_traps.py`. Five checks, **three fail today**.

```bash
python -m pytest tests/test_ward_traps.py -q
```

**Make them pass by changing the data. Never by changing the test.** If you
genuinely believe a test is wrong, raise it — do not edit it.

The three red ones and exactly what each wants:

| test | what the data needs |
|---|---|
| `test_some_closure_has_no_evidence` | at least one closure with `"evidence": []` |
| `test_some_closure_is_too_fast` | at least one closure less than **10 minutes** after `assigned_at` |
| `test_some_evidence_is_from_somewhere_else` | at least one `photo_after` more than **300 m** from the complaint's `location` |

The two already green — `test_some_asset_is_closed_while_others_stay_open` and
`test_there_are_control_closures_that_are_entirely_fine` (needs at least 6) —
must **stay** green. Run the whole file every time.

## The exact file format

Two files per ward, both plain JSON arrays. This shape is fixed by
`voirdire/claim.py`; nothing else is read.

`seeds/<ward>/data/complaints.json`

```json
{
  "id": 1,
  "kind": "pothole",
  "asset_id": "ASSET-TRAP2",
  "ward": 12,
  "location": { "lat": 12.9010, "lon": 77.5010, "landmark": "opp. 3rd Cross bus stop" },
  "reported_at": "2026-07-03T09:00:00Z",
  "assigned_at": "2026-07-03T10:00:00Z",
  "photos": ["before_1.txt"],
  "severity": "medium"
}
```

`seeds/<ward>/data/closures.json`

```json
{
  "complaint_id": 1,
  "closed_at": "2026-07-05T10:00:00Z",
  "closed_by": "crew-1",
  "evidence": [
    { "type": "photo_after", "file": "after_1.txt", "lat": 12.9010, "lon": 77.5010 },
    { "type": "work_order", "ref": "WO-1" }
  ],
  "note": "fixed"
}
```

**Field rules — get these wrong and checks silently abstain:**

- Timestamps are **exactly** `%Y-%m-%dT%H:%M:%SZ`. Any other format parses to
  `None`, and `needs_time` then returns `None` — no error, no refusal, nothing.
  This is the single most likely way to waste an afternoon.
- `assigned_at` drives `needs_time`. If it is missing, `reported_at` is used
  instead. If both are missing the check abstains.
- `location.lat` / `location.lon` are floats. Missing either and
  `evidence_on_site` abstains.
- Evidence `lat`/`lon` sit **on the evidence object**, not nested inside it.
- `asset_id` is the join key for both duplicates and history. A typo in it
  silently unlinks a failure from its return.
- `kind` is matched exactly by rules carrying a `kind` param. `"Pothole"` and
  `"pothole"` are different kinds.
- `landmark` is quoted **verbatim** into the refusal message. It currently says
  `"LM-1"`, which makes the demo worthless. Use real Bangalore landmarks:
  `"opp. 3rd Cross bus stop"`, `"near Ganesha temple, 5th Main"`,
  `"outside HDFC ATM, 80 Feet Road"`.

## The five things every ward needs

Copy the shape from **`tests/ward.py`** — it plants all four traps correctly
and is the reference implementation. Read it before you start.

### 1. Controls — at least 6, aim for 12

Closures that were genuinely fine and stayed closed. Photo at the site,
plausible duration, no later complaint on that asset.

**These are not filler.** They are what empanelment tests every proposed rule
against. With no controls, `empanel()` returns `persuasive` with the note
*"no closure has held long enough to test against yet"* and **nothing ever
becomes binding**. The whole project then looks broken.

### 2. Bare — closed with nothing attached

```json
{ "complaint_id": 10, "closed_at": "...", "closed_by": "crew-3", "evidence": [], "note": "attended" }
```

Commonest real failure. Catches `needs_evidence`.

### 3. Fast — closed minutes after assignment

`assigned_at` `10:00`, `closed_at` `10:04`. A pothole is not repaired in four
minutes. Catches `needs_time`.

**Threshold caution:** `learn._typical_minutes()` computes
`max(5.0, round(min(held_durations) * 0.5))` and needs **at least 3 held
closures of that same `kind`**. Fewer than 3 and it returns `None`, so no
`needs_time` rule is ever proposed. Each `kind` you use needs 3+ clean closures
of its own.

### 4. Away — photo from somewhere else

An after-photo a few hundred metres off. `metres_from_site()` is flat-earth:

```
dlat = (ev.lat - loc.lat) * 111320
dlon = (ev.lon - loc.lon) * 111320 * 0.68
distance = sqrt(dlat**2 + dlon**2)
```

**+0.0080 in latitude is about 890 m.** The trap test wants more than 300 m;
the rule fires above 120 m. Use roughly 900 m so it is unambiguous and reads
well on a map.

This is the check that matters most. A closure with a photo attached looks
complete to every dashboard ever built — this is the difference between
evidence and paperwork. Make sure the demo lands on it.

### 5. Dupe — one closed while others stay open

Four complaints on one `asset_id`, one closed, three left open, all three
`reported_at` **before** the `closed_at`. Catches `not_while_open`.

`open_on_same_asset()` only counts siblings reported *before* the closure. A
complaint filed afterwards is a return, not a duplicate.

### And the part people forget: every failure needs its return

A trap is only a *case* if the same `asset_id` is reported again **after** the
closure. That later complaint is what `history.came_back()` detects, and it is
the **only** reason a rule is ever proposed.

```
complaint 10  asset A-BARE  reported 05 Jul  -> closed 06 Jul with nothing
complaint 11  asset A-BARE  reported 26 Jul  -> the return. This is what makes 10 a case.
```

No return, no case, no rule. Four beautifully-crafted traps with no returns
produce **zero** rules and a completely silent gate.

## Scale and spread

Per ward: **30–40 complaints**, roughly 25–30 closures.

- at least 6 clean controls (12 is better)
- 4–6 traps, at least one of each of the four kinds
- one return per trap
- a few complaints still open, never closed — makes the dashboard look real

**Use a different `kind` per ward**, because that is how you demonstrate the
thresholds are measured rather than hard-coded:

| ward | kind | plausible honest duration |
|---|---|---|
| `ward-demo` | `pothole` | about 48 h |
| `ward-water` | `water_leak` | about 6 h (urgent) |
| `ward-lights` | `streetlight` | about 5 days (needs a crew and a part) |

Then `python -m voirdire docket` on each shows three different `needs_time`
thresholds, none of them written by a person. **Say that sentence out loud in
the demo.** It is the strongest thing in the project after empanelment.

## Do not tune the corpus to the gate

You own the data; Person B owns the number. If you keep adding traps until the
gate scores well, the benchmark measures nothing. Plant what a real ward
plausibly does wrong, then leave it alone. Person B has to be able to say the
corpus was fixed before the measurement was taken.

## Done when

```bash
python -m pytest -q                                  # fully green, 0 failures
python -m voirdire learn  seeds/ward-demo            # at least 1 binding AND 1 advisory
python -m voirdire docket seeds/ward-demo            # receipts on every rule
python -m voirdire gate   seeds/ward-demo <bare id>  # REFUSED, exit 1
python -m voirdire gate   seeds/ward-demo <good id>  # allowed, exit 0
```

and the same three for `ward-water` and `ward-lights`.

You want **at least one advisory rule** in the output. A docket where
everything is binding does not show the tiering, and the tiering is the
argument. A rule demanding `work_order` on every closure is the reliable way to
produce one — most honest closures do not have one, so it fails empanelment and
lands in advice. That is not a bug to fix; it is the system working, and it is
the best thing you can put on screen.

---

# A1 — the dashboard refuses

## Read this first: the dashboard is in the wrong place

`voir-dire/` is **empty** (just a `.gitkeep`). The ward dashboard is actually
at:

```
seeds/ward-demo/app.py            http.server on port 8901, /api/complaints
seeds/ward-demo/static/index.html
seeds/ward-demo/store.py          load_data, is_invalid_closure, get_complaints
seeds/ward-demo/oracle.py         deterministic pass/fail for the benchmark
```

**A web server living inside the benchmark corpus is a problem.** The previous
build had an agent write into pristine seeds twice, because `base / path`
silently discards the base when `path` is absolute. `seeds/` should hold data
and an oracle, nothing else.

**Your first move on A1:** move `app.py` and `static/` to `voir-dire/`, make
the ward a `--ward` argument instead of a hardcoded sibling directory, and
leave `store.py` and `oracle.py` where they are (the oracle imports them).

```bash
python voir-dire/app.py --ward seeds/ward-demo --port 8901
```

Do this before writing any new code. It gets harder every day you wait.

## The wiring

The RESOLVED button currently just files a closure. Put the gate in front of
it:

```python
from pathlib import Path
from voirdire import gate, nextstep, overrule, panel
from voirdire.claim import Claim
from voirdire.db import Ledger, ledger_path

ward  = Path("seeds/ward-demo")
led   = Ledger(ledger_path(ward))         # <ward>/.voirdire/ledger.db
scope = str(ward.resolve())               # ALWAYS resolve(). A relative path
                                          # and an absolute one are different
                                          # wards as far as the ledger knows.

claim = Claim.proposed(ward, complaint_id, evidence=evidence, closed_at=None)

sitting = panel.sit(led, scope, claim)    # every rule, fired or not
if sitting.halted:
    ...                                   # refuse
else:
    ...                                   # file the closure
```

Use **`panel.sit`**, not `gate.on`. `gate.on` returns only what fires — right
for a CLI exit code, wrong for a screen. A dashboard that only ever renders
refusals cannot render a closure being *cleared*, and a clerk who only sees the
tool when it says no will believe it says no to everything.

### What `sitting` gives you

```python
sitting.halted            # bool - any binding rule fired
sitting.touched           # ["ASSET-TRAP2", "complaint 11"]
sitting.notes             # advisory seats that fired
sitting.as_dict()         # JSON-ready, straight down the wire
sitting.seats             # list[Seat], sorted halt -> note -> skip -> clear
```

Each `Seat`:

| field | render as |
|---|---|
| `verdict` | `"halt"` red, `"note"` amber, `"clear"` grey tick, `"skip"` grey cross |
| `status` | `"binding"` or `"persuasive"` — **label these on screen** |
| `says` | the human sentence. The headline. |
| `reason` | why it fired *on this closure*, with real numbers |
| `next` | what to do about it. Present on advisory seats too. |
| `domain` | `evidence` / `timing` / `duplicates` — group by this |
| `holding_id` | link to the rule's own page |
| `took_ms` | put it on screen. Sub-millisecond is part of the argument. |

### Three things the refusal screen must show

1. **The receipt.** Pull it from the holding:

   ```python
   h = next(h for h in led.holdings(ward=scope) if h["id"] == seat.holding_id)
   e = h["empanel"]      # {"fire": "1/1", "false": "0/4", "false_ids": [], "tested": 4}
   ```

   Render it as: *tested — fired on 1/1 of its own case, wrong on 0 of 4
   closures that held.* **The refusal is only defensible because of this line.**
   A refusal without its receipt is every other tool that got switched off.

2. **Advisory rules, visibly weaker, not blocking.** Different weight, no red,
   button still enabled. If a `note` blocks anything you have destroyed the
   distinction the whole project is built on.

3. **The override.** Always available, one click, and **logged**:

   ```python
   run_id = led.open_run(scope, f"closure {claim.id}", arm="live")
   overrule.record_outcome(led, run_id, seat.holding_id, complied=False, passed=True)
   led.close_run(run_id, "pass")
   overrule.sweep(led, scope)     # 3 overridden_pass retires the rule
   ```

   A gate with no override is a gate that gets uninstalled in week two. Three
   overrides that succeed anyway and the rule retires itself, in public. Show
   that counter on the rule's page: *"overridden 2 of 3 — one more and this
   rule retires."*

## The line you must not cross

**Never call `store.is_invalid_closure()` from the gate path.** It is the
oracle's ground truth. If the gate consults it, the gate is marking its own
homework and the benchmark measures exactly nothing. The same goes for anything
in `voirdire/history.py`.

The dashboard may call `store` for *display* — showing which past closures came
back is fine and good. It must not reach `store` to decide whether to refuse.
Keep the two code paths visibly separate and comment the boundary.

## Done when

- Refusing a bare closure shows the sentence, the reason with real numbers, the
  next step naming the actual landmark, and the receipt.
- A good closure files, and the screen still shows the four rules that cleared
  it.
- An advisory rule appears, in the weaker style, and does not block.
- Override works, is logged, and the third one retires the rule.
- The gate path contains no reference to `store` or `history`.

---

# A2 — the split-screen demo

`voirdire/demo.py`, plus a page. One complaint, two panes, one click.

| left — the ward today | right — with voir dire |
|---|---|
| RESOLVED accepted, no questions | REFUSED, with the reason |
| the queue count goes up. Everyone is happy. | clerk attaches the photo |
| **three weeks later**: same pothole, new complaint | closed once, stays closed |
| the number the ward is measured on went *up* for work that was never done | |

**Requirements, all learned the hard way:**

- **Scripted and deterministic.** No live model, no network, no wall clock.
  Same input, same frames, every run.
- **Resettable.** The previous build's demo Play button did nothing on the
  second press because the server-side state was already at the end. Reset
  first, then play. Test it by pressing Play twice.
- **Show the change as judged, not as applied.** The old demo wrote the closure
  and *then* judged it, so both panes ended in the same state. The real gate
  refuses *before* the write. Roll back, and render what the gate saw.
- **Nothing over about 4 seconds per step.** A step in the previous demo took
  39 seconds because one check shelled out four times. Everything here is
  in-process and sub-millisecond; if a step is slow, something is wrong.
- **Land on `evidence_on_site`,** not `needs_evidence`. "You attached no photo"
  is obvious. "You attached a photo from 900 m away, and every dashboard in the
  country would have accepted it" is the moment people understand the project.

## The closing line

> The ward is measured on how fast it closes complaints. The ward decides when
> one is closed. Voir dire is the only thing in the room that is measured on
> whether it stayed closed.

---

# A3 — `python -m voirdire ward <ward>`

One screen, no server, for when the venue wi-fi dies. Add a `ward` verb to
`voirdire/__main__.py` next to `learn`, `docket` and `gate` — that is the only
file outside your list you may touch, and only to add this subparser.

Print, in this order:

1. ward name, complaint count, closure count, how many are still open
2. what came back — `history.came_back(ward)`, id / asset / landmark / why
3. the docket — every rule, binding or advisory, with its receipt
4. the counts — `led.counts(scope)`
5. the last refusal, in full, with its next step

Plain text, aligned, no colour codes (they render as garbage in a projector's
terminal). Must fit an 80x40 window without scrolling.

---

# Working agreement

**The only thing you and Person B share is the ledger** at
`<ward>/.voirdire/ledger.db`. Read it through `Ledger`. Never import each
other's modules; never edit each other's files.

**Merge discipline:**

- Never `git push --force`. The remote carries a teammate's dashboard commit.
- Small commits, one idea each.
- Anything touching `voirdire/` core gets raised before it is written.
- `python -m pytest -q` green before every push. If it is red, say which test
  and why, in the message.

**When you are stuck**, read
[PRECEDENT](https://github.com/santoshcheethiralame-dot/PRECEDENT). It is this
engine pointed at coding agents, it is finished, and `docs/SCRIPT.md` there
explains every feature in plain language. Its demo, its pages and its office UI
all exist and work.
