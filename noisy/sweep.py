"""Exponential sine sweep and inverse-filter deconvolution (Farina 2000, AES preprint 5093)."""

import numpy as np
from scipy.signal import fftconvolve


def _sweep_rate_s(f1_hz, f2_hz, duration_s):
    return duration_s / np.log(f2_hz / f1_hz)


def exponential_sweep(f1_hz, f2_hz, duration_s, sample_rate_hz, fade_s=0.05):
    t_s = np.arange(round(duration_s * sample_rate_hz)) / sample_rate_hz
    rate_s = _sweep_rate_s(f1_hz, f2_hz, duration_s)
    sweep = np.sin(2 * np.pi * f1_hz * rate_s * (np.exp(t_s / rate_s) - 1))
    return sweep * fade(len(sweep), round(fade_s * sample_rate_hz))


def fade(n, fade_samples):
    window = np.ones(n)
    ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(fade_samples) / fade_samples)
    window[:fade_samples] = ramp
    window[n - fade_samples :] = ramp[::-1]
    return window


def inverse_filter(sweep, f1_hz, f2_hz, duration_s, sample_rate_hz):
    """Time-reversed sweep with a +6 dB/oct envelope, normalised to unit gain mid-band."""
    t_s = np.arange(len(sweep)) / sample_rate_hz
    inverse = sweep[::-1] * np.exp(-t_s / _sweep_rate_s(f1_hz, f2_hz, duration_s))
    n = 2 * len(sweep)
    response = np.abs(np.fft.rfft(sweep, n) * np.fft.rfft(inverse, n))
    f_hz = np.fft.rfftfreq(n, 1 / sample_rate_hz)
    band = (f_hz > 2 * f1_hz) & (f_hz < f2_hz / 2)
    return inverse / response[band].mean()


def deconvolve(recording, inverse, ir_samples):
    """Linear impulse response of each recorded channel; t=0 is the sweep's first sample.

    Harmonic distortion products land before t=0 and are cut off here.
    """
    recording = np.atleast_2d(recording.T).T
    full = fftconvolve(recording, inverse[:, None], axes=0)
    start = len(inverse) - 1
    return full[start : start + ir_samples]
