"""Device I/O: long recordings, duplex play+record, play on one path while recording another."""

import queue
import threading

import numpy as np
import sounddevice as sd
import soundfile as sf

from noisy.devices import SAMPLE_RATE_HZ

MAX_LEVEL_DBFS = -6.0
SPEAKERS = {"both": (0, 1), "left": (0,), "right": (1,)}


def to_speakers(mono, level_dbfs, speaker="both", channels=2):
    if level_dbfs > MAX_LEVEL_DBFS:
        raise ValueError(f"level {level_dbfs} dBFS exceeds the {MAX_LEVEL_DBFS} dBFS cap")
    out = np.zeros((len(mono), channels), dtype=np.float32)
    for channel in SPEAKERS[speaker]:
        out[:, channel] = mono * 10 ** (level_dbfs / 20)
    return out


def record_to_file(ep, duration_s, path):
    """Stream the mic to a float WAV; Ctrl+C stops early and keeps what was recorded."""
    blocks = queue.Queue()
    total = round(duration_s * SAMPLE_RATE_HZ)
    status_flags = []

    def callback(indata, frames, time, status):
        if status:
            status_flags.append(str(status))
        blocks.put(indata.copy())

    written = 0
    with (
        sf.SoundFile(path, "w", SAMPLE_RATE_HZ, ep.mic_channels, subtype="FLOAT") as wav,
        sd.InputStream(
            samplerate=SAMPLE_RATE_HZ,
            device=ep.mic,
            channels=ep.mic_channels,
            dtype="float32",
            extra_settings=ep.mic_settings,
            callback=callback,
        ) as stream,
    ):
        latency_s = stream.latency
        try:
            while written < total:
                block = blocks.get(timeout=2.0)[: total - written]
                wav.write(block)
                written += len(block)
        except KeyboardInterrupt:
            pass
    return {"frames": written, "stream_latency_s": latency_s, "xruns": status_flags}


def playrec(ep, stimulus):
    """Play and record on one duplex stream, so both share the stream's sample timeline."""
    status_flags = []
    recording = np.zeros((len(stimulus), ep.mic_channels), dtype=np.float32)
    position = 0
    finished = threading.Event()

    def callback(indata, outdata, frames, time, status):
        nonlocal position
        if status:
            status_flags.append(str(status))
        chunk = stimulus[position : position + frames]
        outdata[: len(chunk)] = chunk
        outdata[len(chunk) :] = 0
        recording[position : position + len(chunk)] = indata[: len(chunk)]
        position += frames
        if position >= len(stimulus):
            raise sd.CallbackStop

    with sd.Stream(
        samplerate=SAMPLE_RATE_HZ,
        device=(ep.mic, ep.speaker),
        channels=(ep.mic_channels, stimulus.shape[1]),
        dtype="float32",
        extra_settings=(ep.mic_settings, ep.speaker_settings),
        callback=callback,
        finished_callback=finished.set,
    ) as stream:
        latency_s = stream.latency
        finished.wait()
    return recording, {"stream_latency_s": latency_s, "xruns": status_flags}


def play_while_recording(ep, speaker, speaker_settings, stimulus):
    """Play on `speaker` and record on `ep.mic` with two independent streams.

    The two streams are not sample-aligned; use only for level measurements.
    """
    status_flags = []
    recording = np.zeros((len(stimulus), ep.mic_channels), dtype=np.float32)
    recorded = 0
    played = 0
    finished = threading.Event()

    def input_callback(indata, frames, time, status):
        nonlocal recorded
        if status:
            status_flags.append(f"in: {status}")
        chunk = indata[: len(recording) - recorded]
        recording[recorded : recorded + len(chunk)] = chunk
        recorded += len(chunk)
        if recorded >= len(recording):
            finished.set()

    def output_callback(outdata, frames, time, status):
        nonlocal played
        if status:
            status_flags.append(f"out: {status}")
        chunk = stimulus[played : played + frames]
        outdata[: len(chunk)] = chunk
        outdata[len(chunk) :] = 0
        played += frames

    with (
        sd.InputStream(
            samplerate=SAMPLE_RATE_HZ,
            device=ep.mic,
            channels=ep.mic_channels,
            dtype="float32",
            extra_settings=ep.mic_settings,
            callback=input_callback,
        ) as input_stream,
        sd.OutputStream(
            samplerate=SAMPLE_RATE_HZ,
            device=speaker,
            channels=stimulus.shape[1],
            dtype="float32",
            extra_settings=speaker_settings,
            callback=output_callback,
        ),
    ):
        latency_s = input_stream.latency
        finished.wait()
    return recording, {"stream_latency_s": latency_s, "xruns": status_flags}
