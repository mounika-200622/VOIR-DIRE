"""The terminal is a design surface. Two colours, one box, no emoji."""
from __future__ import annotations

import os
import sys
import time

W = 74
VER, AMB, GRN, DIM, OFF, BOLD = "\033[38;5;203m", "\033[38;5;214m", "\033[38;5;114m", "\033[38;5;242m", "\033[0m", "\033[1m"


def _colour() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(s: str, code: str) -> str:
    return f"{code}{s}{OFF}" if _colour() else s


def _row(text: str, code: str = "", pad: int = 2) -> str:
    room = W - 2 - pad
    if len(text) > room:                       # a long line must not break the box
        text = text[:room - 3] + "..."
    body = " " * pad + text
    fill = " " * max(0, W - 2 - len(body))
    return f"{_c('|', VER)}{_c(body, code) if code else body}{fill}{_c('|', VER)}"


def halt_card(v, number: int | None = None, ward=None,
              touched: list[str] | None = None) -> str:
    n = number if number is not None else v.holding_id
    when = time.strftime("%d %b %Y", time.localtime(v.established)).upper()
    e = v.empanel or {}
    if e.get("tested"):
        receipt = (f"empanelled {e.get('fire','?')} fire  {e.get('false','?')} false"
                   f"    cited {v.cited}")
    elif e.get("taught"):
        # Authored by the person, not derived from anything. Saying "mined from
        # history" here would credit evidence that was never gathered.
        receipt = f"you wrote this rule    cited {v.cited}"
    elif e.get("mined"):
        receipt = f"mined from history, not empanelled    cited {v.cited}"
    else:
        receipt = f"not empanelled    cited {v.cited}"

    # A verdict tells the agent it is wrong. An instruction tells it what to do.
    step = []
    if ward is not None:
        try:
            from .nextstep import suggest
            hint = suggest(v, ward, touched or [])
        except Exception:
            hint = ""
        if hint:
            step = [_row(""), _row(f"DO THIS NEXT:  {hint}", AMB)]

    top = _c("+" + "-" * (W - 2) + "+", VER)
    sep = _c("+" + "-" * (W - 2) + "+", VER)
    return "\n".join([
        top,
        _row(f"HALT   BINDING PRECEDENT No {n}   ESTABLISHED {when}", VER),
        sep,
        _row(v.says, BOLD),
        _row(""),
        _row(v.rule, AMB),
        _row(v.reason, DIM),
        _row(""),
        _row(receipt, DIM),
    ] + step + [top])


def note_line(v) -> str:
    """Advisory. Said once, plainly, and it does not stop anything."""
    head = f"  {_c('note', AMB)}  {v.says}"
    body = f"        {_c(v.reason, DIM)}"
    return head + chr(10) + body


def clear_line() -> str:
    return _c("no binding precedent fires on this closure.", GRN)


def docket_line(h: dict, case: dict) -> str:
    stamp = {"binding": _c("BINDING  ", AMB), "persuasive": _c("advisory ", DIM),
             "overruled": _c("OVERRULED", VER), "retired": _c("retired  ", DIM)}.get(h["status"], h["status"])
    return f"  {_c('No ' + str(h['id']).rjust(3), DIM)}  {stamp}  {h['says'][:48]:<48} {_c(case.get('source',''), DIM)}"

def watch_halt(seat, touched) -> str:
    head = f"  {_c('HALT', VER)}  {seat.says}"
    why = f"        {_c(seat.reason, DIM)}"
    nxt = f"        {_c('do this next: ' + seat.next, AMB)}" if seat.next else ""
    return chr(10).join(x for x in (head, why, nxt) if x)


def watch_recovered(ids) -> str:
    which = ", ".join(f"No {i}" for i in ids)
    return f"  {_c('CLEARED', GRN)}  {which} satisfied. The change may land."


def watch_clear(touched) -> str:
    n = len(touched)
    what = touched[0] if n == 1 else f"{n} files"
    return f"  {_c('ok', GRN)}      {what} - nothing objects."
