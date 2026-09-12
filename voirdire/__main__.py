"""voir dire - ask before you allow.

    python -m voirdire learn  seeds/ward-demo        read what already went wrong
    python -m voirdire docket seeds/ward-demo        what it decided, and why
    python -m voirdire gate   seeds/ward-demo 11     would this closure be refused?
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import gate, history, learn, nextstep, templates
from .claim import Claim
from .db import Ledger, ledger_path


def _led(ward: Path) -> tuple[Ledger, str]:
    ward = Path(ward).resolve()
    return Ledger(ledger_path(ward)), str(ward)


def cmd_learn(a) -> int:
    led, scope = _led(a.ward)
    back = history.came_back(Path(a.ward))
    print(f"  {len(back)} closure(s) came back. Ruling on each.")
    filed = learn.learn_ward(led, Path(a.ward))
    if not filed:
        print("  nothing to learn: no closure here has come back yet.")
        led.close()
        return 0
    for f in filed:
        mark = "BINDING " if f["status"] == "binding" else "advisory"
        print(f"    {mark}  {f['rule']}")
        print(f"              {f['says']}")
        e = f["empanel"]
        print(f"              tested: {e.get('fire')} fired on its own case, "
              f"{e.get('false')} wrong on closures that held")
    c = led.counts(scope)
    print()
    print(f"  {c['binding']} can refuse a closure. {c['persuasive']} can only speak.")
    led.close()
    return 0


def cmd_docket(a) -> int:
    led, scope = _led(a.ward)
    rows = led.holdings(ward=scope)
    if not rows:
        print("  nothing on file. run: python -m voirdire learn " + str(a.ward))
        led.close()
        return 0
    for h in rows:
        mark = "BINDING " if h["status"] == "binding" else "advisory"
        print(f"  No {h['id']:<3} {mark}  {h['says']}")
        print(f"          {templates.render(h['template'], h['params'])}")
        e = h["empanel"] or {}
        if e.get("fire"):
            print(f"          receipt: {e['fire']} fire, {e['false']} false"
                  + (f", would have wrongly refused {e['false_ids']}" if e.get("false_ids") else ""))
    led.close()
    return 0


def cmd_gate(a) -> int:
    led, scope = _led(a.ward)
    evidence = json.loads(a.evidence) if a.evidence else []
    claim = Claim.proposed(Path(a.ward), a.complaint, evidence=evidence)
    refused = gate.on(led, Path(a.ward), claim)
    if not refused:
        print(f"  closure {a.complaint} may be filed.")
        led.close()
        return 0
    for v in refused:
        print()
        print(f"  REFUSED   BINDING RULE No {v.holding_id}")
        print(f"  {v.says}")
        print(f"  {v.rule}")
        print(f"  {v.reason}")
        step = nextstep.suggest(v.template, {}, claim) or ""
        # the rule's own parameters make the instruction specific
        for h in led.holdings(ward=scope):
            if h["id"] == v.holding_id:
                step = nextstep.suggest(v.template, h["params"], claim) or step
        if step:
            print(f"  DO THIS NEXT:  {step}")
    print()
    led.close()
    return 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="voirdire", description=__doc__)
    sub = p.add_subparsers(required=True)

    ln = sub.add_parser("learn", help="read what already went wrong in this ward")
    ln.add_argument("ward")
    ln.set_defaults(fn=cmd_learn)

    dk = sub.add_parser("docket", help="every rule on file, and its receipt")
    dk.add_argument("ward")
    dk.set_defaults(fn=cmd_docket)

    gt = sub.add_parser("gate", help="would this closure be refused?")
    gt.add_argument("ward")
    gt.add_argument("complaint", type=int)
    gt.add_argument("--evidence", default="", help="JSON list of evidence")
    gt.set_defaults(fn=cmd_gate)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
