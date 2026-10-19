"""Locate the built-in devices and build stream settings for each capture mode."""

from dataclasses import dataclass

import sounddevice as sd

SAMPLE_RATE_HZ = 48000

WASAPI = "Windows WASAPI"
WDMKS = "Windows WDM-KS"
MIC_NAME = "Microphone Array (AMD Audio Device)"
SPEAKER_NAME = "Speakers (Realtek(R) Audio)"
WDMKS_MIC_NAME = "Microphone Array 1 (AMDAfdInstall Wave Microphone"
WDMKS_SPEAKER_NAME = "Speakers 1 (Realtek HD Audio output"

MODES = ("shared", "shared-raw", "exclusive", "wdmks")

# PaWasapiStreamOption.eStreamOptionRaw in pa_win_wasapi.h
_STREAM_OPTION_RAW = 1


class WasapiSettings(sd.WasapiSettings):
    """sounddevice.WasapiSettings plus PortAudio's raw stream option, which it lacks."""

    def __init__(self, raw=False, **kwargs):
        super().__init__(**kwargs)
        self.raw = raw
        self.exclusive = kwargs.get("exclusive", False)
        if raw:
            self._streaminfo.streamOption = _STREAM_OPTION_RAW


@dataclass(frozen=True)
class Endpoints:
    mode: str
    mic: int
    speaker: int
    mic_settings: WasapiSettings | None
    speaker_settings: WasapiSettings | None
    mic_channels: int
    speaker_channels: int = 2


def find_device(name, hostapi, kind):
    api = next(i for i, h in enumerate(sd.query_hostapis()) if h["name"] == hostapi)
    for index in sd.query_hostapis(api)["devices"]:
        device = sd.query_devices(index)
        if device["name"].startswith(name) and device[f"max_{kind}_channels"] > 0:
            return index
    raise LookupError(f"no {kind} device starting with {name!r} on {hostapi}")


def endpoints(mode):
    if mode == "wdmks":
        return Endpoints(
            mode,
            find_device(WDMKS_MIC_NAME, WDMKS, "input"),
            find_device(WDMKS_SPEAKER_NAME, WDMKS, "output"),
            None,
            None,
            mic_channels=2,
        )
    mic = find_device(MIC_NAME, WASAPI, "input")
    speaker = find_device(SPEAKER_NAME, WASAPI, "output")
    if mode == "shared":
        # Shared mode delivers the post-APO mix format (4 ch); raw and exclusive deliver the 2 mics.
        return Endpoints(mode, mic, speaker, WasapiSettings(), WasapiSettings(), mic_channels=4)
    if mode == "shared-raw":
        return Endpoints(
            mode, mic, speaker, WasapiSettings(raw=True), WasapiSettings(raw=True), mic_channels=2
        )
    if mode == "exclusive":
        return Endpoints(
            mode,
            mic,
            speaker,
            WasapiSettings(raw=True, exclusive=True),
            WasapiSettings(raw=True, exclusive=True),
            mic_channels=2,
        )
    raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")


def reference_speaker():
    """The shared-mode render path, used when only the capture side should vary between runs."""
    return find_device(SPEAKER_NAME, WASAPI, "output"), WasapiSettings()


def describe(ep):
    return {
        "mode": ep.mode,
        "mic": sd.query_devices(ep.mic)["name"],
        "speaker": sd.query_devices(ep.speaker)["name"],
        "mic_channels": ep.mic_channels,
        "raw": bool(ep.mic_settings and ep.mic_settings.raw),
        "exclusive": bool(ep.mic_settings and ep.mic_settings.exclusive),
    }
