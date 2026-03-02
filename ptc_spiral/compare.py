from __future__ import annotations

from fractions import Fraction

from ptc_spiral.model import SpiralSig


def _common_k(a: SpiralSig, b: SpiralSig) -> int:
    return min(a.k, b.k)


def common_prefix_len(a: SpiralSig, b: SpiralSig) -> int:
    """
    Number of initial levels where xs match, comparing level-by-level up to min(k).
    Assumes both spirals use the same prime sequence (same 'lens').
    """
    k = _common_k(a, b)
    n = 0
    for i in range(k):
        if a.xs[i] != b.xs[i]:
            break
        n += 1
    return n


def divergence_index(a: SpiralSig, b: SpiralSig) -> int | None:
    """
    1-based index of the first level where xs differ; None if no divergence
    within the common prefix length min(k).
    Assumes both spirals use the same prime sequence (same 'lens').
    """
    k = _common_k(a, b)
    for i in range(k):
        if a.xs[i] != b.xs[i]:
            return i + 1
    return None


def divergence_info(a: SpiralSig, b: SpiralSig) -> tuple[int, int, int] | None:
    """
    Returns (index_1based, x_a, x_b) at first divergence; None if no divergence.
    """
    idx = divergence_index(a, b)
    if idx is None:
        return None
    i = idx - 1
    return (idx, a.xs[i], b.xs[i])


def common_prefix_len_relaxed(a: SpiralSig, b: SpiralSig) -> int:
    """
    Like common_prefix_len, but stops when prime sequences differ.
    Returns the number of initial levels where both primes match AND xs match.
    """
    k = min(a.k, b.k)
    n = 0
    for i in range(k):
        if a.primes[i] != b.primes[i]:
            break
        if a.xs[i] != b.xs[i]:
            break
        n += 1
    return n


def divergence_index_relaxed(a: SpiralSig, b: SpiralSig) -> int | None:
    """
    1-based index of first level where:
      - primes match, but xs differ.
    Stops (returns None) if prime sequences diverge before any xs divergence.
    """
    k = min(a.k, b.k)
    for i in range(k):
        if a.primes[i] != b.primes[i]:
            return None
        if a.xs[i] != b.xs[i]:
            return i + 1
    return None


def _M_prefix(primes: list[int], k: int) -> int:
    """Product of the first k primes. k may be 0 -> 1."""
    M = 1
    for p in primes[:k]:
        M *= p
    return M


def spiral_distance_bound(a: SpiralSig, b: SpiralSig, *, relaxed: bool = True) -> tuple[Fraction, bool]:
    """
    Spiral distance as Fraction(1, M_k*), where k* is the length of the common prefix.

    - If relaxed=True: we stop comparing when prime sequences diverge.
    - If relaxed=False: we require same primes up to min(k); if mismatch is found, raise.

    Returns: (distance, exact)
      - exact=True  -> we found an xs divergence at some level, so k* is final.
      - exact=False -> no divergence found within the comparable prefix; distance is a bound.
    """
    k = min(a.k, b.k)
    common = 0

    for i in range(k):
        if a.primes[i] != b.primes[i]:
            if relaxed:
                # Can't compare further; only a bound
                M = _M_prefix(a.primes, common)
                return (Fraction(1, M), False)
            raise ValueError(f"lens mismatch: primes differ at level {i + 1}")

        if a.xs[i] != b.xs[i]:
            # Divergence at i+1 -> k* = i
            M = _M_prefix(a.primes, common)
            return (Fraction(1, M), True)

        common += 1

    # No divergence found up to min length; only a bound (could diverge later)
    M = _M_prefix(a.primes, common)
    return (Fraction(1, M), False)


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
