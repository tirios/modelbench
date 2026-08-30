# -*- coding: utf-8 -*-
"""Hard coding tier, loaded from hard_tasks.json (authored + adversarially verified).

Kept in a data file rather than hand-written so the authoring pass is reproducible
and every task carries its own reference and mutant solution for the gate.
"""
import json
import os

from tasks_core import T, SYS_CODE

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "hard_tasks.json")

HARD = []

if os.path.exists(PATH):
    with open(PATH, encoding="utf-8") as f:
        _data = json.load(f)
    for _t in _data.get("tasks", []):
        HARD.append(_t)
        T(id=_t["id"], cat="hardcode", system=SYS_CODE, max_tokens=8000,
          prompt=_t["prompt"],
          # 240s: the complexity task deliberately runs a large input, and a model's
          # accidentally-quadratic answer must be allowed to time out rather than
          # kill the whole run.
          score=("pytest", dict(tests_src=_t["tests"], timeout=240)),
          note=_t.get("category", ""))


def reference(tid):
    for t in HARD:
        if t["id"] == tid:
            return "```python\n" + t["reference_solution"] + "\n```"
    return None


def mutant(tid):
    for t in HARD:
        if t["id"] == tid:
            return "```python\n" + t["mutant_solution"] + "\n```"
    return None
