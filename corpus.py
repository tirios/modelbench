# -*- coding: utf-8 -*-
"""Deterministic synthetic long-context corpus with needles at known depths.

Entirely invented: no partner data, no facility detail, no real values. The
point is a haystack whose filler is varied enough not to be trivially
compressible, with three probes:
  N1  a single distinctive fact placed deep in the document
  N2  a two-hop lookup, pointer early and target late, so retrieval alone fails
  N3  a fact that is never stated, where the only correct answer is to say so
"""
import random

CONDITIONS = ["steady", "mildly unsteady", "settled", "drifting slightly", "stable"]
ACTIONS = [
    "the mounting torque was re-checked and left unchanged",
    "the operator logged a short pause before acquisition",
    "the reference channel was re-zeroed between repeats",
    "no adjustment was made to the rig between this entry and the last",
    "acquisition was restarted once after an early trigger",
    "the alignment jig was removed before the run began",
    "a spare cable was swapped in and the check repeated",
    "the ambient reading was noted but not acted on",
]
NOTES = [
    "Nothing further was recorded against this entry.",
    "The entry was reviewed the following morning and left as written.",
    "A follow-up was pencilled in but no follow-up entry exists.",
    "The margin carries a tick and no comment.",
    "This entry was transcribed from the paper log without change.",
]

N1_ENTRY = 118
N1_VALUE = "47.317"
N2_POINTER_ENTRY = 62
N2_TARGET_ENTRY = 173
N2_SESSION = "S19"
N2_VALUE = "0.9142"


def _sites(n):
    """Needle positions scale with corpus length so depth is constant."""
    return (max(2, round(0.59 * n)),      # N1 single fact
            max(1, round(0.31 * n)),      # N2 pointer
            max(3, round(0.86 * n)))      # N2 target


def build(n_entries=200, seed=5):
    rng = random.Random(seed)
    n1_at, n2p_at, n2t_at = _sites(n_entries)
    out = ["LABORATORY NOTEBOOK, TRANSCRIBED. Entries are in order and are not dated.",
           ""]
    for i in range(1, n_entries + 1):
        sess = "S%d" % (1 + (i * 7) % 40)
        parts = ["Entry %03d. Session %s. Conditions were %s and %s."
                 % (i, sess, rng.choice(CONDITIONS), rng.choice(ACTIONS))]
        if i == n1_at:
            parts.append("The auxiliary reference marker was measured at %s millimetres "
                         "from the datum." % N1_VALUE)
        if i == n2p_at:
            parts.append("The correction constant that applies to session %s is not "
                         "reproduced here; it is recorded in entry %03d."
                         % (N2_SESSION, n2t_at))
        if i == n2t_at:
            parts.append("The correction constant stored in this entry is %s. It is the "
                         "value referred to from the earlier cross-reference."
                         % N2_VALUE)
        parts.append(rng.choice(NOTES))
        out.append(" ".join(parts))
        out.append("")
    return "\n".join(out)


NEEDLES = {
    "n1": dict(question="At how many millimetres from the datum was the auxiliary "
                        "reference marker measured? Give the number only.",
               expected=47.317, kind="numeric"),
    "n2": dict(question="What is the numerical value of the correction constant that "
                        "applies to session %s? Give the number only. You will need to "
                        "follow a cross-reference to find it." % N2_SESSION,
               expected=0.9142, kind="numeric"),
    "n3": dict(question="Which operator recorded entry 090, by name?",
               expected=None, kind="abstain"),
}


if __name__ == "__main__":
    for n in (60, 200, 420):
        txt = build(n)
        print("%4d entries: %8d chars, ~%6d tokens (4 chars/token estimate)"
              % (n, len(txt), len(txt) // 4))
    t = build(200)
    for key in ("n1", "n2", "n3"):
        pass
    idx1 = t.find("auxiliary reference marker")
    idx2p = t.find("is recorded in entry")
    idx2t = t.find("correction constant stored in this entry")
    L = len(t)
    print("needle depths in the 200-entry corpus:")
    print("  N1 single fact      at %.0f%%" % (100.0 * idx1 / L))
    print("  N2 pointer          at %.0f%%" % (100.0 * idx2p / L))
    print("  N2 target           at %.0f%%" % (100.0 * idx2t / L))
    print("  N3 absent fact      never stated: 'operator' appears %d times"
          % t.count("operator"))
