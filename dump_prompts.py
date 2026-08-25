# -*- coding: utf-8 -*-
"""Write every task's system prompt and user prompt to disk.

Comparator models are driven as subagents that read these files and write an
answer file. Doing it through files, rather than inline, guarantees the cloud
models see byte-identical prompts to the ones sent to the local endpoint.
"""
import os
from battery import TASKS

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")
os.makedirs(ROOT, exist_ok=True)

for t in TASKS:
    d = os.path.join(ROOT, t["id"])
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "system.txt"), "w", encoding="utf-8") as f:
        f.write(t.get("system", ""))
    with open(os.path.join(d, "prompt.txt"), "w", encoding="utf-8") as f:
        f.write(t["prompt"])
    print("%-22s system %5d chars  prompt %7d chars"
          % (t["id"], len(t.get("system", "")), len(t["prompt"])))

for m in ("opus5", "sonnet5", "haiku45"):
    os.makedirs(os.path.join(os.path.dirname(ROOT), "answers", m), exist_ok=True)
print("\nprompts at:", ROOT)
print("answer dirs created for opus5, sonnet5, haiku45")
