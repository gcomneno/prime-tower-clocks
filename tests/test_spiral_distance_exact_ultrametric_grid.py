from fractions import Fraction

import pytest

from ptc_spiral.compare import spiral_distance_exact
from ptc_spiral.trajectory import spiral_sig


def _sig(n: int, primes: list[int]):
    return spiral_sig(n, primes, mode="lossy")


def _Mk(primes: list[int], k: int) -> int:
    prod = 1
    for p in primes[:k]:
        prod *= p
    return prod


@pytest.mark.parametrize(
    "primes",
    [
        [2, 3, 5, 7],
        [3, 5, 7, 11],
        [5, 7, 11, 13],
        [3, 5, 7, 11, 13],
    ],
)
@pytest.mark.parametrize("base", [0, 42, 123, 999])
def test_spiral_distance_exact_ultrametric_grid(primes, base):
    # richiediamo almeno 3 livelli per costruire M1, M2, M3
    assert len(primes) >= 3

    M1 = _Mk(primes, 1)
    M2 = _Mk(primes, 2)
    M3 = _Mk(primes, 3)

    # Costruzione che GARANTISCE divergenze entro la lente:
    # - a vs b: delta=M1 -> match fino a M1, diverge al livello 2 => d=1/M1
    # - a vs c: delta=M2 -> match fino a M2, diverge al livello 3 => d=1/M2
    # - b vs c: delta=M2-M1 = M1*(p2-1) -> match fino a M1, diverge al livello 2 => d=1/M1
    a = _sig(base, primes)
    b = _sig(base + M1, primes)
    c = _sig(base + M2, primes)

    dab = spiral_distance_exact(a, b)
    dac = spiral_distance_exact(a, c)
    dbc = spiral_distance_exact(b, c)

    assert dab == Fraction(1, M1)
    assert dac == Fraction(1, M2)
    assert dbc == Fraction(1, M1)

    # ultrametria: d(a,c) <= max(d(a,b), d(b,c))
    assert dac <= max(dab, dbc)


@pytest.mark.parametrize(
    "primes, base",
    [
        ([2, 3, 5, 7], 1000),
        ([3, 5, 7, 11, 13], 2000),
    ],
)
def test_spiral_distance_exact_ultrametric_strong_property(primes, base):
    """
    Proprietà tipica degli ultrametrici:
    se d(a,b) < d(a,c) allora d(b,c) = d(a,c).
    """
    M2 = 1
    for p in primes[:2]:
        M2 *= p
    M3 = M2 * primes[2]

    a = _sig(base, primes)
    b = _sig(base + M3, primes)  # più vicino
    c = _sig(base + M2, primes)  # meno vicino

    dab = spiral_distance_exact(a, b)  # 1/M3
    dac = spiral_distance_exact(a, c)  # 1/M2
    dbc = spiral_distance_exact(b, c)  # 1/M2

    assert dab < dac
    assert dbc == dac
