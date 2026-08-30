"""Local LM Studio runner: streams a completion and records real timing.

Timing definitions used throughout:
  ttft_s      wall seconds from request send to the FIRST content token
  gen_s       wall seconds from first token to last token
  tok_per_s   completion_tokens / gen_s  (pure generation rate, excludes prefill)
  total_s     ttft_s + gen_s
Prefill cost lands in ttft_s, which is why long-context tasks are timed separately.
"""
import json, time, urllib.request

import os as _os
# Overridable so the battery can be pointed at any OpenAI-compatible endpoint.
ENDPOINT = _os.environ.get(
    "MODELBENCH_ENDPOINT", "http://localhost:1234/v1/chat/completions")


def ask_local(model, prompt, system=None, max_tokens=4096, temperature=0.0,
              timeout=1800, extra=None):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    body = {
        "model": model,
        "messages": msgs,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if extra:
        body.update(extra)
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    ttft = None
    t_last = None
    chunks = []
    reasoning = []
    usage = {}
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if obj.get("usage"):
                usage = obj["usage"]
            for ch in obj.get("choices", []):
                d = ch.get("delta") or {}
                # LM Studio surfaces thinking separately on reasoning models
                rc = d.get("reasoning_content") or d.get("reasoning")
                if rc:
                    reasoning.append(rc)
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    t_last = time.perf_counter()
                c = d.get("content")
                if c:
                    chunks.append(c)
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    t_last = time.perf_counter()
    t_end = time.perf_counter()
    text = "".join(chunks)
    think = "".join(reasoning)
    gen_s = (t_last - (t0 + ttft)) if (ttft is not None and t_last) else 0.0
    ct = usage.get("completion_tokens")
    return {
        "text": text,
        "reasoning": think,
        "ttft_s": round(ttft, 3) if ttft is not None else None,
        "gen_s": round(gen_s, 3),
        "total_s": round(t_end - t0, 3),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": ct,
        "tok_per_s": round(ct / gen_s, 2) if (ct and gen_s > 0.05) else None,
    }
