import numpy as np
from scipy.signal import fftconvolve

from noisy import latency

FS = 48000


def test_gcc_phat_finds_delay_through_coloured_path():
    burst = latency.noise_burst(0.5, FS)
    path = np.zeros(200)
    path[0], path[3], path[40] = 1.0, 0.6, -0.3
    recorded = np.r_[np.zeros(1234), fftconvolve(burst, path)]
    recorded = recorded + 0.05 * np.random.default_rng(1).standard_normal(len(recorded))
    delay, ratio = latency.gcc_phat_delay(burst, recorded, 4000)
    assert delay == 1234
    assert ratio > 10


def test_noise_burst_is_peak_normalised():
    burst = latency.noise_burst(0.2, FS)
    assert np.isclose(np.max(np.abs(burst)), 1.0)
