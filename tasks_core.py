# -*- coding: utf-8 -*-
"""Task battery: coding, reasoning, format, hallucination.

Every expected value in this file was computed, not asserted. No partner data
appears anywhere: all numbers are invented or synthetic and the domain flavour
is methodology only, which CLAUDE.md permits discussing freely.
"""
import math

SYS_ANSWER = (
    "You are being evaluated on a benchmark. Work the problem, then end your reply "
    "with a single final line of the form 'ANSWER: <value>' and write nothing after it."
)
SYS_CODE = (
    "You are being evaluated on a benchmark. Return the complete solution as ONE fenced "
    "Python code block. Define exactly the requested function at module level. Do not "
    "include tests, example usage, or a __main__ block."
)
SYS_PLAIN = "You are being evaluated on a benchmark. Follow the instructions exactly."

TASKS = []


def T(**kw):
    TASKS.append(kw)
    return kw


# ------------------------------------------------------------------ CODING (5)

CIRC_TESTS = r"""
import math
def close(a, b, tol=1e-9):
    d = (a - b + math.pi) % (2*math.pi) - math.pi
    return abs(d) <= tol
def mk(name, fn):
    check(name, fn)
def t1():
    g = circular_mean([0.1, -0.1])
    if not close(g, 0.0): raise AssertionError('got %r want 0.0' % g)
def t2():
    g = circular_mean([3.0, -2.9])
    if not close(g, -3.0915926536, 1e-8): raise AssertionError('got %r want -3.0915926536' % g)
def t3():
    g = circular_mean([0.0, math.pi/2])
    if not close(g, 0.7853981634, 1e-8): raise AssertionError('got %r want 0.7853981634' % g)
def t4():
    g = circular_mean([1.0, 1.0, 1.0])
    if not close(g, 1.0): raise AssertionError('got %r want 1.0' % g)
def t5():
    g = circular_mean([-3.0, 3.0])
    if abs(abs(g) - math.pi) > 1e-6: raise AssertionError('got %r want +/-pi' % g)
def t6():
    for a in [-3.0, -1.0, 0.0, 2.0, 3.1]:
        g = circular_mean([a, a + 0.3])
        if not (-math.pi < g <= math.pi + 1e-12): raise AssertionError('out of range: %r' % g)
def t7():
    g = circular_mean([])
    if g != 0.0: raise AssertionError('empty got %r' % g)
mk('wrap_free', t1); mk('wraps_pi', t2); mk('quarter', t3); mk('identical', t4)
mk('antipodal', t5); mk('in_range', t6); mk('empty', t7)
"""

T(id="code_circular_mean", cat="code", system=SYS_CODE, max_tokens=3000,
  prompt="""Write a Python function `circular_mean(angles)`.

`angles` is a list of angles in radians. Return their circular (directional) mean:
the angle of the resultant vector formed by averaging the unit vectors, that is
atan2(mean of the sines, mean of the cosines). The result must lie in the range
(-pi, pi]. Use only the Python standard library. Return 0.0 for an empty list.""",
  score=("pytest", dict(tests_src=CIRC_TESTS)))


HARM_TESTS = r"""
import numpy as np
th = np.linspace(0, 2*np.pi, 256, endpoint=False)
A0, A, B = 0.4, [1.2, -0.5, 0.25], [0.8, 0.33, -0.6]
y = A0 + sum(A[k]*np.cos((k+1)*th) + B[k]*np.sin((k+1)*th) for k in range(3))
r = fit_harmonics(list(th), list(y), 3)
def t_shape():
    if not (len(r) == 3 and len(r[1]) == 3 and len(r[2]) == 3):
        raise AssertionError('shape %r' % (r,))
def t_a0():
    if abs(float(r[0]) - A0) > 1e-6: raise AssertionError('a0 %r' % (r[0],))
def t_a():
    if any(abs(float(r[1][k]) - A[k]) > 1e-6 for k in range(3)):
        raise AssertionError('a %r want %r' % (list(r[1]), A))
def t_b():
    if any(abs(float(r[2][k]) - B[k]) > 1e-6 for k in range(3)):
        raise AssertionError('b %r want %r' % (list(r[2]), B))
def t_k1():
    th2 = np.linspace(0, 2*np.pi, 64, endpoint=False)
    y2 = 2.0 + 3.0*np.cos(th2) - 1.5*np.sin(th2)
    q = fit_harmonics(list(th2), list(y2), 1)
    if not (abs(float(q[0])-2.0) < 1e-6 and abs(float(q[1][0])-3.0) < 1e-6
            and abs(float(q[2][0])+1.5) < 1e-6):
        raise AssertionError('K1 %r' % (q,))
check('shape', t_shape); check('a0', t_a0); check('a_coef', t_a)
check('b_coef', t_b); check('K1', t_k1)
"""

