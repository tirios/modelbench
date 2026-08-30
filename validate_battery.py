"""Prove the battery can be passed and can be failed.

A task is BROKEN if a hand-written correct answer scores below 1.0: the check is
wrong, not the model. A task is UNDISCRIMINATING if a deliberately wrong answer
still scores 0.8 or more. Scores between are partial credit, which is legitimate
for rubric-style checks and is reported so it is never mistaken for a pass.
"""
from battery import TASKS, score_task
from reference import GOOD, BAD

broken, blunt, partial = [], [], []
print(f"{'task':<22} {'correct':>8} {'wrong':>7}   note")
print("-" * 76)
for t in TASKS:
    tid = t["id"]
    g, gd = score_task(t, GOOD[tid])
    b, bd = score_task(t, BAD[tid])
    if g < 1.0:
        note = "BROKEN: correct answer scores %.2f -> %s" % (g, gd[:44]); broken.append(tid)
    elif b >= 0.8:
        note = "UNDISCRIMINATING: wrong answer scores %.2f" % b; blunt.append(tid)
    elif b > 0.0:
        note = "ok (partial credit: wrong answer keeps %.2f)" % b; partial.append((tid, b))
    else:
        note = "ok (clean zero on wrong answer)"
    print(f"{tid:<22} {g:>8.2f} {b:>7.2f}   {note}")
print()
if broken:
    raise SystemExit("BROKEN CHECKS: %s" % broken)
if blunt:
    raise SystemExit("UNDISCRIMINATING CHECKS: %s" % blunt)
print("Every task: correct answer scores 1.00, wrong answer scores below 0.80.")
if partial:
    print("Partial-credit tasks (a wrong answer still earns something, by design):")
    for tid, b in partial:
        print("   %-22s %.2f" % (tid, b))
