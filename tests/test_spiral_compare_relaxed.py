from ptc_spiral.compare import common_prefix_len_relaxed, divergence_index_relaxed
from ptc_spiral.trajectory import spiral_sig


def test_relaxed_stops_on_lens_mismatch():
    # Same N but different lenses after first element
    a = spiral_sig(12345, [3, 5, 7, 11], mode="lossy")
    b = spiral_sig(12345, [3, 13, 17, 19], mode="lossy")

    # They match at level 1 (prime=3 and residue mod 3), then lenses differ.
    assert common_prefix_len_relaxed(a, b) == 1
    assert divergence_index_relaxed(a, b) is None


def test_relaxed_detects_divergence_before_lens_mismatch():
    # Same lens for first 2 primes (3,5), then differs; numbers diverge at level 2
    a = spiral_sig(10, [3, 5, 7], mode="lossy")
    b = spiral_sig(13, [3, 5, 13], mode="lossy")

    # divergence should be detected at level 2 (mod 15) before lens mismatch at level 3
    assert divergence_index_relaxed(a, b) == 2
    assert common_prefix_len_relaxed(a, b) == 1
