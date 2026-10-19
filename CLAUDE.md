# Working with Claude on this project

The project brief is `PROMPT.md` (a phased ANC feasibility study on built-in laptop hardware).
Its phase boundaries are hard stops: finish a phase, report, and wait for my measurements or
approval before starting the next one.

## Ground rules
- Read `README.md` and `GOTCHAS.md` before making changes. When you hit a non-obvious pitfall
  (driver/APO quirk, WASAPI/PortAudio behaviour, footgun in numpy/scipy/sounddevice), add an
  entry to `GOTCHAS.md` so it isn't rediscovered later.
- Match existing conventions exactly — don't introduce a "cleaner" structure, pattern, or
  abstraction for new code just because it seems better. If you think a break from convention
  is warranted, ask first instead of deciding unilaterally.
- Everything is in English. Physical quantities carry their unit in the identifier
  (`duration_s`, `f1_hz`, `level_dbfs`, `delay_samples`). Levels are relative dB / dBFS —
  nothing is calibrated, so never label anything SPL.
- Built-in hardware only (see `PROMPT.md`). If a step would need extra hardware, design a
  workaround with the built-in devices or say plainly that it cannot be done.
- Physics decides scope. Ground design choices in the primary sources listed in `PROMPT.md`
  and cite them in reports. Say so explicitly when the physics or the hardware says no.

## Module conventions
- All code lives in the `noisy/` package; one module per measurement concern (`devices`,
  `audit`, `sweep`, `latency`, `capture`, ...). Don't invent new top-level files without
  precedent.
- Pure DSP (signal generation, deconvolution, delay estimation, analysis) is kept separate from
  device I/O so it can be tested offline on synthetic signals. Device I/O goes through
  `noisy/capture.py` and `noisy/devices.py`.
- Every measurement is a subcommand of `python -m noisy` (`noisy/__main__.py`). It writes its
  audio to `data/` (gitignored) as WAV plus a JSON sidecar with mode, devices, sample rate,
  stream latency and timestamp, and prints a short summary.
- Reports go in `reports/phaseN-<topic>.md`, figures in `reports/figures/`. Each report states
  the numbers that drove decisions and the open risks.

## Task workflow
- Feature ideas start as raw entries in `IDEAS.md`.
- Before non-trivial work, check the `TASKS.md` index (unique IDs, status, area, link to a
  per-task briefing in `tasks/`) for whether it's already tracked. If not, promote it first:
  assign the next ID, write a briefing with context/open questions/proposed
  approach/acceptance criteria, add it to the index, and mark it back in `IDEAS.md`.
- Update task status as work starts (🔧 IN PROGRESS) and finishes (✅ DONE — code done, tested,
  changelog entry added). Keep the substantive detail in the task's own file; the index stays
  thin.

## Changelog
- After finishing a feature, add a `CHANGELOG.md` entry in the same change: a version/date
  heading with categorized sections (New feature / Bug fix / Enhancement / Ops), bullets in the
  existing `[module-name] short description` style.

## Mandatory delivery gate
- Treat the workflow as a strict sequence: idea in `IDEAS.md` -> approved task with unique ID
  and briefing in `TASKS.md` -> status `IN PROGRESS` -> implementation -> tests/validation ->
  `CHANGELOG.md` entry -> status `DONE`.
- Do not write code, notebooks, tests, or configuration for non-trivial work before the task
  and briefing exist and the task is marked `IN PROGRESS`.
- Treat `IDEAS.md` as a dated notebook: append ideas under `[YYYY-MM-DD]` as bullet points,
  investigate them first, record the recommendation, and only then promote approved ideas to
  tasks while recording the task link in the original bullet.
- Before handoff, verify that the task status, acceptance criteria, tests, changelog, and final
  diff all describe the same actual state.

## Tests
- Tests live in `tests/`, one file per module under test (`test_sweep.py`, `test_latency.py`,
  ...). They run offline on synthetic signals with known answers (known IR, known delay) —
  never require the audio hardware. Hardware checks are measurement subcommands, not tests.
- Run with `uv run pytest`.

## Lint/format
- Ruff (configured in `pyproject.toml`) is the source of style truth: `uv run ruff check` and
  `uv run ruff format`. Don't hand-format.

## Safety
- Never drive the speakers above the level cap or below the high-pass corner defined in the
  code; raw/exclusive mode bypasses the Realtek render APO (see `GOTCHAS.md`).
- Don't play audio on the speakers yourself without asking — measurements are run by me.

## General collaboration style
- For exploratory/opinion questions, give a short recommendation with the main tradeoff —
  don't implement until I agree.
- Don't add error handling, abstractions, or scope beyond what's asked. No speculative future-
  proofing.
- Confirm before destructive or hard-to-reverse actions (force-push, reset --hard, deleting
  branches/files, amending pushed commits) — a prior approval doesn't carry forward to new
  instances of the same action.
- Default to no code comments unless explaining non-obvious *why*.
