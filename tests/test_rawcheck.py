import numpy as np

from noisy import rawcheck

FS = 48000


def test_quantised_quiet_noise_has_many_zeros_but_no_long_run():
    noise = np.round(5 * np.random.default_rng(0).standard_normal((FS, 2))) / 32768
    assert np.mean(noise == 0) > 0.05
    assert max(rawcheck.longest_zero_run_samples(noise)) < round(0.010 * FS)


def test_gated_segment_is_found_per_channel():
    x = np.ones((FS, 2))
    x[1000:1480, 0] = 0
    x[0:10, 1] = 0
    x[-30:, 1] = 0
    assert rawcheck.longest_zero_run_samples(x) == [480, 30]
