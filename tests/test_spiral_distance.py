from fractions import Fraction

import pytest

from ptc_spiral.compare import spiral_distance_bound, spiral_distance_exact
from ptc_spiral.model import SpiralSig
from ptc_spiral.trajectory import spiral_sig


def test_spiral_distance_exact_from_divergence():
    primes = [3, 5, 7, 11, 13]

    # Choose numbers that match mod 3,15,105,1155 and diverge at 15015
    # i.e. delta = M4 = 1155 -> common prefix = 4, divergence at level 5
    a = spiral_sig(12345, primes, mode="lossy")
    b = spiral_sig(12345 + 1155, primes, mode="lossy")

    d, exact = spiral_distance_bound(a, b)
    assert exact is True
    assert d == Fraction(1, 1155)

    assert spiral_distance_exact(a, b) == Fraction(1, 1155)


def test_spiral_distance_bound_when_no_divergence_in_prefix():
    primes = [3, 5, 7, 11, 13]

    # Same N, but b has fewer levels -> cannot decide exact equality beyond prefix
    a = spiral_sig(9999, primes, mode="lossy")
    b = spiral_sig(9999, primes[:3], mode="lossy")

    d, exact = spiral_distance_bound(a, b, relaxed=True)
    assert exact is False
    # They match for 3 levels -> M3 = 3*5*7 = 105
    assert d == Fraction(1, 105)


def test_spiral_distance_bound_relaxed_lens_mismatch():
    a = spiral_sig(10, [3, 5, 7], mode="lossy")
    b = spiral_sig(10, [3, 13, 17], mode="lossy")

    d, exact = spiral_distance_bound(a, b, relaxed=True)
    assert exact is False
    assert d == Fraction(1, 3)  # only prime=3 comparable


def test_spiral_distance_strict_lens_mismatch_raises():
    a = spiral_sig(10, [3, 5, 7], mode="lossy")
    b = spiral_sig(10, [3, 13, 17], mode="lossy")

    with pytest.raises(ValueError):
        spiral_distance_bound(a, b, relaxed=False)


def spiral_distance_exact(a: SpiralSig, b: SpiralSig, *, relaxed: bool = True) -> Fraction:
    """
    Exact spiral distance between two signatures, when decidable from their prefixes.

    (…docstring come l’hai scritta tu…)
    """
    # If the two signatures are identical, distance is exactly zero.
    # This makes the function total on (sig, sig) and respects the metric axiom d(x,x)=0.
    if a == b:
        return Fraction(0, 1)

    d, exact = spiral_distance_bound(a, b, relaxed=relaxed)
    if not exact:
        raise ValueError("distance not decidable with given prefix (need more levels or same lens)")
    return d


def test_spiral_distance_exact_identity_is_zero():
    primes = [3, 5, 7, 11, 13]
    a = spiral_sig(12345, primes, mode="lossy")
    assert spiral_distance_exact(a, a) == Fraction(0, 1)
