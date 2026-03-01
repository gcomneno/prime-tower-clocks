from __future__ import annotations

from typing import List

import ptc_model
from ptc_spiral.model import SpiralSig, Mode


def classic_to_spiral(
    sig: ptc_model.PTCSig,
    *,
    mode: Mode = "lossless",
    bound_bits: int | None = None,
    downgrade_to_lossy: bool = True,
    note: str | None = None,
) -> SpiralSig:
    """
    Convert a classic PTCSig (list of clocks p,z,e in base=2) into a SpiralSig.

    We recover residues mod p as:
      - if z: r = 0
      - else: r = base^e mod p

    Then we lift progressively using CRT to obtain x_k = N mod M_k with M_k = Π p_i.

    Lossless handling:
      - If bound_bits is not provided, we try to read sig.N_bits (if present).
      - If mode=="lossless" and bound_bits is known but cannot be proven
        (M_last <= 2**bound_bits - 1), then:
          * if downgrade_to_lossy=True: we return a lossy SpiralSig instead
          * else: SpiralSig will raise ValueError (by design)
    """
    base = sig.base

    # Pick a bound if we can.
    if bound_bits is None:
        # PTCSig from your repo exposes N_bits; keep it optional to stay robust.
        bound_bits = getattr(sig, "N_bits", None)

    primes: List[int] = []
    xs: List[int] = []

    # progressive CRT state: x ≡ N (mod M)
    x = 0
    M = 1

    for c in sig.clocks:
        p = c.p
        primes.append(p)

        # residue mod p
        r = 0 if c.z else pow(base, c.e, p)

        # combine: x ≡ old (mod M), x ≡ r (mod p)
        inv = pow(M, -1, p)  # inverse of M mod p
        t = ((r - x) * inv) % p
        x = x + M * t
        M = M * p

        xs.append(x % M)

    auto_note = "from classic PTCSig"
    if note:
        auto_note = f"{auto_note}; {note}"

    # If we *wanted* lossless but can't prove it, optionally downgrade.
    if mode == "lossless" and bound_bits is not None and len(primes) > 0:
        max_n = (1 << bound_bits) - 1
        if M <= max_n and downgrade_to_lossy:
            mode = "lossy"
            bound_bits = None
            auto_note = f"{auto_note}; downgraded to lossy (insufficient M for bound_bits)"

    return SpiralSig(
        version=1,
        primes=primes,
        xs=xs,
        mode=mode,
        bound_bits=bound_bits,
        created_utc=SpiralSig.now_utc_iso(),
        note=auto_note,
    )
