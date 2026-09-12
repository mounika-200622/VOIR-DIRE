# VOID DIRE

**Your coding agent forgot the migration again. You told it not to, on Tuesday.**

Void Dire turns a confirmed failure into a **binding check** — deterministic,
executable, and cited to the run that established it. Not a paragraph in the
system prompt, which a model is free to ignore, but a rule that fires on the
working tree and stops the change.

```
Autopsy tells the agent about the crash. Void Dire takes the keys.
```

- **Measured**: 300 runs, 53% → 70% first-try pass, repeat failures 58% → 31%
- **Honest**: it publishes where it makes agents *worse*, and the 9 tasks it broke
- **Free**: Python and the standard library. One SQLite file. No Docker, no
  Postgres, no embedding API, no key required for any part of it
- **Any agent**: blocks inside **Claude Code** and opencode; reads git, not the
  agent, so Cursor and a person typing by hand get the same treatment

---

## Contents

1. [See it](#see-it) · 2. [Install](#install) · 3. [Use it](#use-it-on-your-own-repo)
· 4. [Stop the write](#stop-the-write-before-it-lands) · 5. [Look at what it
learned](#look-at-what-it-learned) · 6. [How a lesson becomes
law](#how-a-lesson-becomes-law) · 7. [What it checks](#what-it-checks) ·
8. [The numbers](#the-numbers) · 9. [What is not
proven](#what-is-not-proven) · 10. [Against Autopsy](#against-autopsy) ·
11. [Commands](#every-command) · 12. [Architecture](#architecture)

Presenting it? [`docs/DEMO.md`](docs/DEMO.md) is the run sheet.

---

## See it

```bash
python -m voiddire demo        # then open http://127.0.0.1:8900
```

Two copies of the same app, two agents, one clock, one task: *add a
`phone_verified` field to the Patient model*. The left agent has no memory. The
right one has the ledger.

Left edits the model, skips the migration, and **its app goes down on screen** —
*"Service unavailable: no such column: phone_verified"*. Right is halted
mid-edit by a card citing holding No 1, writes the migration, and stays up.

You do not have to read code to see which one is still standing. That is the
point: this is a developer tool, and a panel that cannot read a diff can still
see an application die.

---

## Install

```bash
pip install -e .
```

No dependencies. The part that blocks a write is stdlib only and installs
anywhere without argument. `pip install -e ".[art]"` adds Pillow, needed only to
regenerate the sprites.

---

## Use it on your own repo

Run these **in your repository**, not in this one.

```bash
voiddire init                                  # learn this repo's habits
voiddire rule "models/*.py needs migrations/"  # or just tell it
voiddire why models/patient.py                 # what applies here?
voiddire gate .                                # exits 1 if a rule fires
voiddire off 4                                 # this rule is wrong
voiddire status                                # what it caught this week
voiddire hook                                  # git pre-commit hook
voiddire claude                                # block writes inside Claude Code
voiddire watch                                 # live, with any agent
```

### `watch` is the one that works everywhere

It reads **git, not the agent**, so opencode, Cursor, Claude Code and a person
typing by hand all get the same treatment, and there is no plugin to keep up to
date per harness:

```
  HALT  Changing models/*.py means changing migrations/ too.
        models/patient.py changed, nothing under migrations/** did
        do this next: create migrations/105_patient.sql
  CLEARED  No 4 satisfied. The change may land.
```

That `do this next` filename is not a template. It is read off the repository's
own migration naming.

### `init` is the one that matters

An empty ledger on day one is useless — it is the single biggest adoption
problem a memory layer has, and Autopsy has it too. `init` reads your commit
history and proposes rules before anything has gone wrong. On real repositories
it finds real things: in `caliper` it worked out that `results/` never moves
without `docs/`, a working practice nobody had written down.

It is also willing to find nothing. On a repo whose history shows no habit
strong enough to be a rule it says so, because inventing one would be worse.

Three tests decide whether a pairing becomes a proposal:

| | |
|---|---|
| **support** | seen together often enough to be a habit, not a coincidence |
| **confidence** | P(B given A) — touching A really does mean touching B |
| **asymmetry** | P(A given B) is *low* — otherwise the two simply move together and the data cannot say which is the trigger |

The third one took measuring. Without it, an initial commit that touches every
directory makes everything "always" pair with everything, and two things that
genuinely move as one support *"A needs B"* exactly as much as *"B needs A"*.

Everything `init` proposes lands **advisory**. History is evidence about habits,
not proof that breaking one causes harm. `voiddire confirm <n>` promotes, and
empanelment still gates the promotion. A rule *you* write binds immediately,
because you know your own repo — but it is still replayed against past work and
demoted if it would have blocked something that already succeeded.

`gate` exits 1 when a binding holding fires, so it drops into a pre-commit hook or CI
without ceremony. `off` mutes a rule without deleting the case that produced it:
a tool that blocks you once for a bad reason and offers no way out gets
uninstalled, and everything it ever learned goes with it.

---

## Stop the write before it lands

`watch` reports; it cannot refuse. Two integrations actually refuse.

### Claude Code

```bash
voiddire claude                    # installs the hook into .claude/
git add .claude && git commit -m "install voiddire"
```

That is the whole setup — **no service to start, no daemon, no key.** It
registers a `PreToolUse` hook that sees `Write`, `Edit`, `MultiEdit` and
`NotebookEdit` *before* the bytes reach the disk, and denies the call if a
binding holding fires. The card goes back to the model as the reason it was
refused:

```
BLOCKED BY VOID DIRE - this exact change failed here before.

  Holding No 1, established 12 Sep 2026. Changing models/*.py means changing migrations/ too.
  Rule:   co_change( models/*.py -> migrations/** )
  Reason: models/patient.py changed, nothing under migrations/** did
  Tested: 1/1 fire, 0/5 false positives.
  DO THIS NEXT: create migrations/002_patient.sql
```

It also registers `UserPromptSubmit`, which puts the rules in front of the
model *before* it starts. That half matters more than it looks: being blocked
costs a whole turn and the model has to work out why; being told costs a
sentence and it complies the first time. Our own compliance sweep says the gate
is not the mechanism — the instruction is.

If `voiddire serve` happens to be running it will use it, so the desk page
lights up as decisions happen; if not, it answers in-process. Either way the
verdict is identical, and **every failure path allows the write** — no ledger,
bad payload, unreachable service, or an outright crash all mean *allow*.

### opencode

```bash
voiddire opencode          # installs into .opencode/plugins/
voiddire serve             # the plugin decides nothing on its own
opencode
```

It throws in `tool.execute.before`, which aborts the tool call **before the
bytes reach the disk**, and the halt card goes back to the model as the tool's
error. It fails open on a timeout: a memory layer that can stall your agent by
being down is worse than no memory layer.

Both surfaces build the same card from the same `gate.evaluate`, and a test
asserts they stay byte-identical — an agent should not be able to tell which
harness refused it.

Three modes, and they are the three arms of the benchmark:

| mode | what the agent gets |
|---|---|
| `--mode off` | nothing. Arm A |
| `--mode advise` | every rule as prose, nothing blocked — what Autopsy does. Arm B |
| `--mode enforce` | the rules named in the prompt **and** the write refused. Arm C |

Enforce tells the agent up front *and* stops it. Being stopped costs a whole
turn and the model has to work out why; being told costs a sentence and it
complies the first time.

End to end, in a repository with one rule and no failure yet:

```
$ voiddire rule "models/*.py needs migrations/"
  Changing models/*.py means changing migrations/ too.
  co_change( models/*.py -> migrations/** )
  BINDING

$ voiddire gate .
  HALT   BINDING HOLDING No 1   ESTABLISHED 11 SEP 2026
  Changing models/*.py means changing migrations/ too.
  models/patient.py changed, nothing under migrations/** did
  DO THIS NEXT:  create migrations/002_voiddire.sql
```

---

## Look at what it learned

```bash
voiddire board
```

Five pages, static, no build step, and every one renders with nothing running.

| | |
|---|---|
| **the desk** | live while `voiddire watch` runs; otherwise it plays a **recorded** session, labelled as a replay. Not an animation — a real capture of the watcher |
| **the docket** | every case on file. Click a folder in the drawer to open its file: the holding, the receipt, the facts, the citations, its overruling standing |
| **the evidence** | the result first, then the compliance curve including the zone where the tool makes agents *worse*, then the caveats |
| **the tape** | 300 runs replayed in three seconds, arm A against arm C |
| **overruled** | how a rule loses its authority, and where every binding rule currently stands |

`board` names any missing data file and the command that produces it, so a page
never quietly shows less than it should.

---

## How a lesson becomes law

**Case** → a failed run: a human rejection, a failing check, or a free signal —
a file rewritten inside one run, a revert, tests that flipped green to red.

**Holding** → the case compiled into one of eleven typed checks. A model's only
job is choosing a template and filling its blanks; it never writes a checker,
because a small free model fills a schema reliably and writes novel code badly.
Nothing fits → a prose warning, labelled as the weaker tier.

**Empanelment** → the part that makes *binding* mean something. A holding is
replayed against history before it gets any authority: it must fire on the case
that produced it, and stay silent across the stored working trees of past
**successful** runs. Fail either and it is demoted to advice. With no history to
test against it stays advisory, and a later passing run can promote it.

Every card carries the receipt, and there are three distinct verdicts in the
ledger right now:

| | |
|---|---|
| `1/1 fire · 0/5 false` | fired on its own case, silent across five past successes → **binding** |
| `tested: 0` | *no successful run to test against yet* → advisory, untested |
| `0/1 fire` | **it did not fire on its own case** → advisory, and rightly distrusted |

**Citation** → every firing is recorded with what happened next: complied/passed,
complied/failed, overridden/passed, overridden/failed.

**Overruling** → only a run that overrode a rule and succeeded *anyway* counts
against it. At **3** such runs, with more against than for, the rule is retired,
stops blocking anything, and is published on the overruled page with the
evidence that killed it. Being wrong in public is the point.

### The pairing is learned, not authored

The fallback compiler needs no model at all. It reads the repo's own successful
runs and finds the directories that were **never changed alone** — then, when a
failing run changes one without the other, it proposes exactly that rule. In the
seeded app it learns `models/*.py -> migrations/**` from one run that went right
and enforces it on the one that goes wrong.

---

## What it checks

Twelve templates, grouped into seven domains a person can read.

| domain | what it asks |
|---|---|
| **structure** | the thing you touched has a partner that did not move — `co_change`, `must_run`, `required_command`, `forbidden_edit` |
| **security** | secrets, destructive migrations, TLS turned off, **and the agent editing the gate itself** |
| **hygiene** | debuggers, `console.log`, stubs, swallowed exceptions, empty catch blocks |
| **tests** | you deleted a test, you skipped one instead of fixing it, a generated regression test fails |
| **context** | `blast_radius` — you changed a function's shape and 14 callers did not move |
| **cost** | `no_quadratic` — the lines this change *added* have a quadratic shape |
| **borrowed** | four gates from [sleeper](../sleeper): what it imports, doc drift, measured-vs-claimed cost, duplicate functions. Abstains when sleeper is absent |

**25 rules ship in the pack**, 9 of them binding, installed only where a repo can
trip over them. The split is about false positives, not severity: a live AWS key
is never intentional, but tests genuinely do get deleted during a refactor.

One of those rules exists only because this tool blocks:

> **`self_disarm`** — binding on `.voiddire/`, `.git/hooks/`,
> `.opencode/plugins/`, `opencode.json`.
> *"This turns the gate off. Change it yourself, not through the agent."*

An advisory tool has nothing worth disarming. This one does, and this repository
has been disarmed twice by the thing it was restraining — once when an agent
wrote into the seed corpus from outside its worktree, once when a plugin file
went missing and every benchmark arm silently became a bare agent still printing
numbers that looked like results.

---

## The numbers

Two arms, five seeds, thirty tasks across three repos, **300 runs**. Identical
tasks, identical agent, identical seeds — the only thing that differs is whether
void dire is enforced.

| | A — no memory | C — binding gates |
|---|---|---|
| first-try pass | 53.3% | **70.0%** |
| pass on trapped tasks | 39.1% | **60.9%** |
| **fell for the same trap twice** | **58.1%** | **31.0%** |
| false positives on control tasks | 0.0% | 0.0% |
| runs stopped, that passed anyway | — | **54 of 58** |
| regressions vs arm A | — | **9** |

```bash
python -m voiddire bench --arms A,C --seeds 1,2,3,4,5
```

### Every trap class moved

| trap class | A | C |
|---|---|---|
| changing a model, no migration | 57% | **85%** |
| changing the API, not the client types | 35% | **65%** |
| editing a generated file by hand | 33% | **53%** |
| adding a plugin, not declaring it | 25% | **38%** |

The third row took a new template to move at all. A co-change rule asks whether
the right directory moved, and an agent that hand-edits `client/generated.py`
instead of running the generator *does* touch the right directory, with the wrong
content. `forbidden_edit` is the obvious fix and the wrong one, because a
legitimate regeneration touches that same path. What separates them is **whether
the generator ran** — so the recorder learned to see commands, and `must_run`
asks that question, with the rule read out of the file's own words
(`GENERATED FILE - run tools/gen.py, do not edit by hand`).

### It starts level and pulls away

Pass rate over the first ten tasks of a seed, against the last ten:

| | first ten | last ten |
|---|---|---|
| A | 46% | 48% |
| **C** | 50% | **86%** |

Arm A has nothing to accumulate. Arm C greens toward the end of every seed
because the precedents that stop it were established earlier in that same run.

### And it depends entirely on the agent obeying

That headline was measured with an agent that always does what the halt card
asks. Sweeping that assumption is the more useful result — 5 points, 90 runs
each, 540 runs total:

```bash
python -m voiddire bench --compliance
```

| the agent obeys the card... | pass rate | repeat-failure | recovery |
|---|---|---|---|
| never | 53.3% | 64.6% | 43.2% |
| a quarter of the time | 60.0% | 52.1% | 59.5% |
| half | 67.8% | 37.5% | 78.4% |
| three quarters | 68.9% | 35.4% | 81.1% |
| always | 74.4% | 25.0% | 89.7% |

Arm A, for comparison, sits at **58.9%** pass and **50.0%** repeat-failure.

> **Below roughly 21% compliance this makes an agent worse than no memory at
> all.** Blocking something that then ignores you costs a run and buys nothing.

So the gate is not the mechanism — the **instruction** is. That is why every
halt card names the exact next action rather than saying "do the missing work",
and why enforce mode now also puts the rules in the prompt before the agent
starts.

---

## What is not proven

Five things, stated here rather than discovered by someone else.

**1. The agent is synthetic.** It performs each companion action with
probability `p_recall` from a seeded generator. This measures the enforcement
layer, not a language model.

**2. Arm B was not run.** Its entire mechanism is whether a model obeys a
paragraph in its prompt, which a scripted agent cannot answer. Four attempts,
four different blockers — and each one was a real bug found by trying:

- a subprocess with no deadline wedged the run (the agent started the seeded web
  server, which never exits)
- the oracle asked whether the repo was *consistent*, and a repo nobody touched
  is consistent — so a model that read files and stopped scored **100% in all
  three arms**
- a rate limit produced 90 runs that never reached the model, all scored as
  passes
- every free model reachable attempts only 1 task in 4, and `gpt-4o-mini`
  attempts **0 of 19** typegen and registry tasks

All four are fixed or guarded — the bench now refuses to write a report when
more than 10% of runs never reached the model, and "did nothing" no longer
counts as a pass. *"Gates beat warnings"* remains a thesis. *"Gates beat no
memory"* is the finding, and it stands on its own.

**3. Nine regressions.** Nine of 150 tasks passed without memory and failed with
it, six on `plugin_without_declaration`. A result showing the tool never hurts
would be the less trustworthy one.

**4. A live false positive.** Testing against a real model surfaced one the
synthetic benchmark never could: `must_run( client/*.py : tools/gen.py )` fired
on a control task that only edited a README. Empanelment did not catch it
because no past successful run had ever edited `docs/` alone, so the
false-positive test passed vacuously — **it can only refute a rule with evidence
it has.**

**5. `blast_radius` and `no_quadratic` are unmeasured.** Both are real checks;
neither has a trap class in the benchmark, so there is no number for them.

An earlier run was scored under a bytecode-cache bug and is kept as
`bench/report.prebugfix.json`. A `.pyc` records source mtime to one-second
granularity, and these runs write a module and import it inside the same second,
so Python could serve the previous version and score a failing run as a pass.
Every subprocess now sets `PYTHONDONTWRITEBYTECODE`.

---

## Against Autopsy

[balebbae/autopsy](https://github.com/balebbae/autopsy) is the reference. Where
it is ahead, it is said so.

| | Autopsy | Void Dire |
|---|---|---|
| **Mechanism** | prose injected into the prompt, advisory only | a **typed check that blocks**. Prose is a labelled weaker tier |
| **The plugin** | same hook; its own comment says it *"never blocks a tool call, even if the service returns block=true"* | **throws**, so the call aborts before bytes land |
| **Trust in a lesson** | live the moment it is extracted | **empanelment** — must fire on its own case and stay silent on past successes |
| **Lifecycle** | exponential decay inside a score | explicit status machine, and **overruled precedents are published** |
| **Signal source** | human rejections, postflight failures | same, plus **churn / revert / test-flip** — learns with no human in the loop |
| **Proof it works** | none; listed as future work | **300-run ablation**, published false-positive rate, published regressions |
| **Agent coupling** | opencode plugin only | **git + filesystem** — any agent. Plugin is the extra, not the requirement |
| **Store** | Postgres 16 + pgvector + Docker Compose | **one SQLite file** |
| **Embeddings** | Gemini `gemini-embedding-001`, needs a key | local bag-of-words, no key, no quota |
| **Retrieval** | ANN + 3-hop recursive CTE, 9 node and 8 edge types | cosine + scope filter over **4 tables** |
| **Cost** | free tier possible, stack is Postgres + FastAPI + Next.js | **$0, runs on a closed laptop** |
| **Session capture** | **every tool call, message, permission** | reads git — *less data, deliberately* |
| **Retrieval quality** | **real embeddings** | **bag-of-words, and it is measurably weak** |

Two places they are genuinely ahead:

1. **Retrieval.** Ours scored *"add a phone_verified field to the patient
   model"* against `models/*.py` at exactly **zero**, which left the agent with
   an empty prompt until it was found. The workaround is to name every binding
   rule rather than rank them. Their index is better.
2. **Session capture.** They record everything the agent does; we read the tree.
   Runtime-agnostic and less code, but less data.

The one-sentence version: *Autopsy tells the agent about the crash. Void Dire
takes the keys.*

---

## Every command

| | |
|---|---|
| `voiddire init` | mine git history and install the rule pack |
| `voiddire rule "..."` | teach it a rule in one sentence |
| `voiddire confirm <n>` | promote a mined rule to binding |
| `voiddire why <file>` | which rules apply here, and the case behind each |
| `voiddire gate .` | exits 1 if a binding holding fires |
| `voiddire off <n>` / `on <n>` | mute a rule without deleting its case |
| `voiddire status` | what it caught this week, and what it let through |
| `voiddire hook` | install the git pre-commit hook |
| `voiddire claude` | install the Claude Code hook that stops a write |
| `voiddire opencode` | install the opencode plugin that stops a write |
| `voiddire watch` | live decisions, any agent, any editor |
| `voiddire serve` | the HTTP face the plugin talks to |
| `voiddire docket` | list the cases and what they established |
| `voiddire reject "..."` | file a rejection against the working tree |
| `voiddire sweep` | re-decide every binding holding from its citations |
| `voiddire board` | freeze the ledger and serve the five pages |
| `voiddire demo` | the split screen: two apps, one clock |
| `voiddire bench` | run the arms, write `bench/report.json` |
| `voiddire live` | the three arms driven by real opencode |
| `voiddire replay` | record one real session for the desk |
| `voiddire dump` | the ledger as JSON |

---

## Architecture

```
agent run ──► recorder (git + fs + harvesters) ──► cases
                                                    │
                                        compiler (typed schema)
                                                    │
                                     empanelment (replay against history)
                                                    │
                      binding ◄──────────── holdings ────────► persuasive
                         │                      ▲                  │
                    gate: blocks            citations        prose in prompt
                         │                      │                  │
                         └────► run outcome ────┴──────────────────┘
                                      │
                                 overruling
```

Four tables: `runs`, `cases`, `holdings`, `citations`. Artifacts on disk, keyed
by run id.

**Everything free and local.** SQLite via stdlib `sqlite3`. Retrieval is a
bag-of-words cosine over a few hundred rows — no pgvector, no ANN index, no
Postgres, no Docker, no embedding API. A model is optional, speaks the
OpenAI-compatible protocol, and is used **only** to fill a typed schema when
compiling a case. It is never on the path of a gate decision.

```bash
export VOIDDIRE_BASE_URL=...   # default http://localhost:11434/v1 (Ollama)
export VOIDDIRE_MODEL=...
export VOIDDIRE_API_KEY=...    # optional
```

With no model reachable the deterministic fallback takes over.

**6,411 lines of Python. 247 tests.**

```bash
python -m pytest -q
```

---

## Why the name

Voir dire is the examination a juror sits through before being allowed to judge
anything. That is the first half of the mechanism: no rule here gets to refuse
a change until it has been replayed against this repository's own history and
shown that it catches its own case and stays silent on work that already
succeeded.

Void is the second half. An untested rule never binds. A binding rule that
three runs overrode and succeeded anyway is voided — retired, stripped of its
authority, and published on the overruled page with the citations that killed
it.

A memory that can only grow can only get more wrong. The name carries both
directions.
