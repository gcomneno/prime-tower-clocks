"""
CRT reconstruction utilities for Prime Tower Clocks.

reconstruct_from_signature(PTCSig) returns (N_mod_M, M, lossless_by_bits)
where lossless_by_bits is True only if summary contains M_bits and N_bits and M_bits > N_bits.
"""

from math import prod


def _egcd(a: int, b: int) -> tuple[int, int, int]:
    if b == 0:
        return (a, 1, 0)
    g, x1, y1 = _egcd(b, a % b)
    return (g, y1, x1 - (a // b) * y1)


def _inv_mod(a: int, m: int) -> int:
    g, x, _ = _egcd(a, m)
    if g != 1:
        raise ValueError("Modulo non coprimo: inverso non esiste")
    return x % m


def crt_pair(a1: int, m1: int, a2: int, m2: int) -> tuple[int, int]:
    """
    Combine:
      x ≡ a1 (mod m1)
      x ≡ a2 (mod m2)
    assuming gcd(m1,m2)=1.
    returns (a, m) with x ≡ a (mod m), m=m1*m2
    """
    inv = _inv_mod(m1 % m2, m2)
    t = ((a2 - a1) % m2) * inv % m2
    a = a1 + m1 * t
    m = m1 * m2
    return a % m, m


def reconstruct_from_signature(sig: PTCSig) -> tuple[int, int, bool]:
    """
    Returns (N_mod_M, M, lossless_guaranteed_if_known).
    'lossless' can be guaranteed only if summary includes N_bits and M_bits and M_bits > N_bits.
    """
    base = sig.base
    residues: list[tuple[int, int]] = []  # (r, p)

    for c in sig.clocks:
        if c.z:
            r = 0
        else:
            r = pow(base, int(c.e), c.p)
        residues.append((r, c.p))

    # CRT fold
    a, m = residues[0][0] % residues[0][1], residues[0][1]
    for r, p in residues[1:]:
        a, m = crt_pair(a, m, r % p, p)

    lossless = False
    if sig.M_bits is not None and sig.N_bits is not None:
        lossless = int(sig.M_bits) > int(sig.N_bits)

    return a, m, lossless

__all__ = ['reconstruct_from_signature']
