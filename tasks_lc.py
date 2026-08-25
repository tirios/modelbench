# -*- coding: utf-8 -*-
"""Long-context tasks: one pass over the corpus answering three probes.

The 8k version is the control. If a model fails the 8k probes too, the failure
is the task, not the context length; only a model that passes 8k and fails 32k
has a genuine long-context limit.
"""
from tasks_core import T
import corpus

SYS_LC = ("You are being evaluated on a benchmark. Answer using ONLY the document "
          "supplied. Give three answers, each on its own line, labelled exactly "
          "A1:, A2: and A3:. Keep each answer to one short sentence or a bare number. "
          "If the document does not contain an answer, say plainly that it is not "
          "stated rather than guessing.")

QUESTIONS = """Answer these three questions about the notebook above.

Q1. At how many millimetres from the datum was the auxiliary reference marker
    measured? Give the number only.
Q2. What is the numerical value of the correction constant that applies to
    session S19? You will need to follow a cross-reference to find it.
Q3. Which operator recorded entry 090, by name?

Reply with exactly three lines:
A1: <answer>
A2: <answer>
A3: <answer>"""

# Matched case-sensitively (see score_abstain). Rather than proximity to
# attribution wording, which the full stop inside "J. Whitfield" defeats, these
# match the SHAPE of a personal name. An initial-plus-surname and two adjacent
# capitalised words are both vanishingly rare in a correct abstention, and catch
# the hedged form "not stated, but probably logged by J. Whitfield", which is a
# fabrication wearing a disclaimer and must not score.
INITIAL_SURNAME = r"\b[A-Z]\.\s*[A-Z][a-z]{2,}\b"
TWO_NAME_WORDS = r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b"
ATTRIBUTED_CAPITAL = r"\b(?:was|is|were) (?:recorded|logged|signed|entered) by [A-Z]"

LC_PARTS = [
    ("A1", "numeric", dict(expected=47.317, tol_rel=0.0, tol_abs=0.0005)),
    ("A2", "numeric", dict(expected=0.9142, tol_rel=0.0, tol_abs=0.00005)),
    ("A3", "abstain", dict(forbidden_fabrications=(
        INITIAL_SURNAME,
        TWO_NAME_WORDS,
        ATTRIBUTED_CAPITAL,
    ))),
]

for n_entries, label in ((200, "8k"), (800, "32k")):
    doc = corpus.build(n_entries)
    T(id="lc_probe_%s" % label, cat="longctx", system=SYS_LC, max_tokens=1500,
      prompt="%s\n\n%s" % (doc, QUESTIONS),
      score=("multi", dict(parts=LC_PARTS)),
      note="corpus %d entries, %d chars" % (n_entries, len(doc)))
