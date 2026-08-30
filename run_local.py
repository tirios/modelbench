# -*- coding: utf-8 -*-
"""Run the battery against a model on the LM Studio endpoint and save raw results.

Usage:
    python run_local.py <model-id> <out.json> [task_id ...]

Saves every response verbatim alongside its score, so a disputed score can be
re-adjudicated later without re-running the model.
"""
import json
import os
import sys
import time

from battery import TASKS, score_task, content_score
from runner import ask_local


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    model = sys.argv[1]
    out_path = sys.argv[2]
    only = set(sys.argv[3:])
    tasks = [t for t in TASKS if not only or t["id"] in only]

    # Thinking models spend the completion budget on reasoning before emitting an
    # answer. The first baseline run capped code tasks at 3000 and every one came
    # back at exactly 3000 tokens with no function defined: a truncation, scored as
    # a model failure. Floors are per category and deliberately generous; the real
    # token cost is reported separately rather than hidden by a tight cap.
    FLOOR = {"code": 20000, "reason": 20000, "format": 8000,
             "hallucination": 8000, "longctx": 4000,
             # The hard tier is longer and needs room to think AND emit a full
             # solution. Qwen3.8 spent 20k tokens reasoning on a simple parser
             # and emitted nothing, so a tight cap here would measure the cap.
             "hardcode": 32000}

    # Experiment overrides. BENCH_EFFORT=none disables the model's reasoning pass
    # (the only mechanism that actually works on this model: /no_think and
    # enable_thinking=false were both measured to have no effect). BENCH_BUDGET
    # overrides the per-task completion ceiling.
    effort = os.environ.get("BENCH_EFFORT")
    budget_override = os.environ.get("BENCH_BUDGET")
    extra = {"reasoning_effort": effort} if effort else None
    if effort or budget_override:
        print(f"    overrides: effort={effort} budget={budget_override}")

    results = []
    t_start = time.time()
    for i, task in enumerate(tasks, 1):
        tid = task["id"]
        print(f"[{i}/{len(tasks)}] {tid} ... ", end="", flush=True)
        rec = {"task": tid, "cat": task["cat"], "model": model}
        try:
            budget = max(task.get("max_tokens", 4096), FLOOR.get(task["cat"], 8000))
            if budget_override:
                budget = int(budget_override)
            r = ask_local(model, task["prompt"], system=task.get("system"),
                          max_tokens=budget, extra=extra, timeout=3600)
            rec["effort"] = effort
            rec["max_tokens"] = budget
            rec["truncated"] = (r.get("completion_tokens") or 0) >= budget
            score, detail = score_task(task, r["text"])
            cscore, _ = content_score(task, r["text"])
            rec.update(r)
            rec["score"] = score
            rec["content_score"] = cscore
            rec["detail"] = detail
            rec["ok"] = True
            rthink = len(r.get("reasoning") or "")
            print(f"score {score:.2f}  {r['completion_tokens']} tok "
                  f"@ {r['tok_per_s']} tok/s  ttft {r['ttft_s']}s"
                  f"{'  TRUNCATED' if rec['truncated'] else ''}"
                  f"  think {rthink}c  ({detail[:44]})")
        except Exception as e:
            rec.update({"ok": False, "error": f"{type(e).__name__}: {e}",
                        "score": 0.0, "detail": "run failed", "text": ""})
            print(f"FAILED {type(e).__name__}: {e}")
        results.append(rec)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"model": model, "elapsed_s": round(time.time() - t_start, 1),
                       "results": results}, f, indent=1)

    ok = [r for r in results if r.get("ok")]
    print(f"\n{len(ok)}/{len(results)} completed, "
          f"mean score {sum(r['score'] for r in results)/max(1,len(results)):.3f}, "
          f"wall {time.time()-t_start:.0f}s -> {out_path}")


if __name__ == "__main__":
    main()
