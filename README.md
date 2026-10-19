# noisy

Feasibility study for reducing ambient noise at my desk using only the ThinkPad's built-in
microphones and speakers. Brief and phases: `PROMPT.md`. How we work: `CLAUDE.md`. Pitfalls:
`GOTCHAS.md`. Status: `TASKS.md`.

## Setup
```
uv sync
uv run pytest
```

## Measurement commands
All commands write WAV + JSON to `data/` (gitignored) and print a summary. `--help` on any
command lists its options.

| Command | Plays audio | What it does |
|---------|-------------|--------------|
| `uv run python -m noisy audit` | no | devices, formats, minimum latency, APO/enhancement state → `reports/data/audit.json` |
| `uv run python -m noisy record --mode exclusive --seconds 600 --label <what>` | no | raw mic recording |
| `uv run python -m noisy rawcheck` | yes, 12 s per mode | which capture mode is unprocessed |
| `uv run python -m noisy ir --mode exclusive` | yes, ~20 s | speaker→mic impulse responses, clock drift |
| `uv run python -m noisy latency --mode exclusive` | yes, ~6 s | round-trip latency |

What each measurement checks and why it matters: `reports/phase0-device-audit.md` §2.

Capture modes: `shared` (what normal apps get, APOs active), `shared-raw`, `exclusive`
(WASAPI exclusive + raw), `wdmks` (kernel streaming). Default is `exclusive`.

## Layout
- `noisy/` — package: `devices`, `audit`, `capture` (device I/O); `sweep`, `latency` (pure DSP);
  `__main__` (CLI).
- `tests/` — offline tests on synthetic signals.
- `reports/` — per-phase reports; `reports/figures/` plots; `reports/data/` small result files.
- `tasks/` — per-task briefings indexed in `TASKS.md`.
