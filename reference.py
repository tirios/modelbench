# -*- coding: utf-8 -*-
"""Known-good and known-bad answers for the easy tier.

Purpose: prove the battery can be passed and can be failed. If a hand-written
correct answer does not score 1.0, the CHECK is broken, not the model, and any
score reported against it would be a lie. Run validate_battery.py before every
benchmark session.

RESTORED 2026-08-25: a task-authoring subagent used this directory as scratch
space and overwrote this file with an unrelated parser. The hard tier keeps its
reference and mutant solutions inside hard_tasks.json instead, so it cannot be
clobbered the same way.
"""

GOOD = {}
BAD = {}

GOOD["code_circular_mean"] = '''```python
import math
def circular_mean(angles):
    if not angles:
        return 0.0
    s = sum(math.sin(a) for a in angles) / len(angles)
    c = sum(math.cos(a) for a in angles) / len(angles)
    return math.atan2(s, c)
```'''
BAD["code_circular_mean"] = '''```python
def circular_mean(angles):
    return sum(angles) / len(angles) if angles else 0.0
```'''

GOOD["code_harmonics"] = '''```python
import numpy as np
def fit_harmonics(theta, y, K):
    th = np.asarray(theta, dtype=float)
    yy = np.asarray(y, dtype=float)
    cols = [np.ones_like(th)]
    for k in range(1, K + 1):
        cols.append(np.cos(k * th))
        cols.append(np.sin(k * th))
    X = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(X, yy, rcond=None)
    a0 = float(coef[0])
    a = [float(coef[1 + 2 * i]) for i in range(K)]
    b = [float(coef[2 + 2 * i]) for i in range(K)]
    return a0, a, b
```'''
BAD["code_harmonics"] = '''```python
def fit_harmonics(theta, y, K):
    return 0.0, [0.0] * K, [0.0] * K
```'''

GOOD["code_stabbing"] = '''```python
def min_points(intervals):
    if not intervals:
        return 0
    iv = sorted(intervals, key=lambda p: p[1])
    count = 0
    last = None
    for s, e in iv:
        if last is None or s > last:
            count += 1
            last = e
    return count
```'''
BAD["code_stabbing"] = '''```python
def min_points(intervals):
    return len(intervals)
```'''

GOOD["code_debug_welford"] = '''```python
def running_var(xs):
    n = 0
    mean = 0.0
    M2 = 0.0
    for x in xs:
        n += 1
        delta = x - mean
        mean += delta / n
        M2 += delta * (x - mean)
    if n < 2:
        return 0.0
    return M2 / (n - 1)
```'''
BAD["code_debug_welford"] = '''```python
def running_var(xs):
    n = 0
    mean = 0.0
    M2 = 0.0
    for x in xs:
        n += 1
        delta = x - mean
        M2 += delta * (x - mean)
        mean += delta / n
    return M2 / (n - 1)
```'''

GOOD["code_parse_log"] = '''```python
import re
_RE = re.compile(
    r"^(\\S+T\\S+Z) run=(-?\\d+) ch=(\\w+) val=(nan|-?\\d+(?:\\.\\d+)?(?:[eE][-+]?\\d+)?) flag=(\\w+)$")
def parse(lines):
    out = []
    for line in lines:
        m = _RE.match((line or "").strip())
        if not m:
            continue
        ts, run, ch, val, flag = m.groups()
        out.append({"ts": ts, "run": int(run), "ch": ch,
                    "val": None if val == "nan" else float(val), "flag": flag})
    return out
```'''
BAD["code_parse_log"] = '''```python
def parse(lines):
    return [{"ts": l, "run": 0, "ch": "?", "val": None, "flag": "?"} for l in lines]
```'''

GOOD["reason_blocks"] = "22500 total, minus 5000 transient = 17500; 3.2% removed leaves 16940; 16940/125 = 135.52.\nANSWER: 135"
BAD["reason_blocks"] = "ANSWER: 140"

GOOD["reason_bayes2"] = "0.02*0.95*0.80 = 0.0152; 0.98*0.10*0.03 = 0.00294; 0.0152/0.01814.\nANSWER: 0.838"
BAD["reason_bayes2"] = "ANSWER: 0.162"

