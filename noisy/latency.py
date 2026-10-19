"""Delay estimation by generalised cross-correlation with phase transform (Knapp & Carter 1976)."""

import numpy as np
from scipy.signal import butter, sosfilt


def gcc_phat_delay(reference, recorded, max_delay_samples):
    """Delay of `recorded` relative to `reference` in samples, and the peak-to-median ratio."""
    n = len(reference) + len(recorded)
    cross = np.fft.rfft(recorded, n) * np.conj(np.fft.rfft(reference, n))
    correlation = np.fft.irfft(cross / np.maximum(np.abs(cross), 1e-12), n)
    window = np.abs(correlation[: max_delay_samples + 1])
    delay_samples = int(np.argmax(window))
    return delay_samples, float(window[delay_samples] / np.median(window))


def noise_burst(duration_s, sample_rate_hz, low_hz=300, high_hz=8000, seed=0):
    """Band-limited noise inside the range the laptop speakers can reproduce, peak-normalised."""
    noise = np.random.default_rng(seed).standard_normal(round(duration_s * sample_rate_hz))
    sos = butter(4, [low_hz, high_hz], btype="bandpass", fs=sample_rate_hz, output="sos")
    burst = sosfilt(sos, noise)
    return burst / np.max(np.abs(burst))
