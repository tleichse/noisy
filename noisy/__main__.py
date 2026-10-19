"""Measurement commands. Run `uv run python -m noisy <command> --help`."""

import argparse
import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

from noisy import audit, capture, latency, rawcheck, sweep  # noqa: E402
from noisy.devices import MODES, SAMPLE_RATE_HZ, describe, endpoints, reference_speaker  # noqa: E402

DATA_DIR = Path("data")
FS = SAMPLE_RATE_HZ


def _stem(kind, mode, label):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    DATA_DIR.mkdir(exist_ok=True)
    return DATA_DIR / "-".join(filter(None, [kind, stamp, mode, label]))


def _write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"wrote {path}")


def _sidecar(args, ep, **extra):
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "command": args.command,
        "args": {k: v for k, v in vars(args).items() if k != "func"},
        "sample_rate_hz": FS,
        "endpoints": describe(ep),
        **extra,
    }


def _dbfs(x):
    return 20 * np.log10(np.maximum(x, 1e-12))


def cmd_audit(args):
    result = audit.audit()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out, result)
    for mode, info in result["modes"].items():
        channels = sorted({f["channels"] for f in info["mic_formats"]})
        rates = sorted({f["sample_rate_hz"] for f in info["mic_formats"]})
        print(
            f"{mode:11s} mic ch {channels} @ {rates} Hz, "
            f"min latency in {info['mic_min_latency_s']} s / out {info['speaker_min_latency_s']} s"
        )
    print("native formats (exclusive):", result["native_formats_exclusive"])
    for flow, reg in result["registry"].items():
        print(flow, reg)


def cmd_record(args):
    ep = endpoints(args.mode)
    stem = _stem("rec", args.mode, args.label)
    print(f"recording {args.seconds} s from {describe(ep)['mic']} ({args.mode}); Ctrl+C stops")
    info = capture.record_to_file(ep, args.seconds, stem.with_suffix(".wav"))
    print(f"wrote {stem.with_suffix('.wav')} ({info['frames'] / FS:.1f} s)")
    _write_json(stem.with_suffix(".json"), _sidecar(args, ep, **info))


def _peak_index(ir):
    """Sub-sample peak of the channel-summed envelope (parabolic interpolation)."""
    envelope = np.abs(ir).sum(axis=1)
    i = int(np.argmax(envelope))
    if 0 < i < len(envelope) - 1:
        a, b, c = envelope[i - 1 : i + 2]
        return i + 0.5 * (a - c) / (a - 2 * b + c)
    return float(i)


