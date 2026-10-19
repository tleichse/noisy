"""Analysis for the raw-mode check: detecting gating in a recording."""

import numpy as np


def longest_zero_run_samples(x):
    """Longest run of exact zeros per channel of a (samples, channels) array.

    Isolated zeros are normal in quiet 16-bit audio; only a sustained run indicates gating.
    """
    padded = np.vstack([np.zeros((1, x.shape[1]), bool), x == 0, np.zeros((1, x.shape[1]), bool)])
    runs = []
    for column in padded.T:
        edges = np.flatnonzero(np.diff(column.astype(np.int8)))
        runs.append(int(np.max(edges[1::2] - edges[::2], initial=0)))
    return runs
