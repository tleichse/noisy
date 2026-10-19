# Ideas

## [2026-10-18]
- Phase 0 of `PROMPT.md` — device audit & measurement tooling (WASAPI enumeration, raw-mode
  proof, raw recording, Farina sweep IRs, round-trip latency).
  - Investigation: PortAudio enumeration + endpoint registry. The mic endpoint reports
    `RawProcessingSupported = true`; a Dolby APO is registered on capture and a Realtek APO on
    render; enhancements are not disabled. Shared mode exposes 4 capture channels, raw and
    exclusive expose 2. Capture only opens at 48 kHz. `sounddevice` lacks PortAudio's raw
    stream option but the struct field is reachable.
  - Recommendation: build the tooling in Python on `sounddevice`, comparing four capture modes
    (shared, shared-raw, exclusive, WDM-KS) so the raw-mode claim is proven by measurement, not
    assumed.
  - Promoted → [T-001](tasks/T-001-phase0-device-audit.md)
- Phase 1 of `PROMPT.md` — characterise ambient noise and the speaker→mic chain from my
  recordings. Depends on T-001 tooling and my measurements; promote when T-001 is done.
- Phase 2 of `PROMPT.md` — feasibility & GO/NO-GO per noise component. Promote after Phase 1.
- Phases 3–5 of `PROMPT.md` — offline FxLMS simulation, real-time loop, verification. Only
  promoted if Phase 2 says GO.
- Phase 5 verification flaw: the second bezel mic is ~2 cm from the error mic, inside the zone
  of quiet. It can show a real drop that never reaches the ears ~50 cm away (Elliott et al.
  1988). Only the ABX listening test measures the goal. Weigh this in Phase 2. If it's GO,
  consider moving the laptop closer to the head for the verification runs.
