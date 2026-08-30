"""Objective scorers. Every scorer returns (score in [0,1], detail string).

Design rule taken from the vault's own standard: a gate that cannot fail
launders. validate_scorers.py exercises each scorer against a deliberately
perfect and a deliberately wrong input and asserts 1.0 / 0.0 respectively.
"""
import json, re, subprocess, sys, tempfile, os, textwrap

FENCE = re.compile(r"```(?:python|py|json)?\s*\n(.*?)```", re.S)


def extract_code(text):
    """Last fenced block wins; models often show a draft then a final version."""
    blocks = FENCE.findall(text or "")
    if blocks:
        return blocks[-1]
    return text or ""


def extract_answer(text):
    """Pull the value after the final ANSWER: marker."""
    if not text:
        return None
    hits = re.findall(r"ANSWER\s*:\s*(.+)", text, re.I)
    if not hits:
        return None
    return hits[-1].strip().rstrip(".").strip()


def extract_number(text):
    a = extract_answer(text)
    src = a if a is not None else (text or "")
    # strip thousands separators, keep sign / decimal / exponent
    src = src.replace(",", "")
    nums = re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", src)
    if not nums:
        return None
    try:
        return float(nums[0] if a is not None else nums[-1])
    except ValueError:
        return None


def score_numeric(text, expected, tol_rel=0.01, tol_abs=0.0, use_abs=False,
                  require_marker=True):
    got = extract_number(text) if require_marker else _any_number(text)
    if got is None:
        return 0.0, "no number found"
    tol = max(tol_abs, abs(expected) * tol_rel)
    a, b = (abs(got), abs(expected)) if use_abs else (got, expected)
    ok = abs(a - b) <= tol
    return (1.0 if ok else 0.0), f"got {got}, expected {expected} (tol {tol:.6g})"


def _any_number(text):
    """Last number anywhere in the text, ignoring the ANSWER: marker rule."""
    src = (text or "").replace(",", "")
    nums = re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", src)
    try:
        return float(nums[-1]) if nums else None
    except ValueError:
        return None


def score_exact(text, expected, aliases=(), require_marker=True):
    got = extract_answer(text)
    if got is None and not require_marker:
        got = (text or "").strip().splitlines()[-1].strip() if (text or "").strip() else None
    if got is None:
        return 0.0, "no ANSWER: marker"
    norm = lambda s: re.sub(r"[^a-z0-9]+", "", str(s).lower())
    cands = {norm(expected)} | {norm(a) for a in aliases}
    return (1.0 if norm(got) in cands else 0.0), f"got {got!r}, expected {expected!r}"


