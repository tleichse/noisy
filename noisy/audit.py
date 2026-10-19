"""Device audit: what the built-in endpoints expose in each mode. Plays nothing."""

import winreg

import sounddevice as sd

from noisy.devices import MODES, SAMPLE_RATE_HZ, WasapiSettings, endpoints

SAMPLE_RATES_HZ = (16000, 44100, 48000, 96000)
DTYPES = ("int16", "int24", "int32", "float32")
CHANNELS = (1, 2, 4)

_MMDEVICES = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio"
_PKEY_DEVICE_DESC = "{a45c254e-df1c-4efd-8020-67d146a850e0},2"
_PKEY_DEVICE_INTERFACE = "{b3f8fa53-0004-438e-9003-51a46e139bfc},6"
_PKEY_RAW_SUPPORTED = "{8943b373-388c-4395-b557-bc6dbaffafdb},2"
_PKEY_DISABLE_SYSFX = "{1da5d803-d492-4edd-8c23-e0c0ffee7f0e},5"
_DEVICE_STATE_ACTIVE = 1


def _check(kind, **kwargs):
    check = sd.check_input_settings if kind == "input" else sd.check_output_settings
    try:
        check(**kwargs)
        return True
    except sd.PortAudioError:
        return False


def supported_formats(device, kind, settings):
    """(channels, sample_rate_hz, dtype) combinations PortAudio accepts for the device."""
    return [
        {"channels": ch, "sample_rate_hz": sr, "dtype": dt}
        for ch in CHANNELS
        for sr in SAMPLE_RATES_HZ
        for dt in DTYPES
        if _check(
            kind,
            device=device,
            channels=ch,
            samplerate=sr,
            dtype=dt,
            extra_settings=settings,
        )
    ]


def native_formats(device, kind):
    """Sample formats the hardware takes directly in exclusive mode (no PortAudio conversion)."""
    return [
        dt
        for dt in DTYPES
        if _check(
            kind,
            device=device,
            channels=2,
            samplerate=SAMPLE_RATE_HZ,
            dtype=dt,
            extra_settings=WasapiSettings(raw=True, exclusive=True, explicit_sample_format=True),
        )
    ]


def minimum_latency_s(ep, kind):
    """Smallest stream latency PortAudio reports when asked for (almost) zero."""
    stream_class = sd.InputStream if kind == "input" else sd.OutputStream
    device = ep.mic if kind == "input" else ep.speaker
    settings = ep.mic_settings if kind == "input" else ep.speaker_settings
    channels = ep.mic_channels if kind == "input" else ep.speaker_channels
    try:
        with stream_class(
            samplerate=SAMPLE_RATE_HZ,
            device=device,
            channels=channels,
            dtype="float32",
            latency=0.0001,
            extra_settings=settings,
            # WDM-KS only supports callback streams.
            callback=lambda *args: None,
        ) as stream:
            return stream.latency
    except sd.PortAudioError as error:
        return str(error)


def _values(key):
    values = {}
    index = 0
    while True:
        try:
            name, value, _ = winreg.EnumValue(key, index)
        except OSError:
            return values
        values[name] = value
        index += 1


def endpoint_registry(flow, description):
    """Enhancement/APO state of the active endpoint, e.g. ("Capture", "Microphone Array")."""
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"{_MMDEVICES}\{flow}") as root:
        index = 0
        while True:
            try:
                guid = winreg.EnumKey(root, index)
            except OSError:
                return None
            index += 1
            with winreg.OpenKey(root, guid) as endpoint:
                state = _values(endpoint).get("DeviceState")
                with winreg.OpenKey(endpoint, "Properties") as props_key:
                    props = _values(props_key)
                try:
                    with winreg.OpenKey(endpoint, "FxProperties") as fx_key:
                        fx = _values(fx_key)
                except OSError:
                    fx = {}
            if state != _DEVICE_STATE_ACTIVE or props.get(_PKEY_DEVICE_DESC) != description:
                continue
            raw = props.get(_PKEY_RAW_SUPPORTED)
            return {
                "endpoint_guid": guid,
                "description": description,
                "interface": props.get(_PKEY_DEVICE_INTERFACE),
                # VT_BOOL blob: bytes 8..9 are 0xFFFF for true.
                "raw_processing_supported": None if raw is None else raw[8:10] == b"\xff\xff",
                "enhancements_disabled": fx.get(_PKEY_DISABLE_SYSFX) == 1,
                "apo_drivers": sorted(
                    {v for v in fx.values() if isinstance(v, str) and "APO" in v.upper()}
                ),
            }


def audit():
    hostapis = [h["name"] for h in sd.query_hostapis()]
    devices = [
        {
            "index": i,
            "hostapi": hostapis[d["hostapi"]],
            "name": d["name"],
            "max_input_channels": d["max_input_channels"],
            "max_output_channels": d["max_output_channels"],
            "default_samplerate": d["default_samplerate"],
        }
        for i, d in enumerate(sd.query_devices())
    ]
    modes = {}
    for mode in MODES:
        ep = endpoints(mode)
        modes[mode] = {
            "mic": sd.query_devices(ep.mic)["name"],
            "speaker": sd.query_devices(ep.speaker)["name"],
            "mic_formats": supported_formats(ep.mic, "input", ep.mic_settings),
            "speaker_formats": supported_formats(ep.speaker, "output", ep.speaker_settings),
            "mic_min_latency_s": minimum_latency_s(ep, "input"),
            "speaker_min_latency_s": minimum_latency_s(ep, "output"),
        }
    exclusive = endpoints("exclusive")
    return {
        "hostapis": hostapis,
        "devices": devices,
        "modes": modes,
        "native_formats_exclusive": {
            "mic": native_formats(exclusive.mic, "input"),
            "speaker": native_formats(exclusive.speaker, "output"),
        },
        "registry": {
            "capture": endpoint_registry("Capture", "Microphone Array"),
            "render": endpoint_registry("Render", "Speakers"),
        },
    }
