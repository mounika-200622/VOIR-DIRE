# VOIR DIRE

**A pothole gets reported. The ward marks it resolved. Three weeks later
somebody reports the same pothole, as a new complaint.**

Nobody checked. The body measured on how fast it closes complaints is the body
that decides when one is closed.

Voir dire sits in front of that button. Before a closure is filed it asks
whether the evidence for it exists — and if it doesn't, it **refuses the
closure and says exactly what to attach**.

```
$ python -m voirdire gate seeds/ward-demo 11

  REFUSED   BINDING RULE No 1
  Closing a pothole needs a photo of the finished work.
  needs_evidence( pothole : photo_after )
  no photo_after on complaint 11; nothing attached
  DO THIS NEXT:  photograph the finished work at opp. 3rd Cross bus stop and attach it
```

That landmark is not a template. It is read off the complaint the citizen filed.

---

## The idea

Named for the examination a juror sits through before being allowed to judge
anything. Every rule here goes through the same thing.

**The problem with a tool that refuses things** is that it will refuse the
wrong thing, and then it gets switched off — and everything it learned goes
with it. That is why every comparable system stays advisory: advice cannot be
expensively wrong.

So a rule earns the right to refuse. Before it can block a single closure it is
replayed against the ward's own record and has to pass two tests:

1. **It fires on the closure that produced it.** A rule that cannot catch its
   own case will not catch the next one.
2. **It stays silent on every closure that held.** A rule that would have
   refused a repair that was genuinely finished is a rule that sends a crew
   back to a road that is already fixed.

Fail either and it is demoted to advice. It still speaks. It cannot stop
anyone.

Every rule carries that receipt, in public:

```
  BINDING   needs_evidence( pothole : photo_after )
            Closing a pothole needs a photo of the finished work.
            tested: 1/1 fired on its own case, 0/4 wrong on closures that held
```

---

## What it checks

Four shapes. A rule is one of these with the blanks filled in — which is what
makes it printable, arguable, and switch-off-able.

| | |
|---|---|
| `needs_evidence` | closed with nothing attached |
| `needs_time` | closed faster than this work has ever taken here |
| `evidence_on_site` | the after-photo was taken somewhere else |
| `not_while_open` | closed while the same asset has other complaints open |

The thresholds are **measured, not chosen**. *"How long has this kind of job
actually taken in this ward, when it stuck?"* is a question the records answer,
so a rule built that way can be argued with using the same records.

---

## Try it

```bash
python -m voirdire learn  seeds/ward-demo     # read what already went wrong
python -m voirdire docket seeds/ward-demo     # every rule, and its receipt
python -m voirdire gate   seeds/ward-demo 11  # would this closure be refused?
python -m pytest -q
```

`gate` exits 1 when a closure would be refused, so it drops into whatever a
ward already runs without ceremony.

---

## How it is built

```
Python 3.12, standard library only.  No Docker, no database server, no API key.
One SQLite file per ward. Four tables: runs, cases, holdings, citations.
Runs offline on a clerk's laptop.
```

**No model is involved in a decision.** The gate is deterministic — you cannot
ship a wall that a language model can talk its way past. Nothing here even
needs one: a failed closure has a small number of visible things wrong with it,
and each maps onto one of the four shapes.

The one piece kept deliberately apart is `history.py`, which knows how a
closure actually turned out. That is knowable only in hindsight, so it is used
for exactly two things — making a case out of a closure that came back, and
testing a proposed rule against ones that held. **The gate never sees it.**
Otherwise the thing would be marking its own homework.

---

## Where this is

**Stage 1 is in.** The ledger, the claim, the four checks, empanelment, the
gate, learning from history, and the instruction line. 14 tests.

Two things are honestly not done:

- **The seeded wards have the structure but not the traps.** Every closure in
  `seeds/ward-demo` currently carries a photo and took two days, so there is
  nothing yet for the gate to catch. `tests/test_ward_traps.py` is a contract
  for that corpus — three of its five checks fail today and each names exactly
  what the data needs.
- **No measurement yet.** Two arms, one ward closed with the gate and one
  without, and the number that matters is the repeat-complaint rate. That is
  stage 3, and it will publish the cases where the gate made things worse as
  well as better.