def cmd_ir(args):
    ep = endpoints(args.mode)
    sweep_signal = sweep.exponential_sweep(args.f1_hz, args.f2_hz, args.sweep_s, FS)
    inverse = sweep.inverse_filter(sweep_signal, args.f1_hz, args.f2_hz, args.sweep_s, FS)
    lead = np.zeros(round(0.5 * FS))
    gap = np.zeros(round(args.gap_s * FS))
    period = len(sweep_signal) + len(gap)
    mono = np.concatenate([lead] + [sweep_signal, gap] * args.repeats)
    stimulus = capture.to_speakers(mono, args.level_dbfs, args.speaker, ep.speaker_channels)

    recording, info = capture.playrec(ep, stimulus)

    irs = []
    for r in range(args.repeats):
        start = len(lead) + r * period
        irs.append(sweep.deconvolve(recording[start : start + period], inverse, len(gap)))
    peaks = np.array([_peak_index(ir) for ir in irs])
    times_s = (len(lead) + np.arange(args.repeats) * period) / FS
    drift_ppm = float(np.polyfit(times_s, peaks / FS, 1)[0] * 1e6) if args.repeats > 1 else None
    shifts = np.round(peaks - peaks[0]).astype(int)
    averaged = np.mean([np.roll(ir, -s, axis=0) for ir, s in zip(irs, shifts, strict=True)], axis=0)

    tail = averaged[-len(averaged) // 10 :]
    peak = np.abs(averaged).max(axis=0)
    snr_db = _dbfs(peak) - _dbfs(np.sqrt(np.mean(tail**2, axis=0)))
    stem = _stem("ir", args.mode, args.label)
    sf.write(stem.with_suffix(".wav"), averaged.astype(np.float32), FS, subtype="FLOAT")
    _plot_ir(averaged, peaks[0], stem.with_suffix(".png"), args)
    result = {
        "delay_per_repeat_samples": peaks.tolist(),
        "delay_ms": float(peaks[0] / FS * 1e3),
        "clock_drift_ppm": drift_ppm,
        "peak_to_tail_db_per_channel": snr_db.tolist(),
        **info,
    }
    _write_json(stem.with_suffix(".json"), _sidecar(args, ep, **result))
    print(
        f"IR delay {result['delay_ms']:.2f} ms, drift {drift_ppm} ppm, "
        f"peak-to-tail {np.round(snr_db, 1).tolist()} dB, xruns {len(info['xruns'])}"
    )


def _plot_ir(ir, peak, path, args):
    fig, (ax_t, ax_f) = plt.subplots(2, 1, figsize=(9, 7))
    t_ms = np.arange(len(ir)) / FS * 1e3
    window = slice(max(0, int(peak) - FS // 1000), int(peak) + 20 * FS // 1000)
    f_hz = np.fft.rfftfreq(len(ir), 1 / FS)
    for ch in range(ir.shape[1]):
        ax_t.plot(t_ms[window], ir[window, ch], lw=0.8, label=f"mic {ch}")
        ax_f.semilogx(
            f_hz[1:], _dbfs(np.abs(np.fft.rfft(ir[:, ch])))[1:], lw=0.8, label=f"mic {ch}"
        )
    ax_t.set(xlabel="time (ms)", ylabel="amplitude", title=f"speaker→mic IR ({args.mode})")
    ax_f.set(xlabel="frequency (Hz)", ylabel="relative dB", xlim=(args.f1_hz, args.f2_hz))
    for ax in (ax_t, ax_f):
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


def cmd_latency(args):
    ep = endpoints(args.mode)
    burst = latency.noise_burst(args.burst_s, FS)
    gap = np.zeros(round(args.gap_s * FS))
    lead = np.zeros(round(0.5 * FS))
    period = len(burst) + len(gap)
    mono = np.concatenate([lead] + [burst, gap] * args.repeats)
    stimulus = capture.to_speakers(mono, args.level_dbfs, "both", ep.speaker_channels)

    recording, info = capture.playrec(ep, stimulus)

    delays = []
    ratios = []
    for r in range(args.repeats):
        start = len(lead) + r * period
        segment = recording[start : start + period]
        per_channel = [
            latency.gcc_phat_delay(burst, segment[:, ch], len(gap) - 1)
            for ch in range(ep.mic_channels)
        ]
        delays.append([d for d, _ in per_channel])
        ratios.append([q for _, q in per_channel])
    delays = np.array(delays)
    result = {
        "delay_samples": delays.tolist(),
        "peak_to_median": np.array(ratios).tolist(),
        "round_trip_ms_median": float(np.median(delays) / FS * 1e3),
        "round_trip_ms_spread": float(np.ptp(delays) / FS * 1e3),
        **info,
    }
    stem = _stem("latency", args.mode, args.label)
    _write_json(stem.with_suffix(".json"), _sidecar(args, ep, **result))
    print(
        f"{args.mode}: round trip {result['round_trip_ms_median']:.2f} ms "
        f"(spread {result['round_trip_ms_spread']:.2f} ms), PortAudio reports "
        f"{info['stream_latency_s']} s, xruns {len(info['xruns'])}"
    )


def _tone_level_dbfs(block, tone_hz):
    window = np.hanning(len(block))
    spectrum = np.fft.rfft(block * window[:, None], axis=0)
    bin_index = round(tone_hz * len(block) / FS)
    return _dbfs(2 * np.abs(spectrum[bin_index]) / window.sum())


def cmd_rawcheck(args):
    """Same tone through the same render path, recorded in each capture mode.

    AGC / noise suppression / AEC show up as tone-level drift or suppression relative to exclusive
    mode; gating shows up as a long run of exact zeros or a silence floor that drops after the
    tone.
    """
    speaker, speaker_settings = reference_speaker()
    t_s = np.arange(round(args.tone_s * FS)) / FS
    tone = np.sin(2 * np.pi * args.tone_hz * t_s) * sweep.fade(len(t_s), round(0.05 * FS))
    silence = np.zeros(round(2.0 * FS))
    mono = np.concatenate([silence, tone, silence])
    stimulus = capture.to_speakers(mono, args.level_dbfs, "both", 2)
    # The streams are unaligned by up to ~100 ms; analysis windows keep clear margins.
    lead = slice(round(0.3 * FS), round(1.5 * FS))
    tail = slice(len(mono) - round(1.5 * FS), len(mono) - round(0.3 * FS))
    tone_start = len(silence) + FS // 2
    tone_blocks = [
        slice(tone_start + i * FS, tone_start + (i + 1) * FS) for i in range(int(args.tone_s) - 1)
    ]

    results = {}
    for mode in args.modes:
        ep = endpoints(mode)
        print(f"{mode}: playing {args.tone_s + 4:.0f} s ...")
        recording, info = capture.play_while_recording(ep, speaker, speaker_settings, stimulus)
        levels = np.array([_tone_level_dbfs(recording[b], args.tone_hz) for b in tone_blocks])
        zero_run_samples = np.maximum(
            rawcheck.longest_zero_run_samples(recording[lead]),
            rawcheck.longest_zero_run_samples(recording[tail]),
        )
        results[mode] = {
            "endpoints": describe(ep),
            "tone_level_dbfs": levels.mean(axis=0).tolist(),
            "tone_drift_db": (levels[-1] - levels[0]).tolist(),
            "tone_max_deviation_db": np.abs(levels - levels.mean(axis=0)).max(axis=0).tolist(),
            "floor_lead_dbfs": _dbfs(np.sqrt(np.mean(recording[lead] ** 2, axis=0))).tolist(),
            "floor_tail_dbfs": _dbfs(np.sqrt(np.mean(recording[tail] ** 2, axis=0))).tolist(),
            "longest_zero_run_ms": (zero_run_samples * 1000 / FS).tolist(),
            **info,
        }
        stem = _stem("rawcheck", mode, args.label)
        sf.write(stem.with_suffix(".wav"), recording, FS, subtype="FLOAT")

    # Exclusive is the bit-exact driver path; other modes may add a static engine gain.
    mics = slice(0, 2)
    reference = results.get("exclusive")
    print(
        f"\n{'mode':11s} {'tone dBFS':>18s} {'drift dB':>14s} "
        f"{'floor lead/tail dBFS':>26s} {'vs excl dB':>10s}  verdict"
    )
    for mode, r in results.items():
        gain_db = None
        if reference is not None:
            gain_db = float(
                np.mean(r["tone_level_dbfs"][mics]) - np.mean(reference["tone_level_dbfs"][mics])
            )
        r["gain_vs_exclusive_db"] = gain_db
        unprocessed = (
            max(np.abs(r["tone_max_deviation_db"][mics])) < args.max_drift_db
            and max(r["longest_zero_run_ms"][mics]) < args.max_zero_run_ms
            and (gain_db is None or gain_db > -args.max_suppression_db)
        )
        r["looks_unprocessed"] = bool(unprocessed)
        gain_text = "-" if gain_db is None else f"{gain_db:+.1f}"
        print(
            f"{mode:11s} {np.round(r['tone_level_dbfs'], 1)!s:>18s} "
            f"{np.round(r['tone_drift_db'], 2)!s:>14s} "
            f"{np.round(r['floor_lead_dbfs'], 1)!s:>12s}/"
            f"{np.round(r['floor_tail_dbfs'], 1)!s:<13s} {gain_text:>10s}  "
            f"{'unprocessed' if unprocessed else 'PROCESSED?'}"
        )
    stem = _stem("rawcheck", "all", args.label)
    _write_json(
        stem.with_suffix(".json"),
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "args": {k: v for k, v in vars(args).items() if k != "func"},
            "modes": results,
        },
    )


def main():
    parser = argparse.ArgumentParser(prog="noisy")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("audit", help="enumerate devices, formats, latency, enhancement state")
    p.add_argument("--out", default="reports/data/audit.json")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("record", help="record the raw mics to WAV")
    p.add_argument("--mode", choices=MODES, default="exclusive")
    p.add_argument("--seconds", type=float, default=600)
    p.add_argument("--label", default="")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("ir", help="speaker-to-mic impulse responses by exponential sweep")
    p.add_argument("--mode", choices=MODES, default="exclusive")
    p.add_argument("--repeats", type=int, default=4)
    p.add_argument("--level-dbfs", type=float, default=-18)
    p.add_argument("--f1-hz", type=float, default=100)
    p.add_argument("--f2-hz", type=float, default=20000)
    p.add_argument("--sweep-s", type=float, default=3)
    p.add_argument("--gap-s", type=float, default=1.5)
    p.add_argument("--speaker", choices=capture.SPEAKERS, default="both")
    p.add_argument("--label", default="")
    p.set_defaults(func=cmd_ir)

    p = sub.add_parser("latency", help="round-trip latency by GCC-PHAT on noise bursts")
    p.add_argument("--mode", choices=MODES, default="exclusive")
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--level-dbfs", type=float, default=-18)
    p.add_argument("--burst-s", type=float, default=0.5)
    p.add_argument("--gap-s", type=float, default=0.5)
    p.add_argument("--label", default="")
    p.set_defaults(func=cmd_latency)

    p = sub.add_parser("rawcheck", help="prove which capture mode is unprocessed")
    p.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    p.add_argument("--tone-hz", type=float, default=1000)
    p.add_argument("--tone-s", type=float, default=8)
    p.add_argument("--level-dbfs", type=float, default=-24)
    p.add_argument("--max-drift-db", type=float, default=1.0)
    p.add_argument("--max-suppression-db", type=float, default=3.0)
    p.add_argument("--max-zero-run-ms", type=float, default=10.0)
    p.add_argument("--label", default="")
    p.set_defaults(func=cmd_rawcheck)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