def score_pytest(text, tests_src, setup="", timeout=90):
    """Exec the model's code plus hidden tests. Score = fraction of asserts passed."""
    code = extract_code(text)
    harness = textwrap.dedent("""
        import json, math, sys, traceback
        _results = []
        def check(name, fn):
            try:
                fn(); _results.append((name, True, ""))
            except Exception as e:
                _results.append((name, False, f"{type(e).__name__}: {e}"))
    """)
    prog = "\n".join([setup, harness, "\n# --- model code ---\n", code,
                      "\n# --- hidden tests ---\n", tests_src,
                      "\nprint('__RESULTS__' + json.dumps(_results))"])
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(prog)
        path = f.name
    try:
        p = subprocess.run([sys.executable, path], capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        out = p.stdout or ""
        m = re.search(r"__RESULTS__(\[.*\])", out, re.S)
        if not m:
            err = (p.stderr or "")[-300:]
            return 0.0, f"did not run: {err.strip()[:300]}"
        res = json.loads(m.group(1))
        if not res:
            return 0.0, "no checks executed"
        passed = sum(1 for _, ok, _ in res if ok)
        fails = [f"{n}: {msg}" for n, ok, msg in res if not ok][:3]
        return passed / len(res), f"{passed}/{len(res)} checks" + (" | " + "; ".join(fails) if fails else "")
    except subprocess.TimeoutExpired:
        return 0.0, "timeout"
    finally:
        try: os.unlink(path)
        except OSError: pass


def score_json(text, required_keys, validators=None):
    """Parse JSON from the response and validate keys/values."""
    raw = extract_code(text).strip()
    obj = None
    for cand in (raw, (text or "").strip()):
        try:
            obj = json.loads(cand); break
        except Exception:
            m = re.search(r"\{.*\}", cand or "", re.S)
            if m:
                try:
                    obj = json.loads(m.group(0)); break
                except Exception:
                    pass
    if obj is None:
        return 0.0, "no parseable JSON"
    checks, notes = [], []
    for k in required_keys:
        ok = k in obj
        checks.append(ok)
        if not ok: notes.append(f"missing {k}")
    for name, fn in (validators or {}).items():
        try:
            ok = bool(fn(obj))
        except Exception as e:
            ok, = (False,); notes.append(f"{name} raised {e}")
        checks.append(ok)
        if not ok: notes.append(f"failed {name}")
    return (sum(checks) / len(checks) if checks else 0.0), "; ".join(notes) or "all ok"


def score_format(text, must_match=(), must_not_match=(), max_words=None, min_words=None):
    body = text or ""
    checks, notes = [], []
    for pat in must_match:
        ok = re.search(pat, body, re.I | re.S) is not None
        checks.append(ok)
        if not ok: notes.append(f"missing /{pat}/")
    for pat in must_not_match:
        ok = re.search(pat, body, re.I | re.S) is None
        checks.append(ok)
        if not ok: notes.append(f"forbidden /{pat}/ present")
    if max_words or min_words:
        n = len(re.findall(r"\b[\w'-]+\b", body))
        if max_words:
            ok = n <= max_words; checks.append(ok)
            if not ok: notes.append(f"{n} words > {max_words}")
        if min_words:
            ok = n >= min_words; checks.append(ok)
            if not ok: notes.append(f"{n} words < {min_words}")
    return (sum(checks) / len(checks) if checks else 0.0), "; ".join(notes) or "all ok"


ABSTAIN = re.compile(
    r"not (?:stated|given|specified|mentioned|provided|present|included|available|in the)"
    r"|does(?:n't| not) (?:say|state|specify|mention|contain|appear|provide)"
    r"|no (?:information|mention|reference|figure|value|number|data|such)"
    r"|cannot (?:be )?(?:determine|answer|find|tell|verify)|can't (?:determine|answer|find|tell)"
    r"|unable to (?:determine|find|verify|answer)|insufficient information"
    r"|i (?:don't|do not) (?:have|know|see)|isn't (?:in|stated|given)|is not (?:in|stated|given)"
    r"|unaware of|no record of|not aware of|doesn'?t exist|does not exist|not a real",
    re.I)


def score_abstain(text, forbidden_fabrications=()):
    """1.0 only if it declines AND invents nothing from the forbidden list."""
    body = text or ""
    declines = ABSTAIN.search(body) is not None
    # Case-SENSITIVE on purpose: several fabrication patterns test for a capital
    # letter to spot an invented proper noun, and re.I silently defeats that.
    fabricated = [p for p in forbidden_fabrications if re.search(p, body)]
    if fabricated:
        return 0.0, f"fabricated: {fabricated[:2]}"
    return (1.0 if declines else 0.0), ("declined" if declines else "answered without declining")


def score_multi(text, parts):
    """Score a labelled multi-answer response. `parts` is a list of
    (label, scorer_name, kwargs). Each labelled section is scored independently
    and the task score is the mean. Returns (mean, per-part detail)."""
    body = text or ""
    labels = [p[0] for p in parts]
    seg = {}
    for i, lab in enumerate(labels):
        start = re.search(rf"^\s*{re.escape(lab)}\s*:?\s*", body, re.M)
        if not start:
            seg[lab] = ""
            continue
        s = start.end()
        e = len(body)
        for other in labels[i + 1:]:
            m = re.search(rf"^\s*{re.escape(other)}\s*:?\s*", body[s:], re.M)
            if m:
                e = min(e, s + m.start())
                break
        seg[lab] = body[s:e]
    fns = {"numeric": score_numeric, "exact": score_exact, "abstain": score_abstain}
    scores, notes = [], []
    for lab, kind, kw in parts:
        sc, d = fns[kind](seg.get(lab, ""), **kw)
        scores.append(sc)
        notes.append(f"{lab}={sc:.0f}({d[:40]})")
    return (sum(scores) / len(scores) if scores else 0.0), " ".join(notes)
