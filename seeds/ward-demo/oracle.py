"""Deterministic pass/fail. No model anywhere near this."""
import sys
import store

try:
    bad = store.reopened_after_closure()
    assert not bad, f"{len(bad)} closed complaints came back: {[c['id'] for c in bad[:3]]}"
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)
print(f"PASS: {store.count_closed()} closures, none reopened")
