# -*- coding: utf-8 -*-
"""Merge a resumed hard-tier part-file into the main hard-tier results.

run_local.py rewrites its output file from scratch, so resuming a partial run
into the same path would silently discard the tasks already completed. The three
truncation results from the first attempt are real measurements and must survive.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(HERE, "results_hard_qwen38.json")
PART = os.path.join(HERE, "results_hard_qwen38_b.json")


def load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def main():
    a, b = load(MAIN), load(PART)
    if not b:
        print("no part file to merge; nothing to do")
        return
    rows = {}
    elapsed = 0.0
    for d in (a, b):
        if not d:
            continue
        elapsed += float(d.get("elapsed_s") or 0)
        for r in d.get("results", []):
            rows[r["task"]] = r
    merged = sorted(rows.values(), key=lambda r: r["task"])
    with open(MAIN, "w", encoding="utf-8") as f:
        json.dump({"model": (b or a).get("model"),
                   "elapsed_s": round(elapsed, 1),
                   "results": merged}, f, indent=1)
    os.replace(PART, PART + ".merged")
    print(f"merged -> {len(merged)} hard tasks, {round(elapsed)}s total")
    for r in merged:
        print(f"   {r['task']:<42} {r['score']:.2f}"
              f"{'  TRUNCATED' if r.get('truncated') else ''}"
              f"  {r.get('completion_tokens')} tok")


if __name__ == "__main__":
    main()
