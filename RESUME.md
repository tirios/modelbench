# Qwen3.8 benchmark — resume notes (paused 2026-08-25)

## What is finished

- **Battery**: 27 tasks. 19 easy (5 code, 6 reason, 4 format, 2 hallucination,
  2 long-context) + 8 hard coding. Every task gated: reference scores 1.00,
  deliberately-wrong mutant scores below 0.5. `python validate_battery.py`
  re-runs that gate; `python validate_scorers.py` gates the scorers themselves.
- **Cloud arms, all 27 tasks done**: Opus 5 = 27/27, Sonnet 5 = 27/27,
  Haiku 4.5 = 0.914 (see gap below). Answers in `answers/<model>/<task>.txt`,
  scores in `results_<model>.json`.
- **Local easy tier done**: qwen3.8 = 18/19 in 520s, qwen3.6 = 18/19 in 1284s.

## Configuration that matters

- Model `qwen/qwen3.8-27b`, Q4_K_M, loaded as a SINGLE instance,
  `--context-length 65536 --gpu max --parallel 1 --identifier q38`.
- Load exactly one instance. Three were loaded at once earlier (24k/32k/40k) and
  the API silently routed to the 24k one, which failed the 32k probe with
  `n_ctx: 24576`. Always check `lms ps` before trusting a local result.
- 64k costs 23.1 GiB of the 24 GB card, ~1 GiB spare. LM Studio's
  `--estimate-only` runs about 2 GiB conservative; real cost ~86 KiB/token,
  because only 16 of the 64 layers are full attention.

## Remaining work

1. `answers/haiku45/hard_parse.txt` is MISSING — that agent returned its code in
   chat instead of writing the file, so Haiku's 0.914 counts it as zero. Re-run
   that one task and rescore; Haiku's true figure is higher.
2. Local hard tier was still running when paused: `chain_hard.sh` runs qwen3.6's
   8 hard tasks, then swaps to qwen3.8 at 65536 and runs its 8. Outputs land in
   `results_hard_qwen36.json` / `results_hard_qwen38.json` and
   `run36_hard.log` / `run38_hard.log`. Check `chain_hard.out` for
   "ALL LOCAL RUNS COMPLETE". This costs no Claude tokens.
3. `python aggregate.py` builds the comparison table once results exist. It reads
   any `results_*.json`, so merge the hard-tier files in first.
4. Write the final report.

## Findings already established

- The easy tier is saturated by every cloud model, so it has no resolution
  between cloud tiers. The hard tier did NOT fix that: Opus 5 and Sonnet 5 both
  still score 27/27. It does discriminate downward.
- Qwen3.8's one easy-tier failure, `code_parse_log`, reproduced EXACTLY across
  two independent runs: 20,000 tokens, ~47,000 characters of reasoning,
  truncated, no code emitted. A deterministic runaway-reasoning failure.
- qwen3.6 failed `hall_fake_method` (described a fabricated method rather than
  declining); qwen3.8 declined correctly. The two locals fail differently.
- Qwen3.8 generation 87-98 tok/s vs qwen3.6 at 47 tok/s. 30,415-token prefill
  in 13.3s (~2,290 tok/s).

## Corrections made to the harness, worth not repeating

- Token caps: thinking models spend the whole budget reasoning. A 3000-token cap
  made every coding task score 0 with "name not defined". Per-category floors now
  live in `run_local.py`.
- `score_abstain` applied fabrication patterns with `re.I`, which silently
  defeated every `[A-Z]` capitalisation test. Now case-sensitive.
- A `\b` written into a regex through a shell heredoc became a literal backspace
  byte (`\x08`), making patterns unmatchable while looking correct on screen.
- `reason_control` was ambiguous: "the change in drag area" admits both signs.
  Opus 5 and Sonnet 5 answered -0.003 and were wrongly marked down. Now accepts
  either sign.
- `pkill -f run_local.py` does NOT kill these processes on this machine. Two runs
  interleaved into one results file before it was caught. Verify with
  `ps -W | grep -c 'Python312/python$'`.
- Task-authoring subagents used this directory as scratch and overwrote
  `reference.py`. Restored; their files are quarantined in `agent_scratch/`.
