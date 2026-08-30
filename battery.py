# -*- coding: utf-8 -*-
"""Assemble and score the battery. Import this, never edit task files here."""
import json
import scorers

import tasks_core          # noqa: F401  registers coding + reasoning
import tasks_extra         # noqa: F401  registers format + hallucination
import tasks_lc            # noqa: F401  registers long context
import tasks_hard          # noqa: F401  registers the hard coding tier
from tasks_core import TASKS

SCORERS = {
    "pytest": scorers.score_pytest,
    "numeric": scorers.score_numeric,
    "exact": scorers.score_exact,
    "json": scorers.score_json,
    "format": scorers.score_format,
    "abstain": scorers.score_abstain,
    "multi": scorers.score_multi,
}


def score_task(task, text):
    kind, kw = task["score"]
    return SCORERS[kind](text, **kw)


def content_score(task, text):
    """Lenient re-score that ignores the ANSWER:-marker requirement.

    Separates "got the wrong answer" from "got the right answer but disobeyed the
    output format". Haiku 4.5 answered reason_ci with a bare 'b' - correct content,
    missing marker - and conflating those two failures would misreport the model.
    Only affects numeric/exact tasks; every other scorer is returned unchanged.
    """
    kind, kw = task["score"]
    if kind in ("numeric", "exact"):
        return SCORERS[kind](text, **dict(kw, require_marker=False))
    return SCORERS[kind](text, **kw)


def summary():
    from collections import Counter
    c = Counter(t["cat"] for t in TASKS)
    return dict(c), len(TASKS)


if __name__ == "__main__":
    cats, n = summary()
    print("%d tasks: %s" % (n, cats))
    for t in TASKS:
        plen = len(t["prompt"])
        print("  %-22s %-14s prompt %7d chars  scorer %s"
              % (t["id"], t["cat"], plen, t["score"][0]))