T(id="code_harmonics", cat="code", system=SYS_CODE, max_tokens=3000,
  prompt="""Write a Python function `fit_harmonics(theta, y, K)`.

Fit, by ordinary least squares, the model

    y ~= a0 + sum over k = 1..K of [ a_k * cos(k*theta) + b_k * sin(k*theta) ]

to the samples (theta, y). `theta` is in radians.

Return a tuple `(a0, a_list, b_list)` where `a0` is a float and `a_list` and
`b_list` are lists of length K holding a_1..a_K and b_1..b_K in order.
numpy is available and may be used.""",
  score=("pytest", dict(setup="import numpy as np", tests_src=HARM_TESTS)))


STAB_TESTS = r"""
cases = [
    ([(1,3),(2,5),(4,6)], 2),
    ([(1,2),(3,4),(5,6)], 3),
    ([(1,10),(2,3),(4,5)], 2),
    ([], 0),
    ([(1,1)], 1),
    ([(1,5),(1,5)], 1),
    ([(1,4),(2,3),(3,6),(5,7),(8,9)], 3),
    ([(4,6),(1,3),(2,5)], 2),
]
def mkcase(inp, want, i):
    def run():
        got = min_points(list(inp))
        if got != want:
            raise AssertionError('case%d %r got %r want %r' % (i, inp, got, want))
    return run
for i, (inp, want) in enumerate(cases):
    check('case%d' % i, mkcase(inp, want, i))
"""

T(id="code_stabbing", cat="code", system=SYS_CODE, max_tokens=3000,
  prompt="""Write a Python function `min_points(intervals)`.

`intervals` is a list of `(start, end)` tuples denoting CLOSED intervals with
start <= end. Return the minimum number of points on the real line such that
every interval contains at least one of those points. Return 0 for an empty list.""",
  score=("pytest", dict(tests_src=STAB_TESTS)))


WELFORD_TESTS = r"""
import statistics, random
random.seed(11)
sets = [[1,2,3,4,5], [10.0,10.0,10.0], [2.5,-3.5,7.25,0.0,1.125,99.5],
        [random.gauss(100,5) for _ in range(500)], [1e6+1, 1e6+2, 1e6+3]]
def mkset(s, i):
    def run():
        got = running_var(list(s)); want = statistics.variance(s)
        if abs(got - want) > max(1e-9, abs(want)*1e-9):
            raise AssertionError('set%d got %r want %r' % (i, got, want))
    return run
for i, s in enumerate(sets):
    check('set%d' % i, mkset(s, i))
def t_single():
    if running_var([4.0]) != 0.0: raise AssertionError('single')
def t_empty():
    if running_var([]) != 0.0: raise AssertionError('empty')
check('single', t_single); check('empty', t_empty)
"""

T(id="code_debug_welford", cat="code", system=SYS_CODE, max_tokens=3000,
  prompt="""The function below is meant to compute the SAMPLE variance (dividing by n-1)
of a sequence in a single pass using Welford's algorithm. It returns wrong values.

```python
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
```

Return a corrected version of `running_var` with the same name and signature.
It must return the sample variance, and must return 0.0 when the input has
fewer than two elements.""",
  score=("pytest", dict(setup="import statistics", tests_src=WELFORD_TESTS)))


PARSE_TESTS = r"""
LINES = [
 "2026-08-01T09:14:22Z run=17 ch=fx val=-12.4 flag=ok",
 "2026-08-01T09:14:22Z run=17 ch=fy val=3.1 flag=ok",
 "BAD LINE - ignore me",
 "",
 "2026-08-01T09:14:23Z run=18 ch=fx val=nan flag=drop",
 "2026-08-01T09:14:24Z run=9 ch=mz val=0.0 flag=ok",
 "2026-08-01T09:14:25Z run=x ch=fx val=1.0 flag=ok",
]
out = parse(list(LINES))
def t_count():
    if len(out) != 4: raise AssertionError('len %d: %r' % (len(out), out))
def t_first():
    want = {'ts': '2026-08-01T09:14:22Z', 'run': 17, 'ch': 'fx', 'val': -12.4, 'flag': 'ok'}
    if out[0] != want: raise AssertionError('%r' % (out[0],))
def t_nan():
    if not (out[2]['val'] is None and out[2]['run'] == 18):
        raise AssertionError('%r' % (out[2],))
def t_types():
    for r in out:
        if not isinstance(r['run'], int): raise AssertionError('run not int: %r' % (r,))
        if not (r['val'] is None or isinstance(r['val'], float)):
            raise AssertionError('val not float/None: %r' % (r,))
def t_zero():
    if not (out[3]['val'] == 0.0 and out[3]['ch'] == 'mz'):
        raise AssertionError('%r' % (out[3],))
def t_empty():
    if parse([]) != []: raise AssertionError('empty')
check('count', t_count); check('first', t_first); check('nan_none', t_nan)
check('types', t_types); check('zero_kept', t_zero); check('no_raise_empty', t_empty)
"""

