# -*- coding: utf-8 -*-
"""Score the answer files written by the comparator subagents.

Usage: python score_answers.py <model-dir-name> <out.json>
Applies exactly the same scorers used for the local endpoint, so the only
difference between arms is which model produced the text.
"""
import json
import os
import sys

from battery import TASKS, score_task, content_score

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    model = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else f"results_{model}.json"
    adir = os.path.join(ROOT, "answers", model)
    results = []
    for t in TASKS:
        path = os.path.join(adir, t["id"] + ".txt")
        rec = {"task": t["id"], "cat": t["cat"], "model": model}
        if not os.path.exists(path):
            rec.update({"ok": False, "score": 0.0, "detail": "NO ANSWER FILE", "text": ""})
            print(f"  {t['id']:<22} MISSING")
        else:
            text = open(path, encoding="utf-8", errors="replace").read()
            score, detail = score_task(t, text)
            cscore, _ = content_score(t, text)
            rec.update({"ok": True, "score": score, "content_score": cscore,
                        "detail": detail, "text": text, "chars": len(text)})
            flag = "  [content ok, format miss]" if cscore > score else ""
            print(f"  {t['id']:<22} {score:5.2f}  {detail[:52]}{flag}")
        results.append(rec)
    mean = sum(r["score"] for r in results) / len(results)
    cmean = sum(r.get("content_score", r["score"]) for r in results) / len(results)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"model": model, "results": results}, f, indent=1)
    print(f"\n{model}: mean {mean:.3f} over {len(results)} tasks -> {out_path}")


if __name__ == "__main__":
    main()
