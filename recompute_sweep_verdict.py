# -*- coding: utf-8 -*-
"""Recompute the stored sweep verdicts under the corrected four-part rule.

The columns in sweep_results.json were measured correctly; only the `usable`
flag derived from them was wrong (it read the needle score alone). This rewrites
the flag in place and renames the needle-only result to `needles_ok`, matching
what sweep_context.py now writes.

The rule is tested against a deliberately-perfect and a deliberately-wrong record
before it is applied, because a gate that cannot fail is what produced the bug.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "sweep_results.json")


def verdict(r):
    return bool(r.get("loads") and r.get("resident")
                and r.get("fast") and r.get("needles_ok"))


def selftest():
    perfect = {"loads": True, "resident": True, "fast": True, "needles_ok": True}
    if not verdict(perfect):
        raise AssertionError("gate rejects a perfect record")
    for drop in ("loads", "resident", "fast", "needles_ok"):
        bad = dict(perfect, **{drop: False})
        if verdict(bad):
            raise AssertionError("gate ACCEPTS a record failing %s" % drop)
    print("selftest: gate accepts perfect, rejects each single failure  OK")


def main():
    selftest()
    d = json.load(open(P, encoding="utf-8"))
    changed = []
    for r in d["results"]:
        if "needles_ok" not in r:
            r["needles_ok"] = bool(r.get("needle_score", 0) >= 0.99)
        was = r.get("usable")
        now = verdict(r)
        if was != now:
            changed.append((r["ctx"], was, now))
        r["usable"] = now
    d["verdict_rule"] = ("usable = loads AND resident AND fast AND needles_ok; "
                         "corrected 2026-08-26, previously needles only")
    json.dump(d, open(P, "w", encoding="utf-8"), indent=1)

    print("\n%8s %7s %9s %6s %10s %8s" % ("ctx", "loads", "resident", "fast", "needles_ok", "usable"))
    for r in d["results"]:
        print("%8d %7s %9s %6s %10s %8s" % (r["ctx"], r.get("loads"), r.get("resident"),
                                            r.get("fast"), r.get("needles_ok"), r["usable"]))
    ok = [r["ctx"] for r in d["results"] if r["usable"]]
    print("\nverdicts changed:", changed if changed else "none")
    print("MEASURED USABLE CEILING now:", max(ok) if ok else None)


if __name__ == "__main__":
    main()
