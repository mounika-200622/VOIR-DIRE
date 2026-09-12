# Showing it

Everything here has been run end to end. Ports, commands and expected output are
literal — if a line below does not appear on screen, something is broken and the
demo should stop rather than be talked over.

---

## Before the room

Five minutes, once.

```bash
cd voiddire
pip install -e .
python -m pytest -q                  # 239 passed
```

Then make sure the two surfaces both come up:

```bash
python -m voiddire board            # the office, port 8850
python -m voiddire demo             # the race, ports 8900-8902
```

Leave both running in separate terminals. `demo` holds three ports and dies with
its shell.

**Check the board says nothing is missing.** It lists every page and names any
data file that is absent, along with the command that produces it:

```
  docket: 6 cases, 4 binding, 2 advisory, 0 overruled

  http://127.0.0.1:8850/desk.html       the desk: live, or the recorded session
  http://127.0.0.1:8850/cabinet.html    the docket, and every case file in it
  http://127.0.0.1:8850/chart.html      the evidence: does it help, and where does it hurt
  http://127.0.0.1:8850/tape.html       three hundred runs, replayed
  http://127.0.0.1:8850/overruled.html  how a rule loses its authority
```

If it prints a `missing` block, run the command it names before you present.

---

## The ninety seconds

Open on **the race**, at `http://127.0.0.1:8900`, and say one sentence:

> Same task, same model, same seed, one clock. The left agent has no memory. The
> right one has been here before.

Press **Play**. Do not narrate while it runs.

| beat | what appears |
|---|---|
| ~0:02 | both agents read `models/patient.py` |
| ~0:05 | both write the field. **The right one is HALTED** |
| ~0:07 | the halt card slides in, citing holding No 1 and naming the file to create |
| ~0:10 | the right agent writes `migrations/003_phone_verified.sql` |
| ~0:14 | **left: "Service unavailable — no such column: phone_verified"**. Right: the patient list, with a new VERIFIED column |

Then the only line that matters:

> Nobody had to read a diff to see which one is still standing.

**If Play does nothing**, the previous run finished and the state is on the
server. Press it again — it now resets first — or hit **Reset** then **Play**.

---

## The five minutes, if they want depth

Go to `http://127.0.0.1:8850/desk.html`. With no watcher running it plays a
**recorded** session, labelled `replay` in the status pill. It is a real capture
of `voiddire watch`, not an animation.

Three objects on that wall are doors. Click them in this order.

### 1. The cabinet → the docket

Four drawers by authority. Pull **binding**. The folders in the drawer are the
rules — click one and the file opens beside the cabinet.

Stop on **the receipt**. This is the part no other tool in this category has:

> `1/1` fired on its own case · `0/5` false on past successes · `6` times cited
>
> *It fired on the case that produced it, and stayed silent across 5 past runs
> that succeeded. That is what buys it the authority to stop a change.*

Then show a rule that **did not** get that authority — the advisory drawer, No 5:

> *It did not fire on the case that produced it. A rule that misses its own case
> cannot be trusted to catch the next one, so it was demoted to advice.*

That contrast is the argument. A memory layer that trusts every lesson it
extracts is one that gets confidently wrong.

### 2. The corkboard → the evidence

Lead with the result, which is what the page now does:

| | A — no memory | C — binding gates |
|---|---|---|
| first-try pass | 53% | **70%** |
| on trapped tasks | 39% | **61%** |
| fell for the same trap twice | 58% | **31%** |
| stopped, and passed anyway | — | **54 of 58** |

Then scroll to the second sheet and say the uncomfortable part out loud, because
they will find it anyway:

> Below about **21% compliance this makes agents worse than no memory at all.**
> A gate the agent ignores costs a run and buys nothing.

And the four caveats below it — false positives, the 9 regressions, arm B unrun,
the synthetic agent. **Do not skip these.** A panel that finds a caveat you hid
stops believing the headline; a panel that watches you volunteer one starts
believing everything else.

