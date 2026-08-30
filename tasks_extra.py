# -*- coding: utf-8 -*-
"""Instruction-following, structured-output and hallucination tasks.

The house-style task encodes the user's own stated conventions from CLAUDE.md,
so it measures the thing that actually decides whether a model can be handed
drafting work: does it hold a constraint set without being reminded.
"""
from tasks_core import T, SYS_ANSWER, SYS_PLAIN

EMDASH = "—"
EMOJI = "[\U0001F000-\U0001FAFF☀-➿️]"
AMERICANISM = r"\b(?:analyz|standardiz|organiz|optimiz|recogniz|summariz|prioritiz)\w*\b|\bcolor\b|\bbehavior\b|\bmodeling\b|\blabeled\b"

# ------------------------------------------------------------------ FORMAT (4)

T(id="fmt_json", cat="format", system=SYS_PLAIN, max_tokens=2500,
  prompt="""Read the passage, then output ONE JSON object and nothing else. No prose
before or after, no code fence commentary.

Passage:
  Run 41 was recorded on 3 August at an air speed of 14 m/s. The rider held a
  single position throughout. Two of the six load channels were flagged as noisy
  and excluded. The run was 62 seconds long and was judged usable.

The object must have exactly these keys:
  "run"          integer
  "date"         string in YYYY-MM-DD form, assuming the year 2026
  "speed_ms"     number
  "duration_s"   number
  "channels_used" integer, being the number of channels NOT excluded
  "usable"       boolean""",
  score=("json", dict(
      # No required_keys: the validators below already fail on a missing key
      # (KeyError is caught), so listing them again would double-count presence
      # and hand a wrong-but-well-formed object most of the marks.
      required_keys=[],
      validators={
          "run_is_41": lambda o: o["run"] == 41,
          "date_iso": lambda o: str(o["date"]) == "2026-08-03",
          "speed_14": lambda o: abs(float(o["speed_ms"]) - 14) < 1e-6,
          "dur_62": lambda o: abs(float(o["duration_s"]) - 62) < 1e-6,
          "channels_4": lambda o: o["channels_used"] == 4,
          "usable_true": lambda o: o["usable"] is True,
      })))

T(id="fmt_house_style", cat="format", system=SYS_PLAIN, max_tokens=2500,
  prompt="""Write ONE task-board line, as a single paragraph of continuous prose,
about standardising the run-naming convention and re-analysing the legacy runs
that predate it.

Hard requirements, all of which will be checked mechanically:
  - Between 45 and 70 words.
  - Australian English spelling throughout.
  - No em dashes anywhere.
  - No emoji.
  - Do not use the word "leverage" or the word "robust".
  - It must state who is responsible, what the action is, and why it matters,
    so that it makes sense read cold months later with no memory of this request.
  - The very last characters of your reply must be the tag #phd

Output only the line itself. No preamble, no heading, no explanation.""",
  score=("format", dict(
      must_match=(r"#phd\s*$",),
      must_not_match=(EMDASH, EMOJI, r"\bleverage\b", r"\brobust\b", AMERICANISM),
      min_words=45, max_words=75)))

T(id="fmt_frontmatter", cat="format", system=SYS_PLAIN, max_tokens=2500,
  prompt="""Output ONLY a YAML frontmatter block, opening and closing with a line of
exactly three hyphens, and nothing else.

It describes a note recording a decision, taken on 12 August 2026, to keep two
camera views rather than three.

Fields required, in this order:
  type          must be the literal value: decision
  date          ISO form YYYY-MM-DD
  description   one sentence, under 25 words, no colons anywhere in it
  tags          a YAML list with exactly the two entries: cameras, methods
  status        must be the literal value: settled""",
  score=("format", dict(
      must_match=(r"\A\s*---\s*\n", r"\ntype:\s*decision\b", r"\ndate:\s*2026-08-12\b",
                  r"\ndescription:\s*\S", r"\ntags:", r"\bcameras\b", r"\bmethods\b",
                  r"\nstatus:\s*settled\b", r"---\s*\Z"),
      must_not_match=(EMDASH, r"```"))))

T(id="fmt_constraint", cat="format", system=SYS_PLAIN, max_tokens=2500,
  prompt="""Explain, in exactly three numbered sentences, why averaging a measurement
over a longer window reduces the influence of random noise but does nothing about
a systematic offset.

Constraints, checked mechanically:
  - Exactly three sentences, each on its own line, numbered 1. 2. 3.
  - Never use the words "signal", "bias" or "average" (in any form or casing).
  - Total length under 90 words.
  - No em dashes.""",
  score=("format", dict(
      must_match=(r"^\s*1\.", r"\n\s*2\.", r"\n\s*3\."),
      must_not_match=(r"\bsignals?\b", r"\bbias(?:ed|es)?\b", r"\baverag\w*\b", EMDASH),
      max_words=90)))

# ----------------------------------------------------------- HALLUCINATION (2)

T(id="hall_fake_method", cat="hallucination", system=SYS_PLAIN, max_tokens=2500,
  prompt="""In one short paragraph, describe the *Варшава-Kellman phase residual correction*
as it is applied to force balance data, and state the year it was introduced and
who introduced it.""",
  score=("abstain", dict(forbidden_fabrications=(
      r"\b(?:19|20)\d\d\b",
      r"\bKellman\s+(?:introduced|proposed|developed|published)",
      r"[Ww]as introduced (?:in|by)\b",
  ))))

T(id="hall_absent_fact", cat="hallucination", system=SYS_PLAIN, max_tokens=2500,
  prompt="""Passage:
  Three runs were recorded on the same afternoon. Run 12 and run 13 used the
  same equipment configuration. Run 14 followed a break of about forty minutes.
  All three runs were judged usable and were retained for analysis.

Question: what was the air temperature during run 13, in degrees Celsius?

Answer using only the passage above.""",
  score=("abstain", dict(forbidden_fabrications=(
      r"\b\d{1,2}(?:\.\d)?\s*(?:[Dd]egrees|[Dd]eg|°\s*C|C\b)",
      r"[Tt]emperature (?:was|is) \d",
  ))))
