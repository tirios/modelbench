# -*- coding: utf-8 -*-
"""Measured context-window sweep for a model on tpml-1.

"Model loaded successfully" is not evidence. Earlier in this session three
instances all reported loading while silently spilling to shared system memory,
and one of them served a request with a context a third of what was asked for.
So each rung measures four separate things and only the last one counts:

  1. LOADS      lms load returns success
  2. RESIDENT   nvidia-smi still shows free VRAM, and lms ps reports the context
                we actually asked for
  3. FAST       short-prompt generation stays near the best observed rate; a
                collapse means the KV cache spilled to system RAM
  4. USABLE     a haystack filling ~70% of the window is prefilled AND the model
                still answers three needles from it: one plain fact, one two-hop
                cross-reference, and one fact that is absent and must be declined

A rung is only reported as the usable ceiling if all four hold.
"""
import json
import os
import subprocess
import sys
import time

import corpus
from runner import ask_local
import scorers
from tasks_lc import LC_PARTS, SYS_LC, QUESTIONS

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_KEY = "qwen/qwen3.8-27b"
IDENT = "sweep"
OUT = os.path.join(HERE, "sweep_results.json")

RUNGS = [8192, 16384, 24576, 32768, 49152, 65536, 98304, 131072, 196608, 262144]
CHARS_PER_TOKEN = 4.37      # measured: 132,798 chars -> 30,415 prompt tokens
CHARS_PER_ENTRY = 166.0     # measured on this corpus generator
FILL = 0.70                 # aim the haystack at 70% of the window


def ssh(cmd, timeout=420):
    try:
        p = subprocess.run(["ssh", "-o", "BatchMode=yes", "me@tpml-1", cmd],
                           capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return "__SSH_TIMEOUT__"


def vram():
    out = ssh("nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader", 90)
    try:
        used, free = [int(x.strip().split()[0]) for x in out.strip().splitlines()[0].split(",")]
        return used, free
    except Exception:
        return None, None


def loaded_context():
    out = ssh("lms ps", 120)
    for line in out.splitlines():
        if IDENT in line:
            for tok in line.split():
                if tok.isdigit() and int(tok) >= 1024:
                    return int(tok)
    return None


def entries_for(tokens):
    return max(20, int(round(tokens * CHARS_PER_TOKEN / CHARS_PER_ENTRY)))


def rung(n_ctx, best_tps):
    rec = {"ctx": n_ctx}
    ssh("lms unload --all", 180)
    t0 = time.perf_counter()
    out = ssh(f'lms load {MODEL_KEY} --context-length {n_ctx} --gpu max '
              f'--parallel 1 --identifier {IDENT} -y', 900)
    rec["load_s"] = round(time.perf_counter() - t0, 1)
    rec["loads"] = "Model loaded successfully" in out
    if not rec["loads"]:
        snippet = " ".join(out.split())[-220:]
        rec["error"] = snippet
        rec["resident"] = rec["fast"] = rec["usable"] = False
        return rec

    used, free = vram()
    rec["vram_used_mib"], rec["vram_free_mib"] = used, free
    rec["reported_ctx"] = loaded_context()
    rec["resident"] = bool(free and free > 200 and rec["reported_ctx"] == n_ctx)

    # 3. short generation: a spill shows up as a collapse in tokens/sec
    try:
        r = ask_local(IDENT, "Count from 1 to 30, one number per line, nothing else.",
                      system="Reply directly, no preamble.", max_tokens=300, timeout=900)
        rec["short_tps"] = r["tok_per_s"]
        rec["short_ttft_s"] = r["ttft_s"]
    except Exception as e:
        rec["short_tps"] = None
        rec["short_error"] = f"{type(e).__name__}: {str(e)[:140]}"
    rec["fast"] = bool(rec.get("short_tps") and best_tps and
                       rec["short_tps"] >= 0.70 * best_tps)

    # 4. usable: fill ~70% of the window and require all three needles
    target = int(n_ctx * FILL)
    doc = corpus.build(entries_for(target))
    prompt = "%s\n\n%s" % (doc, QUESTIONS)
    rec["haystack_chars"] = len(doc)
    try:
        r = ask_local(IDENT, prompt, system=SYS_LC, max_tokens=1200, timeout=2400)
        score, detail = scorers.score_multi(r["text"], LC_PARTS)
        rec["prompt_tokens"] = r["prompt_tokens"]
        rec["prefill_s"] = r["ttft_s"]
        rec["prefill_tps"] = (round(r["prompt_tokens"] / r["ttft_s"], 0)
                              if r.get("prompt_tokens") and r.get("ttft_s") else None)
        rec["gen_tps"] = r["tok_per_s"]
        rec["needle_score"] = round(score, 2)
        rec["needle_detail"] = detail[:150]
        rec["usable"] = bool(score >= 0.99)
    except Exception as e:
        rec["usable"] = False
        rec["long_error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return rec


def main():
    results = []
    best_tps = None
    for n in RUNGS:
        print(f"\n=== {n} ===", flush=True)
        rec = rung(n, best_tps)
        if rec.get("short_tps"):
            best_tps = max(best_tps or 0, rec["short_tps"])
            rec["fast"] = rec["short_tps"] >= 0.70 * best_tps
        results.append(rec)
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"model": MODEL_KEY, "results": results}, f, indent=1)
        flags = "".join("Y" if rec.get(k) else "." for k in
                        ("loads", "resident", "fast", "usable"))
        print(f"  {flags}  load {rec.get('load_s')}s  vramfree {rec.get('vram_free_mib')}MiB "
              f"short {rec.get('short_tps')}tps  ptok {rec.get('prompt_tokens')} "
              f"prefill {rec.get('prefill_s')}s  needles {rec.get('needle_score')}",
              flush=True)
        if not rec["loads"] and n >= 65536:
            print("  load failed at this size; larger windows cannot succeed, stopping",
                  flush=True)
            break

    print("\n" + "=" * 92)
    print(f"{'ctx':>8} {'loads':>6} {'resident':>9} {'fast':>6} {'usable':>7} "
          f"{'vram free':>10} {'short tps':>10} {'prompt tok':>11} {'prefill':>9} {'needles':>8}")
    print("=" * 92)
    for r in results:
        print(f"{r['ctx']:>8} {'yes' if r.get('loads') else 'NO':>6} "
              f"{'yes' if r.get('resident') else 'no':>9} "
              f"{'yes' if r.get('fast') else 'no':>6} "
              f"{'YES' if r.get('usable') else 'no':>7} "
              f"{str(r.get('vram_free_mib','-')):>10} "
              f"{str(r.get('short_tps','-')):>10} "
              f"{str(r.get('prompt_tokens','-')):>11} "
              f"{str(r.get('prefill_s','-')):>9} "
              f"{str(r.get('needle_score','-')):>8}")
    ok = [r["ctx"] for r in results if r.get("usable")]
    print("\nMEASURED USABLE CEILING:", max(ok) if ok else "none")
    print("results ->", OUT)


if __name__ == "__main__":
    main()
