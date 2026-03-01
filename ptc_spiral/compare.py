from __future__ import annotations

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
