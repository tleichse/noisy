# Changelog

## 0.1.1 — 2026-10-18

### Bug fix
- [rawcheck] Gating check uses the longest run of exact zeros (`--max-zero-run-ms`, default 10)
  instead of the zero fraction, which quantised 16-bit silence always failed.
- [rawcheck] Suppression is measured against exclusive mode (bit-exact driver path) instead of
  the loudest mode; the gain vs exclusive is reported per mode.

## 0.1.0 — 2026-10-18

### New feature
- [devices] Capture modes `shared`, `shared-raw`, `exclusive`, `wdmks` for the built-in mic
  array and speakers, including WASAPI raw stream option.
- [audit] Device audit: host APIs, channel counts × formats per mode, native exclusive formats,
  minimum stream latency, endpoint APO/enhancement/raw-support state from the registry.
- [capture] Streaming multichannel float WAV recording; duplex play+record; play on the shared
  render path while recording in any capture mode.
- [sweep] Farina exponential sine sweep, inverse filter and deconvolution.
- [latency] GCC-PHAT delay estimation and band-limited noise bursts.
- [cli] `python -m noisy audit | record | ir | latency | rawcheck`, each writing WAV/JSON to
  `data/`.

### Ops
- [project] uv project (Python 3.12), ruff, pytest; working-style docs (`CLAUDE.md`,
  `IDEAS.md`, `TASKS.md`, `GOTCHAS.md`).
