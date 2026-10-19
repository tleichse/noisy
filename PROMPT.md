ROLE
You are an acoustics / active-noise-control engineer. Treat this as an engineering
feasibility study followed by a narrowly scoped implementation, not as "build an
ANC app." Physics and measurement decide the scope; do not write a real-time
controller until Phase 2 says GO.

GOAL
Reduce the ambient noise I hear at my desk using ONLY my laptop's built-in
microphones and speakers. Success metric (to be refined after Phase 1): a
measurable, repeatable reduction (target ≥6 dB) in the dominant noise component
that the built-in speakers can actually reproduce, at the position where I sit,
with no audible artefacts added.

HARD CONSTRAINT — BUILT-IN HARDWARE ONLY
- Machine: Lenovo ThinkPad, model 21F8 (AMD), Windows 11.
  Input: "Microphone Array (AMD Audio Device)". Output: "Speakers (Realtek(R) Audio)".
- No purchases, no external mics, speakers, audio interfaces, headsets or phones.
  Every measurement, reference, error and verification signal must come from
  these devices. If a step normally needs extra hardware, design a workaround
  with the built-in devices or state plainly that it cannot be done.
- Expect and quantify these limits early: laptop speakers produce little below
  ~150–200 Hz; the mics sit a few cm from the speakers and from each other
  (strong acoustic feedback, little spatial separation); the AMD mic array may
  apply built-in beamforming/noise suppression/AEC; nothing is calibrated, so
  all levels are relative dB (dBFS), not absolute SPL.

OTHER CONSTRAINTS / CONTEXT
- Working repo: ./ . Python for analysis/simulation; C++ (PortAudio/JUCE) or
  Rust for the real-time loop, WASAPI exclusive mode (or ASIO4ALL if it helps).
- Do NOT use speech-denoising libraries (RNNoise, etc.); they clean recordings,
  they don't cancel sound in air.
- Ground every design choice in primary sources (Kuo & Morgan 1996; Nelson &
  Elliott; Elliott "Signal Processing for Active Control"; Hansen et al.), cited.

PHASE 0 — Device audit & measurement tooling
- Enumerate devices via WASAPI: channel counts, supported formats, minimum
  period, exclusive-mode support. Determine whether the array exposes separate
  raw mic channels and how to disable audio enhancements / AMD processing
  (Windows "Audio enhancements", raw mode / AUDIO_SIGNALPROCESSINGMODE_RAW).
  Prove it with a test (e.g. a sweep is not suppressed or gated).
- Scripts to: (a) record raw multichannel PCM (48 kHz, highest bit depth),
  (b) play exponential sine sweeps on the built-in speakers and deconvolve
  speaker→each-mic impulse responses (Farina), (c) measure round-trip latency
  by loopback cross-correlation in shared and exclusive mode.
- Step-by-step instructions for me, including laptop placement relative to my
  head and the noise source.

PHASE 1 — Characterise the raw material (from my recordings, not assumptions)
- Welch PSD, spectrogram, 1/3-octave levels (relative dB, A/C-weighted shape)
  across a working day. Identify tonal vs broadband components and their
  stability over time.
- Speaker→mic frequency response (what the speakers can reproduce, and how
  loud before distortion), full-chain latency, coherence γ²(f) between the
  two mic channels.
Deliverable: report with plots and a table of noise components by band.

PHASE 2 — Feasibility & GO/NO-GO
For each noise component compute: (1) the coherence bound on attenuation,
−10·log10(1−γ²); (2) causality margin vs measured latency (feedforward is
almost certainly infeasible with co-located mics; say so with numbers);
(3) zone-of-quiet size (~λ/10) and whether it can reach my ears from the laptop
position; (4) whether the built-in speakers can reproduce it at the needed level.
Classify each component: tonal-only (narrowband with synthesized reference),
feedforward-feasible, or infeasible. Compare against built-in-hardware
alternatives (e.g. generated sound masking through the same speakers). Give an
explicit GO/NO-GO with numbers. If NO-GO, stop and recommend the best option
that still uses only this laptop.

PHASE 3 — Offline simulation
Using measured impulse responses and recorded noise, simulate in Python:
narrowband/adaptive-notch FxLMS for tonal components, leaky normalized FxLMS
for broadband if feasible, with secondary-path estimation (offline + online,
Eriksson method). Report convergence, steady-state attenuation per band, and
sensitivity to a 10% secondary-path error and to me moving ±10 cm.

PHASE 4 — Real-time implementation
Low-latency loop (exclusive mode), fixed block size, end-to-end latency
logged at startup. Safety is mandatory: output limiter, speaker-protection
high-pass (no driving the tiny drivers below their usable range), howling /
divergence detector with auto-mute, hard mute hotkey, output level cap.
Config file for target frequencies and gains.

PHASE 5 — Verification (built-in hardware only)
- Use one mic channel as the controller's error mic and the other ONLY for
  verification, never fed to the controller. If only one channel is available,
  alternate controller-off/on and verify with the same mic, and state that weakness.
- Alternate OFF/ON/OFF/ON, ≥60 s each, on a stable noise source (e.g. HVAC
  tone); per-band relative-dB table and spectra overlay.
- Check measured attenuation ≤ coherence bound (if it exceeds the bound, the
  measurement is wrong; investigate).
- Blind ABX protocol: the software randomly toggles the controller, I guess the
  state, and it logs hit rate with a binomial p-value.
- Same metrics for the masking alternative.

OUTPUT EACH PHASE
Code in repo, a short markdown report with plots in /reports, the numbers that
drove decisions, and the open risks. Stop at each phase boundary and wait for my
measurements or approval. Be explicit when the physics or the hardware says no.
