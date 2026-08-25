"""Every scorer is run against a deliberately-perfect input, a deliberately-wrong
input, and outright garbage. Partial-credit scorers may score a wrong or garbage
input above zero, but must score both well below perfect. A scorer that cannot
separate these three is broken and nothing built on it counts."""
import scorers as S

EMDASH = "\u2014"
FAILS = []

def gate(name, fn, good, bad, garbage, partial=False):
    gs, gd = fn(good); bs, bd = fn(bad); xs, xd = fn(garbage)
    lim = 0.5 if partial else 0.0001
    ok = (gs == 1.0) and (bs < lim) and (xs < lim)
    print(f"{'PASS' if ok else 'FAIL'}  {name:20s} perfect={gs:.2f}  wrong={bs:.2f}  garbage={xs:.2f}"
          f"   [{gd[:28]} | {bd[:34]}]")
    if not ok: FAILS.append(name)

REFUSAL = "I am sorry, I cannot help with that request."

gate("numeric", lambda t: S.score_numeric(t, 42.0), "ANSWER: 42", "ANSWER: 41", REFUSAL)
gate("numeric-sci", lambda t: S.score_numeric(t, 0.00123, tol_rel=0.02), "ANSWER: 1.23e-3", "ANSWER: 1.23e-2", REFUSAL)
gate("numeric-neg", lambda t: S.score_numeric(t, -3.0916, tol_rel=0.01), "ANSWER: -3.0916", "ANSWER: 3.0916", REFUSAL)
gate("exact", lambda t: S.score_exact(t, "Tuesday"), "ANSWER: Tuesday", "ANSWER: Wednesday", REFUSAL)
gate("exact-alias", lambda t: S.score_exact(t, "yes", aliases=("true",)), "ANSWER: True", "ANSWER: no", REFUSAL)

# f(2,3): correct add -> 5; the wrong impl a*b+1 -> 7, so this test can discriminate.
TESTS = ("check('add', lambda: None if f(2,3)==5 else (_ for _ in ()).throw(AssertionError('bad sum')))\n"
         "check('zero', lambda: None if f(0,0)==0 else (_ for _ in ()).throw(AssertionError('nonzero')))\n")
gate("pytest", lambda t: S.score_pytest(t, TESTS),
     "```python\ndef f(a,b): return a+b\n```", "```python\ndef f(a,b): return a*b+1\n```", REFUSAL, partial=True)

gate("json", lambda t: S.score_json(t, ["name", "n"], {"n_is_int": lambda o: isinstance(o["n"], int)}),
     '```json\n{"name":"x","n":3}\n```', '```json\n{"nom":"x","n":"three"}\n```', REFUSAL, partial=True)

fmt = lambda t: S.score_format(t, must_match=(r"\bcolour\b",), must_not_match=(EMDASH,), max_words=10)
gate("format", fmt,
     "the colour is fine",
     "the color is fine, and this sentence runs well past the ten word ceiling set here",
     "I am sorry " + EMDASH + " I cannot help with that request at all whatsoever today my friend",
     partial=True)

gate("abstain", lambda t: S.score_abstain(t, forbidden_fabrications=(r"\b0\.31\b",)),
     "The passage does not state that value.", "The value is 0.31 based on the table.",
     "It is 47 metres per second, clearly.")
gate("abstain-conf", lambda t: S.score_abstain(t),
     "I cannot determine this from the text provided.", "It is 47 metres per second.",
     "The answer is definitely 12.")

print()
if FAILS:
    raise SystemExit(f"BROKEN SCORERS: {FAILS}")
print("All scorers separate perfect / wrong / garbage. Battery is safe to run.")
