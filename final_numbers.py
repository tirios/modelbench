# -*- coding: utf-8 -*-
"""Definitive figures for the write-up, computed from the result files.

Nothing in the report is hand-copied: every number the summary quotes is printed
here, so a claim in the prose can be checked against the measurement that
produced it.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
NONCODE = {"reason", "format", "hallucination", "longctx"}


def load(*paths):
    rows = {}
    for p in paths:
        try:
            with open(os.path.join(HERE, p), encoding="utf-8") as f:
                for r in json.load(f)["results"]:
                    rows[r["task"]] = r
        except Exception:
            pass
    return rows


def split(rows):
    nc = [r for r in rows.values() if r["cat"] in NONCODE]
    ec = [r for r in rows.values() if r["cat"] == "code"]
    hc = [r for r in rows.values() if r["cat"] == "hardcode"]
    return nc, ec, hc


def line(label, rows):
    nc, ec, hc = split(rows)
    tot = sum(r["score"] for r in rows.values())
    def s(v, n):
        return f"{sum(r['score'] for r in v):.2f}/{n}" if v else "   -  "
    print(f"{label:<34} {s(nc,14):>9} {s(ec,5):>8} {s(hc,8):>9} "
          f"{tot:>7.2f}/{len(rows):<3} {tot/max(1,len(rows)):>6.3f}")
    return tot, len(rows)


ARMS = [
    ("Qwen3.8 local, reasoning ON",
     ("results_qwen38.json", "results_hard_qwen38.json")),
    ("Qwen3.8 local, reasoning OFF",
     ("results_nothink_noncode_qwen38.json", "results_nothink_easycode_qwen38.json",
      "results_nothink_qwen38.json")),
    ("Qwen3.6 local, reasoning ON",
     ("results_qwen36.json", "results_hard_qwen36.json")),
    ("Haiku 4.5", ("results_haiku45.json",)),
    ("Opus 4.6 (hard only)", ("results_opus46.json",)),
    ("Sonnet 5", ("results_sonnet5.json",)),
    ("Opus 5", ("results_opus5.json",)),
]

print(f"{'arm':<34} {'non-code':>9} {'easy':>8} {'hard':>9} {'total':>11} {'mean':>6}")
print("-" * 84)
for label, paths in ARMS:
    rows = load(*paths)
    if rows:
        line(label, rows)

print("\nSPEED AND COST (local, measured)")
print("-" * 84)
for label, paths in [("Qwen3.8 reasoning ON", ("results_qwen38.json", "results_hard_qwen38.json")),
                     ("Qwen3.8 reasoning OFF", ("results_nothink_noncode_qwen38.json",
                                                "results_nothink_easycode_qwen38.json",
                                                "results_nothink_qwen38.json")),
                     ("Qwen3.6 reasoning ON", ("results_qwen36.json",))]:
    rows = load(*paths)
    if not rows:
        continue
    tps = [r["tok_per_s"] for r in rows.values() if r.get("tok_per_s")]
    out = [r["completion_tokens"] for r in rows.values() if r.get("completion_tokens")]
    think = [len(r.get("reasoning") or "") for r in rows.values()]
    silent = [r for r in rows.values() if not (r.get("text") or "")]
    print(f"{label:<34} {sum(tps)/len(tps):>6.1f} tok/s   "
          f"median out {sorted(out)[len(out)//2]:>6} tok   "
          f"mean reasoning {sum(think)//len(think):>7,} chars   "
          f"empty replies {len(silent):>2}/{len(rows)}")

print("\nCONTEXT SWEEP (measured, Qwen3.8 on one RTX 4090)")
print("-" * 84)
try:
    sw = json.load(open(os.path.join(HERE, "sweep_results.json"), encoding="utf-8"))
    print(f"{'ctx':>8} {'usable':>7} {'gen tok/s':>10} {'VRAM free':>10} "
          f"{'prompt tok':>11} {'prefill s':>10} {'prefill tok/s':>14}")
    for r in sw["results"]:
        print(f"{r['ctx']:>8} {'YES' if r.get('usable') else 'no':>7} "
              f"{str(r.get('short_tps','-')):>10} {str(r.get('vram_free_mib','-')):>10} "
              f"{str(r.get('prompt_tokens','-')):>11} {str(r.get('prefill_s','-')):>10} "
              f"{str(r.get('prefill_tps','-')):>14}")
except Exception as e:
    print("  sweep unavailable:", e)
