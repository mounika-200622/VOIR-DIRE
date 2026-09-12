from pathlib import Path

import pytest

from voiddire.change import Change
from voiddire import templates


def ch(touched, added=None, tmp=Path(".")):
    return Change(repo=tmp, touched=touched, added=added or {})


def test_co_change_fires_when_the_pair_is_missing():
    c = ch(["models/patient.py"])
    assert templates.fires("co_change", {"trigger": "models/*.py", "required": "migrations/**"}, c)


def test_co_change_is_silent_when_the_pair_is_present():
    c = ch(["models/patient.py", "migrations/0042_add.py"])
    assert templates.fires("co_change", {"trigger": "models/*.py", "required": "migrations/**"}, c) is None


def test_co_change_is_silent_when_the_trigger_is_untouched():
    c = ch(["README.md"])
    assert templates.fires("co_change", {"trigger": "models/*.py", "required": "migrations/**"}, c) is None


def test_forbidden_edit():
    assert templates.fires("forbidden_edit", {"glob": "*.lock"}, ch(["poetry.lock"]))
    assert templates.fires("forbidden_edit", {"glob": "*.lock"}, ch(["app.py"])) is None


def test_must_not_appear_reads_added_lines_only():
    c = ch(["app.py"], {"app.py": ["import pdb; pdb.set_trace()"]})
    assert templates.fires("must_not_appear", {"regex": r"set_trace", "glob": "*.py"}, c)
    clean = ch(["app.py"], {"app.py": ["x = 1"]})
    assert templates.fires("must_not_appear", {"regex": r"set_trace", "glob": "*.py"}, clean) is None


def test_must_appear_reads_the_file(tmp_path):
    (tmp_path / "m.py").write_text("def down(): pass")
    c = ch(["m.py"], tmp=tmp_path)
    assert templates.fires("must_appear", {"regex": r"def down", "glob": "*.py"}, c) is None
    assert templates.fires("must_appear", {"regex": r"def up", "glob": "*.py"}, c)


def test_required_command_only_runs_when_the_glob_is_touched(tmp_path):
    c = Change(repo=tmp_path, touched=["src/a.py"])
    assert templates.fires("required_command", {"glob": "src/*.py", "cmd": "exit 1"}, c)
    idle = Change(repo=tmp_path, touched=["docs/x.md"])
    assert templates.fires("required_command", {"glob": "src/*.py", "cmd": "exit 1"}, idle) is None


def test_incomplete_params_never_fire():
    assert templates.fires("co_change", {"trigger": "models/*.py"}, ch(["models/a.py"])) is None
    assert not templates.valid("co_change", {"trigger": "x"})


def test_render_is_readable():
    assert templates.render("co_change", {"trigger": "a/*.py", "required": "b/**"}) == "co_change( a/*.py -> b/** )"


def test_must_run_separates_a_hand_edit_from_a_regeneration():
    """The two touch the same path. Only the command tells them apart."""
    p = {"glob": "client/*.py", "cmd": "tools/gen.py"}
    by_hand = Change(repo=Path("."), touched=["client/generated.py"], commands=[])
    assert templates.fires("must_run", p, by_hand)
    regenerated = Change(repo=Path("."), touched=["client/generated.py"],
                         commands=["python tools/gen.py"])
    assert templates.fires("must_run", p, regenerated) is None


def test_must_run_abstains_when_commands_are_invisible():
    """A bare git view cannot see commands. A gate that fires on missing
    evidence is a gate that fires on everything."""
    p = {"glob": "client/*.py", "cmd": "tools/gen.py"}
    unknown = Change(repo=Path("."), touched=["client/generated.py"], commands=None)
    assert templates.fires("must_run", p, unknown) is None
