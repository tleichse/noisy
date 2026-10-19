import numpy as np

from noisy import sweep

FS = 48000


def _measure(true_ir):
    s = sweep.exponential_sweep(100, 20000, 2.0, FS)
    inverse = sweep.inverse_filter(s, 100, 20000, 2.0, FS)
    recording = np.convolve(s, true_ir)[:, None]
    return sweep.deconvolve(recording, inverse, len(true_ir))[:, 0]


def _in_band_db(ir, low_hz=300, high_hz=10000):
    f_hz = np.fft.rfftfreq(len(ir), 1 / FS)
    band = (f_hz > low_hz) & (f_hz < high_hz)
    return 20 * np.log10(np.abs(np.fft.rfft(ir)))[band]


def test_recovers_delay_and_gain_of_known_ir():
    true_ir = np.zeros(2400)
    true_ir[480] = 0.5
    ir = _measure(true_ir)
    assert np.argmax(np.abs(ir)) == 480
    assert abs(np.median(_in_band_db(ir)) - 20 * np.log10(0.5)) < 0.2


def test_recovers_relative_tap_amplitudes():
    true_ir = np.zeros(2400)
    true_ir[480] = 0.5
    true_ir[960] = -0.2
    ir = _measure(true_ir)
    assert abs(ir[960] / ir[480] + 0.4) < 0.01


def test_band_limited_response_is_flat_in_band():
    true_ir = np.zeros(4800)
    true_ir[100] = 1.0
    ir = _measure(true_ir)
    assert np.ptp(_in_band_db(ir)) < 1.0


def test_deconvolves_each_channel():
    s = sweep.exponential_sweep(100, 20000, 1.0, FS)
    inverse = sweep.inverse_filter(s, 100, 20000, 1.0, FS)
    recording = np.stack([np.r_[np.zeros(10), s], np.r_[np.zeros(50), s[:-40]]], axis=1)
    ir = sweep.deconvolve(recording, inverse, 200)
    assert np.argmax(np.abs(ir[:, 0])) == 10
    assert np.argmax(np.abs(ir[:, 1])) == 50
