# Brief A — the product

You own everything a judge sees happen. Read `CLAUDE.md` first; it has the
argument, the API and the constraints. Do not edit `voirdire/` core.

Your files: `seeds/`, `web/ward/`, `voirdire/demo.py`.

---

## A0 — plant the traps (do this first, everything else is blocked on it)

`seeds/ward-demo` has the right shape and no mistakes in it. Every closure
carries a photo and took 48 hours, so the gate finds nothing, the dashboard
shows nothing, and the benchmark measures nothing — and each of those looks
like the gate failing rather than the data being empty.

`tests/test_ward_traps.py` is the contract. Three of its five checks fail
today. **Make them pass by changing the data, not the test.**

Copy the shape from `tests/ward.py`, which plants all four traps correctly.

Per ward you need, roughly, 30–40 complaints:

- **at least 6 clean closures that held** — photo at the site, plausible
  duration. Without these there is no way to measure a false alarm, and
  empanelment has nothing to test a rule against.
- **bare** — `"evidence": []`. The commonest failure in the real dataset.
- **fast** — closed within minutes of `assigned_at`. A pothole is not repaired
  in four minutes.
- **away** — an after-photo a few hundred metres from the complaint's
  `location`. This is the check that matters most: is this evidence, or is it
  paperwork?
- **dupe** — one complaint on an asset closed while others on the same
  `asset_id` stay open.
- **each failure needs its return**: a later complaint on the same `asset_id`.
  That later complaint is what `history.came_back()` detects, and it is the
  only reason a rule ever gets proposed.

Do all three wards (`ward-demo`, `ward-water`, `ward-lights`) — different
`kind` values so the thresholds differ per ward and you can show that they are
measured, not hard-coded.

Landmarks must be real Bangalore ones and specific; the instruction line quotes
them verbatim, and "opp. 3rd Cross bus stop" is what makes the demo land.

**Done when:** `python -m pytest -q` is fully green, and
`python -m voirdire learn seeds/ward-demo` files at least one binding rule and
at least one advisory one.

## A1 — the dashboard refuses

`voir-dire/` already has the teammate's ward dashboard. Wire the RESOLVED
button to the gate.

```python
verdicts = gate.on(led, ward, Claim.proposed(ward, cid, evidence, closed_at))
if verdicts:  # refuse; render v.says, v.rule, v.reason, and the next step
```

- Refusal must show the **receipt** (`n/n fired, 0/n wrong`) — the refusal is
  only defensible because of it.
- Advisory rules render too, in a different weight, and do **not** block.
- The override path must exist and must be logged
  (`overrule.record_outcome`) — a gate with no override is a gate that gets
  switched off.

**Never call `store.is_invalid_closure()` from this path.** See CLAUDE.md §3.

## A2 — the split-screen demo

One complaint, two panes, same click. Left: the ward as it works today —
closure accepted, three weeks later the same pothole reported again. Right:
voir dire — refused, evidence attached, closed once.

Scripted and deterministic. No live model, no network.

## A3 — ward verbs

`python -m voirdire ward <ward>` — one screen: complaints, closures, which
rules are binding, what came back. This is what gets demoed when the laptop
cannot reach anything.

---

## The integration point

You and B share exactly one thing: **the ledger**
(`<ward>/.voirdire/ledger.db`). Read it with `Ledger(...)`. Do not import each
other's modules.
