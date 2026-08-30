# modelbench

A gated benchmark for deciding whether a local model can be trusted with real work.

Built 2026-08-25 to answer one question: is Qwen3.8-27B on the 4090 as good as Opus 4.6,
as was being claimed? It is not. The harness is kept because the question recurs every
time a new local model lands, and rebuilding it each time is the expensive part.

## What makes this different from running a few prompts

Every task ships with a **known-correct solution and a deliberately broken one**. A task
counts only if the correct one scores full marks and the broken one clearly fails. A task
that cannot separate them is not used.

This is not ceremony. The gate caught three real defects in the scoring during the first
build, one of which had already marked Opus 5 and Sonnet 5 wrong for giving the *better*
reading of an ambiguous question. Without the gate the benchmark would have confidently
reported a false ranking.

Run the gate before trusting any result:

```bash
python validate_hard.py
```

Expected: 8 usable, 0 broken, 0 blunt. References at 1.00, mutants at or below 0.43.

## Layout

| Path | What it is |
|---|---|
| `runner.py` | Streaming client for any OpenAI-compatible endpoint |
| `scorers.py` | All scoring functions; each returns `(score, detail)` |
| `battery.py` | Assembles the task set and exposes `score_task` / `content_score` |
| `tasks_core.py` | 5 everyday coding + 6 reasoning tasks |
| `tasks_extra.py` | 4 instruction-following + 2 hallucination traps |
| `tasks_lc.py` | 2 long-context needle probes |
| `tasks_hard.py` | Loads the 8 hard coding tasks from `hard_tasks.json` |
| `hard_tasks.json` | The hard tier: prompt, reference, mutant, hidden tests, review notes |
| `corpus.py` | Deterministic synthetic haystack for the long-context probes |
| `run_local.py` | Runs the battery against a local endpoint |
| `score_answers.py` | Scores cloud-model answers from `answers/<model>/<task>.txt` |
| `sweep_context.py` | Measured context-window sweep (loads / resident / fast / usable) |
| `status_server.py` | Live progress page on `localhost:5090` |
| `final_numbers.py` | Recomputes every reported figure from the result files |
| `results_*.json` | The measurements, one file per arm |
| `logs/` | Run logs and the pre-merge part file, kept as raw evidence |

## Re-running it on a new model

```bash
python validate_hard.py
```

```bash
BENCH_EFFORT=none python run_local.py
```

Point it at a different box with `MODELBENCH_ENDPOINT`. The default is the tailnet address
of the 4090.

```bash
MODELBENCH_ENDPOINT=http://host:1234/v1/chat/completions python run_local.py
```

## Three things that cost hours, worth knowing before you re-run

**Give coding tasks a real token budget.** The first run capped them at 3000 and every
coding task scored zero with a truncated-code error. The model had spent the entire budget
on private reasoning. Per-category floors now live in `run_local.py`.

**Only one reasoning-suppression mechanism works on Qwen3.8.** Six were measured, recorded
in `nothink_mechanisms.json`. Only `reasoning_effort: "none"` does anything. The widely
documented `/no_think` string, the `enable_thinking` flag, an effort of `low`, and plain
instructions to answer immediately all left private reasoning untouched and output empty.

**Check what is actually loaded before believing a long-context result.** Three LM Studio
instances were once resident at once and the API silently served the smallest, producing a
long-context failure that looked like a model limitation. Always `lms unload --all` first,
then confirm with `lms ps`.

## Headline result, 2026-08-25

27 gated tasks. Scores are the fraction of hidden checks passed.

| Model | Non-code /14 | Everyday code /5 | Hard code /8 | Total |
|---|---|---|---|---|
| Opus 5 | 14.00 | 5.00 | 8.00 | 27.00 |
| Sonnet 5 | 14.00 | 5.00 | 8.00 | 27.00 |
| Opus 4.6 | not run | not run | 8.00 | 8.00 / 8 |
| Haiku 4.5 | 13.00 | 5.00 | 7.69 | 25.69 |
| Qwen3.8, reasoning off | 13.88 | 5.00 | 6.69 | 25.57 |
| Qwen3.8, reasoning on | 14.00 | 4.00 | 1.00 | 19.00 |
| Qwen3.6, reasoning on | 13.00 | 5.00 | incomplete | 18.00 / 20 |

Qwen3.8 is Haiku-class, not Opus-class. Opus 4.6 was tested on the hard tier only, because
the other 19 tasks are saturated by every cloud model and would have confirmed a foregone
conclusion.

The reasoning-on row is the finding that matters operationally: it does not write bad code,
it writes *no* code, spending its whole budget deliberating and returning an empty reply.
Doubling the budget doubled the deliberation and still returned nothing.

## Measured context ceiling on one RTX 4090

Usable means it loads, keeps spare VRAM, holds generation speed, and still answers three
needles from a haystack filling 70% of the window.

| Window | Usable | Gen tok/s | VRAM free | Prefill tok/s |
|---|---|---|---|---|
| 65,536 | yes | 106 | 1,046 MB | 2,218 |
| 98,304 | tight | 104 | 52 MB | 1,993 |
| 131,072 | no | 22 | 207 MB | 64 |

65,536 is the recommended setting. At 131,072 the KV cache spills to system memory and one
long document takes 24 minutes to read. It was still *accurate* there, so testing only
whether answers were right would have declared that size fine.

196,608 and 262,144 are unmeasured, not tested-and-failed.

## Data

No proprietary or partner data anywhere. The long-context probes run on a synthetic
notebook generated by `corpus.py`. Safe to keep private and safe to re-run.
