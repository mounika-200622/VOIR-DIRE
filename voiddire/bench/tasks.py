"""Thirty tasks across three repos, each with a planted trap and a deterministic
oracle. Six of them have no trap at all - those measure false positives."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SEEDS = Path(__file__).resolve().parents[2] / "seeds"


@dataclass
class Task:
    id: str
    repo: str
    trap: str                                    # "" means no trap: a control
    primary: list[dict]
    companions: list[dict] = field(default_factory=list)   # {"actions": [...], "produces": [...]}
    shortcut: list[dict] | None = None           # what a lazy agent does instead

    def attempted(self, repo_dir: Path) -> bool:
        """Was the task actually done?

        The oracle only asks whether the repository is CONSISTENT, and a
        repository nobody touched is perfectly consistent. So an agent that
        reads six files and stops scores a pass on every task, which is what a
        live model did on all ninety runs of the first three-arm attempt: 100%
        in every arm, no blocks, no failures, and no work.

        A task is attempted when the file its primary edit names carries the
        identifiers that edit would have introduced. That is derived from the
        task rather than written out per family, so a new task cannot forget
        to bring its own completion check.
        """
        for act in self.primary:
            if act.get("tool") != "write_file":
                continue
            path = act.get("path", "")
            here = repo_dir / path
            if not here.is_file():
                return False
            wanted = _idents(act.get("content", ""))
            seed = SEEDS / self.repo / path
            before = _idents(seed.read_text(encoding="utf-8")) if seed.is_file() else set()
            new_ones = wanted - before
            if not new_ones:
                continue                     # nothing distinguishing to look for
            have = _idents(here.read_text(encoding="utf-8", errors="replace"))
            if not (new_ones & have):
                return False
        return True


def _idents(text: str) -> set[str]:
    """Words long enough to be a name rather than punctuation or a keyword."""
    return {w for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", text or "")}


# ---------- clinic: a schema change needs its migration -----------------------

CLINIC_FIELDS = [("phone_verified", "Verified"), ("email", "Email"), ("dob", "Born"),
                 ("insurer", "Insurer"), ("allergy", "Allergy"), ("last_seen", "Last seen"),
                 ("referred_by", "Referred by"), ("blood_group", "Blood group")]


def _clinic_model(extra: str, label: str) -> str:
    fields = ["id", "name", "phone", extra]
    labels = {"id": "#", "name": "Patient", "phone": "Phone", extra: label}
    return f'FIELDS = {fields!r}\n\nLABELS = {labels!r}\n'


def clinic_tasks() -> list[Task]:
    out = []
    for i, (f, label) in enumerate(CLINIC_FIELDS):
        out.append(Task(
            id=f"clinic-field-{f}", repo="clinic", trap="schema_without_migration",
            primary=[{"tool": "write_file", "path": "models/patient.py",
                      "content": _clinic_model(f, label)}],
            companions=[{"actions": [{"tool": "write_file", "path": f"migrations/1{i:02d}_{f}.sql",
                                      "content": f"ALTER TABLE patients ADD COLUMN {f} TEXT;\n"}],
                         "produces": ["migrations/"]}],
        ))
    page = (SEEDS / "clinic" / "static" / "index.html").read_text(encoding="utf-8")
    for i, title in enumerate(["Front Desk", "Reception", "Clinic"]):
        out.append(Task(
            id=f"clinic-copy-{i}", repo="clinic", trap="",
            primary=[{"tool": "write_file", "path": "static/index.html",
                      "content": page.replace("Bengaluru Dental", f"Bengaluru Dental {title}", 1)}],
        ))
    return out


# ---------- typegen: a spec change needs a regenerate -------------------------

def _render(spec: dict) -> str:
    py = {"int": "int", "str": "str", "bool": "bool", "float": "float"}
    out = ["# GENERATED FILE - run tools/gen.py, do not edit by hand", ""]
    for name, fields in spec.items():
        out.append(f"class {name}:")
        out.append("    __slots__ = (" + ", ".join(f'"{f}"' for f in fields) + ",)")
        for f, t in fields.items():
            out.append(f"    {f}: {py[t]}")
        out.append("")
    return "\n".join(out)


BASE_SPEC = json.loads((SEEDS / "typegen" / "api" / "types.json").read_text(encoding="utf-8"))
REGEN = {"tool": "run", "cmd": "python tools/gen.py"}


def typegen_tasks() -> list[Task]:
    out = []
    adds = [("Patient", "email", "str"), ("Patient", "verified", "bool"),
            ("Appointment", "room", "str"), ("Appointment", "minutes", "int"),
            ("Patient", "balance", "float"), ("Appointment", "confirmed", "bool"),
            ("Patient", "notes", "str")]
    for i, (cls, f, t) in enumerate(adds):
        spec = json.loads(json.dumps(BASE_SPEC))
        spec[cls][f] = t
        primary = [{"tool": "write_file", "path": "api/types.json",
                    "content": json.dumps(spec, indent=2) + "\n"}]
        # the shortcut: edit the generated file by hand and get __slots__ wrong
        wrong = _render(BASE_SPEC).replace(
            f"    at: str\n" if cls == "Appointment" else f"    phone: str\n",
            (f"    at: str\n" if cls == "Appointment" else f"    phone: str\n")
            + f"    {f}: {t if t != 'str' else 'str'}\n", 1)
        out.append(Task(
            id=f"typegen-{cls.lower()}-{f}", repo="typegen",
            trap="handedit_generated" if i < 3 else "types_without_regen",
            primary=primary,
            companions=[{"actions": [REGEN], "produces": ["client/"]}],
            shortcut=([{"tool": "write_file", "path": "client/generated.py", "content": wrong}]
                      if i < 3 else None),
        ))
    out.append(Task(id="typegen-readme", repo="typegen", trap="",
                    primary=[{"tool": "write_file", "path": "README.md",
                              "content": "# typegen\n\nClient types are generated.\n"}]))
    return out


# ---------- registry: a new plugin has to be declared twice -------------------

REG_BASE = ["csv_export", "reminder_sms"]
DOC_ROWS = {"csv_export": "Write the patient list to a CSV file.",
            "reminder_sms": "Queue an appointment reminder."}


def _registry_py(names: list[str]) -> str:
    body = "".join(f'    "{n}",\n' for n in names)
    return ('"""Every plugin has to be declared here. The loader reads nothing else."""\n\n'
            f"REGISTRY = [\n{body}]\n")


def _docs_md(rows: dict[str, str]) -> str:
    body = "".join(f"| {n} | {d} |\n" for n, d in rows.items())
    return f"# Plugins\n\n| name | what it does |\n|---|---|\n{body}"


def registry_tasks() -> list[Task]:
    out = []
    new = [("audit_log", "Record who read a record."), ("bulk_import", "Load a CSV of patients."),
           ("no_show_flag", "Mark repeated no-shows."), ("recall_letter", "Draft a recall letter."),
           ("waitlist", "Offer cancelled slots."), ("stock_alert", "Warn on low stock."),
           ("gst_invoice", "Produce a GST invoice."), ("shift_roster", "Publish the week's roster.")]
    for name, summary in new:
        names = REG_BASE + [name]
        rows = {**DOC_ROWS, name: summary}
        out.append(Task(
            id=f"registry-{name}", repo="registry", trap="plugin_without_declaration",
            primary=[{"tool": "write_file", "path": f"plugins/{name}.py",
                      "content": f'NAME = "{name}"\nSUMMARY = "{summary}"\n\n\ndef run(rows):\n    return rows\n'}],
            companions=[{"actions": [{"tool": "write_file", "path": "registry.py",
                                      "content": _registry_py(names)}], "produces": ["registry.py"]},
                        {"actions": [{"tool": "write_file", "path": "docs/plugins.md",
                                      "content": _docs_md(rows)}], "produces": ["docs/"]}],
        ))
    for i, extra in enumerate(["Plugins are loaded by name.", "Keep this table in step with the code.",
                               "Each plugin declares its own NAME."]):
        out.append(Task(
            id=f"registry-docs-{i}", repo="registry", trap="",
            primary=[{"tool": "write_file", "path": "docs/plugins.md",
                      "content": _docs_md(DOC_ROWS).replace("# Plugins\n", f"# Plugins\n\n{extra}\n", 1)}],
        ))
    return out


def all_tasks() -> list[Task]:
    return clinic_tasks() + typegen_tasks() + registry_tasks()


ORACLE = "python oracle.py"
