# T-001 — Phase 0: device audit & measurement tooling

Status: ✅ DONE · Area: measurement · Source: `PROMPT.md` Phase 0

## Context
Every later phase depends on trustworthy raw signals from the built-in mic array and a known
speaker→mic chain. The AMD mic array sits behind a Dolby APO (capture) and the Realtek speakers
behind a Realtek APO (render); either could apply noise suppression, AGC, AEC or EQ that would
silently corrupt measurements and, later, the control loop.

Findings from the initial enumeration (2026-10-18, no audio played):
- WASAPI mic: 4 ch in shared mode, 2 ch in raw / exclusive → 2 physical mics; the shared 4-ch
  format is the post-APO mix format.
- Capture opens only at 48 kHz (shared, exclusive, WDM-KS). Render exclusive also allows
  44.1 / 96 kHz.
- `RawProcessingSupported = true` on the capture endpoint.
- WDM-KS exposes "Microphone Array 1" and "Microphone Array 2" (AMDAfdInstall), 2 ch each.

## Open questions
- Does raw / exclusive actually bypass all processing, or is there DSP in the AMD ACP firmware
  that no Windows mode can disable? Only the measurement (`rawcheck`) can answer this.
- Mic (AMD ACP) and speakers (Realtek HDA) are different devices — do they share a clock? Clock
  drift would make the secondary path delay wander, which matters for FxLMS. `ir` reports the
  per-repeat delay drift.
- Which WDM-KS pin ("Microphone Array 1" or "2") carries the mics? `rawcheck` uses pin 1.
- Native sample format (16/24/32-bit) in exclusive mode: probed by `audit`. Answer: mic
  16-bit, speakers 16/24-bit.
- Driver stability: the first exclusive + WDM-KS `record` smoke test left the capture driver
  wedged (unkillable process, all later opens hang). Which mode caused it isn't isolated yet.
  See `GOTCHAS.md`.

## Approach
- `noisy/devices.py`: find the devices by name/host API; four capture modes: `shared`,
  `shared-raw`, `exclusive` (WASAPI exclusive + raw), `wdmks`. Raw is set through PortAudio's
  `PaWasapiStreamInfo.streamOption`.
- `noisy/audit.py`: enumerate host APIs/devices, probe channel counts × formats per mode,
  native formats (explicit sample format, exclusive), minimum achievable stream latency, and
  endpoint registry state (APOs, enhancements disabled, raw supported).
- `noisy/sweep.py`: Farina exponential sine sweep, inverse filter, deconvolution (pure DSP).
- `noisy/latency.py`: GCC-PHAT delay estimate (pure DSP).
- `noisy/capture.py`: long multichannel recording to WAV; duplex play+record; play on one
  device while recording on another (for the raw-mode comparison).
- `noisy/__main__.py` subcommands: `audit`, `record`, `ir`, `latency`, `rawcheck`.
- Raw-mode proof (`rawcheck`): for each capture mode, play silence → steady 1 kHz tone →
  silence on the speakers (always through the same shared render path so only capture differs)
  and measure tone level, level drift over the tone (AGC/NS/AEC adapt over seconds), and the
  silence floor / longest run of exact zeros (gating). Pass = drift < 1 dB, no zero run
  >= 10 ms, and tone level not more than 3 dB below exclusive mode.
- Speaker safety: stimulus level capped at −6 dBFS, sweeps start at 100 Hz by default, fades
  on every stimulus.

## Findings — first `rawcheck` run (2026-10-18)
- shared: tone removed (-133 dBFS vs -35 in shared-raw), 4 identical channels, flat -99.5 dBFS
  floor → the Dolby APO cancels the speaker signal as echo and suppresses noise. Unusable.
- shared-raw: APO bypassed (tone stable to 0.16 dB) but not bit-exact; +6.6 dB static gain vs
  exclusive. A ~1.2 s, -47 dBFS event near 464 Hz after the tone, absent in exclusive.
- exclusive: exact int16. Tone level rose ~3.5 dB over the first 4 s (max deviation 1.5 dB),
  unexplained.
- The first verdict logic was wrong. Exact zeros come from 16-bit rounding, not gating, and
  using the loudest mode as the reference penalised exclusive for shared-raw's extra gain. Both
  are fixed in 0.1.1. A repeat run of `shared-raw exclusive` is needed.

## Findings — repeat `rawcheck --modes shared-raw exclusive` (2026-10-18, 0.1.1 logic)
- Both modes pass: max deviation <= 0.37 dB, longest zero run <= 0.17 ms, no xruns.
- exclusive: tone -41.9 / -41.1 dBFS, matching the first run to 0.02 dB. Max deviation 0.15
  dB, floor -81.9 / -81.0 dBFS both before and after the tone, exact int16. The first run's
  drift did not recur.
- shared-raw: +8.6 dB vs exclusive this time (+6.6 dB in the first run). The 464 Hz event
  after the tone did not recur, so it was probably a sound in the room.
- **Decision: exclusive (WASAPI exclusive + raw) is the capture path for all later work.** It
  is bit-exact and repeatable. Shared-raw has no adaptive processing within a run, but its
  gain changes between runs.

## Acceptance criteria
- [x] `audit` enumerates devices via WASAPI with channel counts, supported formats, minimum
      latency, exclusive-mode support and endpoint enhancement state.
- [x] `record` writes raw multichannel 48 kHz float WAV + JSON sidecar in any capture mode.
- [x] `ir` plays exponential sweeps and deconvolves speaker→each-mic IRs (Farina), reporting
      per-repeat delay and clock drift.
- [x] `latency` measures round-trip latency by cross-correlation in shared and exclusive mode.
- [x] Offline tests recover a known IR and a known delay from synthetic signals.
- [x] Step-by-step measurement instructions incl. laptop placement (`reports/phase0-device-audit.md`).
- [x] `rawcheck` run on the hardware proves which mode is unprocessed: exclusive.
- [x] `ir` and `latency` results from the hardware recorded in the Phase 0 report
      (exclusive mode, §2 of `reports/phase0-device-audit.md`).
