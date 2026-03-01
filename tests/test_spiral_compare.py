from ptc_spiral.compare import common_prefix_len, divergence_index
from ptc_spiral.trajectory import spiral_sig


def test_divergence_index_simple():
    primes = [3, 5, 7, 11, 13, 17, 19]

    a = spiral_sig(12345, primes, mode="lossy")
    b = spiral_sig(12346, primes, mode="lossy")

    idx = divergence_index(a, b)
    assert idx is not None
    assert 1 <= idx <= len(primes)

    # Prefix length is idx-1
    assert common_prefix_len(a, b) == idx - 1


def test_no_divergence_when_same_number():
    primes = [3, 5, 7, 11, 13]
    a = spiral_sig(9999, primes, mode="lossy")
    b = spiral_sig(9999, primes, mode="lossy")

    assert divergence_index(a, b) is None
    assert common_prefix_len(a, b) == len(primes)
