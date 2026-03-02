from fractions import Fraction

from ptc_spiral.compare import spiral_distance_exact
from ptc_spiral.trajectory import spiral_sig


def _sig(n: int, primes: list[int]):
    # mode="lossy" va bene qui perché spiral_distance_exact usa la gerarchia modulare
    return spiral_sig(n, primes, mode="lossy")


def test_spiral_distance_exact_metric_axioms_basic():
    primes = [3, 5, 7, 11, 13]
    a = _sig(12345, primes)
    b = _sig(12345 + 15, primes)  # delta = M2 -> distanza attesa 1/15

    # non-negatività + identità degli indiscernibili
    assert spiral_distance_exact(a, a) == Fraction(0, 1)
    assert spiral_distance_exact(a, b) > Fraction(0, 1)

    # simmetria
    assert spiral_distance_exact(a, b) == spiral_distance_exact(b, a)


def test_spiral_distance_exact_ultrametric_triangle_inequality_case_1():
    primes = [3, 5, 7, 11, 13]
    base = 12345

    a = _sig(base, primes)
    b = _sig(base + 15, primes)  # delta = M2 -> d(a,b)=1/15
    c = _sig(base + 105, primes)  # delta = M3 -> d(a,c)=1/105

    dab = spiral_distance_exact(a, b)
    dbc = spiral_distance_exact(b, c)
    dac = spiral_distance_exact(a, c)

    assert dab == Fraction(1, 15)
    assert dbc == Fraction(1, 15)
    assert dac == Fraction(1, 105)

    # ultrametria: d(a,c) <= max(d(a,b), d(b,c))
    assert dac <= max(dab, dbc)


def test_spiral_distance_exact_ultrametric_triangle_inequality_case_2_strict():
    primes = [3, 5, 7, 11, 13]
    base = 9999

    a = _sig(base, primes)
    b = _sig(base + 1155, primes)  # delta = M4 -> d(a,b)=1/1155
    c = _sig(base + 105, primes)  # delta = M3 -> d(a,c)=1/105

    dab = spiral_distance_exact(a, b)
    dac = spiral_distance_exact(a, c)
    dbc = spiral_distance_exact(b, c)

    assert dab == Fraction(1, 1155)
    assert dac == Fraction(1, 105)
    assert dbc == Fraction(1, 105)

    # ultrametria
    assert dab <= max(dac, dbc)

    # proprietà tipica ultrametrica (opzionale ma "sexy"):
    # se d(a,b) < d(a,c) allora d(b,c) = d(a,c)
    assert dab < dac
    assert dbc == dac
