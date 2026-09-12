"""A synthetic agent with one knob.

It always does the obvious edit. Each companion action - the migration, the
regenerate, the registry entry - it remembers with probability `p_recall`, drawn
from a seeded generator. The SAME seed produces the SAME behaviour in every arm,
so the only thing that differs between arms is what the ledger is allowed to do
about what the agent already knows.

This measures the enforcement layer, not a language model. Arm B, whose entire
mechanism is whether a model obeys prose in its prompt, cannot be measured this
way and is not run without a real provider.
"""
from __future__ import annotations

import fnmatch
import random

from .tasks import Task


def script(task: Task, rng: random.Random, p_recall: float) -> tuple[list[dict], list[int]]:
    actions = list(task.primary)
    skipped: list[int] = []
    for i, comp in enumerate(task.companions):
        if rng.random() < p_recall:
            actions += comp["actions"]
        else:
            skipped.append(i)
            if i == 0 and task.shortcut:
                actions += task.shortcut          # the lazy way that looks right
    actions.append({"tool": "done"})
    return actions, skipped


def required_of(verdict) -> str:
    """The side of the rule the card says is missing."""
    rule = getattr(verdict, "rule", "")
    if "->" in rule:
        return rule.split("->", 1)[1].strip(" )")
    if "(" in rule:
        return rule.split("(", 1)[1].split(":")[0].strip(" )")
    return ""


def _satisfies(glob: str, companion: dict) -> bool:
    """Does this companion produce what the card asked for?

    A companion is not always a file write - the regenerate is a command - so it
    declares what it produces, which is what the agent reads off the card.
    """
    stem = glob.rstrip("*").rstrip("/")
    for made in companion.get("produces", []):
        m = made.rstrip("/")
        if not stem or m.startswith(stem) or stem.startswith(m) or fnmatch.fnmatch(made, glob):
            return True
    return False


def repair(task: Task, skipped: list[int], verdicts, comply: bool = True) -> list[dict]:
    """Told no, and told which directory. Do that companion, and nothing else."""
    if not comply:
        return []
    wanted: list[dict] = []
    for v in verdicts:
        glob = required_of(v)
        if not glob:
            continue
        for i in list(skipped):
            if _satisfies(glob, task.companions[i]):
                wanted += task.companions[i]["actions"]
                skipped.remove(i)
    return wanted
