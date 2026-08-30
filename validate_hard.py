# -*- coding: utf-8 -*-
"""Gate the hard coding tier before it scores anything.

A task counts only if its reference solution scores 1.00 and its near-miss mutant
scores below 0.50. A task whose reference fails is a broken CHECK, not a hard task,
and would silently penalise every model. A task whose mutant passes cannot
discriminate and is dead weight. Rejected tasks are written out so they can be
repaired rather than quietly dropped.
"""
import json
import os

import tasks_hard
from battery import score_task, TASKS

HARD_IDS = {t["id"] for t in tasks_hard.HARD}
BY_ID = {t["id"]: t for t in TASKS if t["id"] in HARD_IDS}

good, broken, blunt = [], [], []

print(f"{'task':<20}{'ref':>6}{'mutant':>8}   verdict")
print("-" * 82)
for spec in tasks_hard.HARD:
    tid = spec["id"]
    task = BY_ID.get(tid)
    if task is None:
        broken.append((tid, "not registered"))
        print(f"{tid:<20}{'-':>6}{'-':>8}   NOT REGISTERED")
        continue
    rs, rd = score_task(task, tasks_hard.reference(tid))
    ms, md = score_task(task, tasks_hard.mutant(tid))
    if rs < 1.0:
        verdict = f"BROKEN: reference scores {rs:.2f} -> {rd[:44]}"
        broken.append((tid, rd))
    elif ms >= 0.5:
        verdict = f"BLUNT: mutant scores {ms:.2f}, cannot discriminate"
        blunt.append((tid, ms))
    else:
        verdict = f"ok (gap {rs - ms:.2f})"
        good.append(tid)
    print(f"{tid:<20}{rs:>6.2f}{ms:>8.2f}   {verdict}")

print()
print(f"usable: {len(good)}   broken: {len(broken)}   blunt: {len(blunt)}")
if good:
    print("usable tasks:", ", ".join(good))
if broken:
    print("\nBROKEN (reference does not pass its own tests):")
    for tid, d in broken:
        print(f"   {tid}: {d[:120]}")
if blunt:
    print("\nBLUNT (mutant survives, no discriminating power):")
    for tid, m in blunt:
        print(f"   {tid}: mutant {m:.2f}")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hard_gate.json"),
          "w", encoding="utf-8") as f:
    json.dump({"usable": good,
               "broken": [t for t, _ in broken],
               "blunt": [t for t, _ in blunt]}, f, indent=1)
