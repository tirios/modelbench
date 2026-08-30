# -*- coding: utf-8 -*-
"""Build the comparison table across every arm that has a results file."""
import glob
import json
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
CATS = ["code", "reason", "format", "hallucination", "longctx"]
ORDER = ["qwen38", "qwen36", "haiku45", "sonnet5", "opus5"]
LABEL = {
    "qwen38": "Qwen3.8-27B (local)",
    "qwen36": "Qwen3.6-27B (local)",
    "haiku45": "Haiku 4.5",
    "sonnet5": "Sonnet 5",
    "opus5": "Opus 5",
}


def load():
    arms = {}
    for path in glob.glob(os.path.join(ROOT, "results_*.json")):
        key = os.path.basename(path)[len("results_"):-len(".json")]
        with open(path, encoding="utf-8") as f:
            arms[key] = json.load(f)
    return arms


def main():
    arms = load()
    keys = [k for k in ORDER if k in arms] + [k for k in arms if k not in ORDER]

    print("OVERALL (strict score: content AND required output format)\n")
    hdr = f"{'arm':<22}" + "".join(f"{c[:6]:>8}" for c in CATS) + f"{'ALL':>8}{'n':>4}"
    print(hdr); print("-" * len(hdr))
    per_task = defaultdict(dict)
    for k in keys:
        res = arms[k]["results"]
        by = defaultdict(list)
        for r in res:
            by[r["cat"]].append(r["score"])
            per_task[r["task"]][k] = r["score"]
        row = f"{LABEL.get(k, k):<22}"
        for c in CATS:
            v = by.get(c)
            row += f"{(sum(v)/len(v)):>8.2f}" if v else f"{'-':>8}"
        allv = [r["score"] for r in res]
        row += f"{sum(allv)/len(allv):>8.2f}{len(allv):>4}"
        print(row)

    print("\n\nPER TASK\n")
    hdr2 = f"{'task':<22}" + "".join(f"{LABEL.get(k,k).split()[0][:8]:>10}" for k in keys)
    print(hdr2); print("-" * len(hdr2))
    for task in per_task:
        line = f"{task:<22}"
        for k in keys:
            v = per_task[task].get(k)
            line += f"{v:>10.2f}" if v is not None else f"{'-':>10}"
        print(line)

    print("\n\nLOCAL SPEED AND TOKEN COST\n")
    hdr3 = (f"{'arm':<22}{'tok/s':>8}{'ttft s':>9}{'out tok':>9}"
            f"{'think ch':>10}{'wall s':>9}{'trunc':>7}")
    print(hdr3); print("-" * len(hdr3))
    for k in keys:
        res = [r for r in arms[k]["results"] if r.get("tok_per_s")]
        if not res:
            continue
        tps = [r["tok_per_s"] for r in res]
        ttft = [r["ttft_s"] for r in res if r.get("ttft_s")]
        ct = [r["completion_tokens"] for r in res if r.get("completion_tokens")]
        think = [len(r.get("reasoning") or "") for r in res]
        wall = arms[k].get("elapsed_s", 0)
        trunc = sum(1 for r in arms[k]["results"] if r.get("truncated"))
        print(f"{LABEL.get(k,k):<22}{sum(tps)/len(tps):>8.1f}{sum(ttft)/len(ttft):>9.2f}"
              f"{sum(ct)/len(ct):>9.0f}{sum(think)/len(think):>10.0f}"
              f"{wall:>9.0f}{trunc:>7}")

    print("\n\nFAILURES AND FORMAT MISSES\n")
    for k in keys:
        bad = [r for r in arms[k]["results"] if r["score"] < 1.0]
        if not bad:
            print(f"{LABEL.get(k,k)}: none, clean sweep")
            continue
        print(f"{LABEL.get(k,k)}:")
        for r in bad:
            cs = r.get("content_score")
            tag = " (content correct, format miss)" if cs is not None and cs > r["score"] else ""
            print(f"   {r['task']:<22} {r['score']:.2f}{tag}  {r.get('detail','')[:58]}")


if __name__ == "__main__":
    main()
