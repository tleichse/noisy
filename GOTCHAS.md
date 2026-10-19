# Gotchas

## Environment
- The system `python` is 3.9 with no project dependencies. Always use `uv run ...` (project
  Python 3.12 in `.venv`).
- The Windows console is cp1252: non-ASCII characters in argparse help or `print` raise
  `UnicodeEncodeError`. Keep CLI text ASCII (`->`, not `→`).
- Git Bash `sed -i` on patterns with non-ASCII characters (`—`, emoji) can **silently match
  nothing** and exit 0. Edit such files with a proper editor or Python, then check the change.
- `timeout` from Git Bash does not kill a Python process blocked inside an audio driver; check
  for leftovers with `Get-Process python` afterwards.

## Audio devices (ThinkPad 21F8)
- Shared-mode WASAPI capture reports **4 channels**; raw and exclusive report **2**. The 4-ch
  layout is the post-APO (Dolby) mix format, not 4 microphones. There are 2 physical mics.
- Capture only opens at **48 kHz**, in every mode. The mic's native exclusive-mode format is
  **16-bit** (`int16` is the only format accepted with `explicit_sample_format`); recording
  as float32 is lossless.
- A Dolby APO (`DOLBYAPO_FUSIONAPOSVC`) is on the capture endpoint and a Realtek APO on the
  render endpoint; "Audio enhancements" are not disabled. Raw mode is advertised on both
  endpoints (`RawProcessingSupported`).
- Raw/exclusive render bypasses the Realtek APO, which may include speaker EQ/protection. Keep
  stimulus levels low (cap −6 dBFS in `capture.to_speakers`, sweeps start at 100 Hz).
- `sounddevice.WasapiSettings` has no raw option. `noisy.devices.WasapiSettings` sets
  `PaWasapiStreamInfo.streamOption = eStreamOptionRaw` on the cffi struct directly.
- WDM-KS in PortAudio supports callback streams only ("Blocking API not supported yet").
- **The capture stack can wedge.** On 2026-10-18 a 1-s `record` in exclusive mode followed by
  one in WDM-KS mode left a process stuck in the driver: it couldn't be killed and every later
  stream open (any mode) hung. Which mode caused it is not yet isolated. After the Restart,
  `audit` opened and closed streams in every mode, WDM-KS included, without trouble. So
  opening a stream is not enough to wedge it; streaming audio is the suspect. Until the cause is isolated, run
  WASAPI modes first and WDM-KS last, one at a time. Recovery: **Restart** Windows (not Shut
  down, since Fast Startup keeps driver state). Restarting `Audiosrv` and then disabling and
  re-enabling "AMD Audio Device" did *not* work. It left "AMD Audio CoProcessor" in Code 43
  and the mic endpoint missing.
- Exclusive mode takes the device away from every other app (Teams, browser) while it runs.
- PortAudio device indices are not stable between processes. They shift when any audio device
  (Bluetooth headphones, dock, monitor audio) appears or disappears. On 2026-10-18 the WASAPI
  mic was index 12 in one process and index 9 a few minutes later. Always resolve by name in
  the same process (`devices.find_device`) and never paste an index from an earlier listing.
- **Shared-mode capture runs echo cancellation on the speaker signal.** In `rawcheck` on
  2026-10-18, a 1 kHz tone at -24 dBFS that reached -35 dBFS in raw capture came out at -133
  dBFS in shared mode. All 4 channels were bit-identical, with a flat -99.5 dBFS floor. Shared
  mode can't be used for any speaker-to-mic measurement.
- Shared-raw capture skips the Dolby APO but is **not bit-exact**. Its samples are not integer
  multiples of 1/32768, and the audio engine applies a gain (probably the endpoint capture
  volume). The gain holds steady within a run but **not between runs**: +6.6 dB and then
  +8.6 dB over exclusive, minutes apart, while exclusive repeated to 0.02 dB. Exclusive capture
  is exact int16.
- Raw and exclusive recordings start with **0.2 s of exact zeros** (stream pre-roll). After
  that, quiet passages contain many isolated exact zeros (11-14 % at a floor of ~4-8 LSB rms)
  because the 16-bit source rounds them to zero. Counting zeros does not detect gating; look
  for long runs of zeros instead.