T(id="code_parse_log", cat="code", system=SYS_CODE, max_tokens=3000,
  prompt="""Write a Python function `parse(lines)`.

Each well-formed line looks exactly like:

    2026-08-01T09:14:22Z run=17 ch=fx val=-12.4 flag=ok

Return a list of dicts, one per well-formed line, in input order, with keys:
  'ts'   the timestamp string exactly as it appears
  'run'  an int
  'ch'   a str
  'val'  a float, or None if the value is the literal text 'nan'
  'flag' a str

Skip any line that does not match that shape, including blank lines and lines
where a field has the wrong type. Do not raise on malformed input.""",
  score=("pytest", dict(tests_src=PARSE_TESTS)))


# --------------------------------------------------------------- REASONING (6)

T(id="reason_blocks", cat="reason", system=SYS_ANSWER, max_tokens=4000,
  prompt="""A force balance records at 250 Hz for 90 seconds continuously.
The first 12 seconds and the last 8 seconds are discarded as transients.
Of the samples that remain, exactly 3.2 percent are flagged and removed.
The surviving samples are then averaged in non-overlapping blocks of 125 samples.

How many COMPLETE blocks of 125 result? Give an integer.""",
  score=("numeric", dict(expected=135, tol_abs=0.0)))

T(id="reason_bayes2", cat="reason", system=SYS_ANSWER, max_tokens=5000,
  prompt="""A condition is present in 2 percent of a population.

Test A has sensitivity 0.95 and specificity 0.90.
Test B has sensitivity 0.80 and specificity 0.97.
Conditional on true status, the two tests are independent.

A randomly selected individual tests POSITIVE on both tests.
What is the probability they have the condition? Give the answer to three decimal places.""",
  score=("numeric", dict(expected=0.837927, tol_abs=0.0015)))

T(id="reason_cda", cat="reason", system=SYS_ANSWER, max_tokens=4000,
  prompt="""Drag area is defined by D = q * CdA, where D is the drag force and q is the
free-stream dynamic pressure.

A measurement records a drag force of 21.4 N at an air speed of 13.0 m/s
in air of density 1.19 kg/m^3.

Compute CdA in square metres, to three decimal places.""",
  score=("numeric", dict(expected=0.212819, tol_abs=0.0015)))

T(id="reason_control", cat="reason", system=SYS_ANSWER, max_tokens=4000,
  prompt="""Forty riders changed to a new position between their first and second run.
Their drag area fell by an average of 0.008 m^2 from run one to run two.

Forty other riders kept the same position throughout. Between their first and
second run their drag area also fell, by an average of 0.005 m^2.

Using these figures alone, what is the best estimate of the change in drag area
attributable to the position change itself, in m^2?""",
  # use_abs: "the change in drag area" admits both readings. Both quantities FELL,
  # so the attributable change is a reduction of 0.003; writing it as -0.003 (a
  # signed change) or 0.003 (a magnitude) are equally defensible. Opus 5 and
  # Sonnet 5 both answered -0.003 and were initially marked wrong by a key that
  # had quietly assumed the magnitude reading. The task is ambiguous, not them.
  score=("numeric", dict(expected=0.003, tol_abs=0.0005, use_abs=True)))

T(id="reason_ci", cat="reason", system=SYS_ANSWER, max_tokens=4000,
  prompt="""A 95 percent confidence interval for a mean difference is [-0.002, 0.014].
Exactly one of the following statements is correct. Which one?

(a) There is a 95 percent probability that the true difference lies in this interval.
(b) The data are compatible with no difference at the 5 percent level.
(c) The true difference is zero.
(d) Collecting a larger sample would necessarily produce a narrower interval.

Answer with the single letter.""",
  score=("exact", dict(expected="b", aliases=("(b)", "b)"))))

T(id="reason_schedule", cat="reason", system=SYS_ANSWER, max_tokens=5000,
  prompt="""Four runs A, B, C and D fill four consecutive slots numbered 1 to 4,
one run per slot. All of the following hold:

1. A is not in slot 1.
2. C is in the slot immediately after B.
3. D is in slot 1 or slot 4.
4. C is not in slot 2.
5. A is in an earlier slot than C.

Give the order of runs from slot 1 to slot 4 as four letters with no spaces,
for example ABCD.""",
  score=("exact", dict(expected="DABC")))