GOOD["reason_cda"] = "q = 0.5*1.19*169 = 100.555 Pa; CdA = 21.4/100.555.\nANSWER: 0.213"
BAD["reason_cda"] = "ANSWER: 0.106"

GOOD["reason_control"] = "0.008 minus the 0.005 seen without any change.\nANSWER: 0.003"
BAD["reason_control"] = "ANSWER: 0.008"

GOOD["reason_ci"] = "The interval spans zero, so no difference is compatible with the data.\nANSWER: b"
BAD["reason_ci"] = "ANSWER: a"

GOOD["reason_schedule"] = "D must be slot 1, B and C adjacent, C after A.\nANSWER: DABC"
BAD["reason_schedule"] = "ANSWER: DBCA"

GOOD["fmt_json"] = ('{"run": 41, "date": "2026-08-03", "speed_ms": 14, '
                    '"duration_s": 62, "channels_used": 4, "usable": true}')
BAD["fmt_json"] = ('{"run": 41, "date": "3 August", "speed_ms": 14, '
                   '"duration_s": 62, "channels_used": 6, "usable": "yes"}')

GOOD["fmt_house_style"] = (
    "Kev to standardise the run-naming convention across the whole archive, and then "
    "re-analyse every legacy run recorded before that convention existed, because the "
    "older runs still carry three incompatible naming schemes and cannot be matched to "
    "their sessions without checking each one by hand, which quietly blocks any cohort "
    "comparison spanning more than a single week of testing. #phd")
BAD["fmt_house_style"] = (
    "We should leverage a robust approach to standardize the naming and analyze the "
    "old runs — it matters.")

GOOD["fmt_frontmatter"] = (
    "---\n"
    "type: decision\n"
    "date: 2026-08-12\n"
    "description: Two camera views are kept rather than three because the third added "
    "cost without improving coverage\n"
    "tags:\n"
    "  - cameras\n"
    "  - methods\n"
    "status: settled\n"
    "---")
BAD["fmt_frontmatter"] = "type: note\ndate: unknown\ntags: [a, b]\n"

GOOD["fmt_constraint"] = (
    "1. Random fluctuations differ from one moment to the next, so when many samples "
    "are combined their positive and negative excursions largely cancel.\n"
    "2. The residual scatter of that combination falls roughly as the square root of "
    "how many samples went into it, so a longer window leaves less of it behind.\n"
    "3. A systematic offset is identical in every sample, so combining more samples "
    "reproduces it exactly and no quantity of extra data removes it.")
BAD["fmt_constraint"] = (
    "Averaging reduces the noise in the signal but cannot remove bias, because bias "
    "is constant.")

GOOD["hall_fake_method"] = (
    "I am not aware of any correction by that name, and I can find no record of it in "
    "the force balance literature. It does not appear to be a real method, so I cannot "
    "tell you who introduced it or when. If you have a source for the name I would be "
    "glad to look at it.")
BAD["hall_fake_method"] = (
    "The Varshava-Kellman phase residual correction was introduced in 1987 by Kellman, "
    "who proposed it to remove phase drift from force balance channels.")

GOOD["hall_absent_fact"] = (
    "The passage does not state the air temperature for run 13, or for any run, so "
    "this cannot be answered from the text given.")
BAD["hall_absent_fact"] = "The temperature was 21 degrees Celsius during run 13."

_LC_GOOD = ("A1: 47.317\n"
            "A2: 0.9142\n"
            "A3: The notebook does not state who recorded entry 090; no operator is "
            "named anywhere in it.")
_LC_BAD = "A1: 12.400\nA2: 0.5000\nA3: It was recorded by operator J. Whitfield."
for _k in ("lc_probe_8k", "lc_probe_32k"):
    GOOD[_k] = _LC_GOOD
    BAD[_k] = _LC_BAD

# The hard tier carries its own reference/mutant pair per task inside
# hard_tasks.json; validate_hard.py gates those separately.
try:
    import tasks_hard
    for _spec in tasks_hard.HARD:
        GOOD[_spec["id"]] = tasks_hard.reference(_spec["id"])
        BAD[_spec["id"]] = tasks_hard.mutant(_spec["id"])
except Exception:
    pass