### 3. The in-tray → the tape

Press **run the tape**. 300 runs in about three seconds, five rows per arm, one
row per seed, left to right in the order they ran.

> Arm A stays scattered. Arm C greens toward the right of every row, because the
> precedents that stop it were established earlier in that same run.

The numbers under it: first ten tasks of a seed → last ten. **A: 46% → 48%.
C: 50% → 86%.** That is the claim with no sentence attached.

---

## If they ask to try it themselves

This takes ninety seconds in any repository and it is the strongest thing you
can do, because nothing is seeded:

```bash
cd ~/some-project
voiddire rule "models/*.py needs migrations/"
#   Changing models/*.py means changing migrations/ too.
#   co_change( models/*.py -> migrations/** )
#   BINDING

# edit a model, do not write a migration
voiddire gate .
#   HALT   BINDING HOLDING No 1   ESTABLISHED 11 SEP 2026
#   models/patient.py changed, nothing under migrations/** did
#   DO THIS NEXT:  create migrations/002_voiddire.sql
```

Point at the last line. **That filename is not a template** — it is read off
their repository's own migration naming.

Then:

```bash
voiddire why models/patient.py     # which rules apply here, and the case behind each
voiddire off 1                     # this rule is wrong
voiddire gate .                    # passes now; the case is still on file
voiddire init                      # mine their git history for rules
```

`init` is worth running on a real repo in front of them, because it is also
willing to find nothing — on a history with no habit strong enough to be a rule
it says so rather than inventing one.

---

## Inside opencode

```bash
voiddire opencode        # installs the plugin into .opencode/plugins/
voiddire serve           # the plugin decides nothing on its own
opencode
```

Ask it to add a field to a model. The write is **aborted before the bytes land**
and the card goes back to the model as the tool's error.

Worth naming: Autopsy's plugin has the same hook and its own comment says it
*"never blocks a tool call, even if the service returns block=true."* Ours
throws. That is the entire difference between the two projects in one line.

---

## Questions you will get

**"Isn't this just a linter?"**
It is a linter nobody wrote. The rules come from this repository's own failures,
they carry the case that created them, and they are retired when the evidence
turns against them. Show the receipt and the overruled page.

**"What if it blocks something it shouldn't?"**
`voiddire off <n>` mutes it and keeps the case. A tool that blocks you once for
a bad reason and gives you no way out gets uninstalled, and everything it ever
learned goes with it. Also: false positives are a headline metric on the
evidence page, not a footnote — measured at 0.0% across 540 runs, and we found a
real one in live testing and put it on the page.

**"Does it need a model / an API key / a database?"**
No, no and no. Python and the standard library. One SQLite file. The model is
optional and only fills in a typed schema when compiling a case; with none
reachable the deterministic fallback takes over. It runs on a closed laptop.

**"Has it been proven against a real agent?"**
Partly, and here is exactly how far. The 300-run benchmark uses a scripted
agent, which measures the enforcement layer rather than a language model — the
page says so. Against real models the plugin has been shown to block live. The
three-arm comparison against a live model is **not** done, and the reason is on
the page.

**"Why not a knowledge graph like theirs?"**
At 41 cases, 9 node types and 8 edge types with a 3-hop recursive query encodes
nothing that four tables and a cosine do not. We would rather spend the
complexity on proving it works. That is on the slide, deliberately.

---

## What not to do

- **Do not run the live benchmark in the room.** It takes 11–50 minutes and it
  depends on a provider being reachable.
- **Do not open `demo.html` from the board.** The race lives on port **8900**
  under `voiddire demo`; the copy served at 8850 has no apps behind it and the
  panes will read "unable to connect".
- **Do not claim arm B.** "Gates beat warnings" is the thesis, not the finding.
  The finding is "gates beat no memory", and it is worth having on its own.
