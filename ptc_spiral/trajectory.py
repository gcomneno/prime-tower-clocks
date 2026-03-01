from __future__ import annotations

from typing import List, Tuple

from ptc_spiral.model import SpiralSig, Mode


def spiral_trajectory(N: int, primes: List[int]) -> List[Tuple[int, int]]:
    """
    Returns the spiral trajectory of N over progressively
    increasing modular products of the given primes.

    Each element is (M_k, x_k) where:
        M_k = product of primes up to k
        x_k = N mod M_k

    Guarantees:
        x_{k+1} % M_k == x_k
    """
    trajectory: List[Tuple[int, int]] = []
    M = 1

    for p in primes:
        M *= p
        x = N % M
        trajectory.append((M, x))

    return trajectory

def spiral_sig(
    N: int,
    primes: List[int],
    *,
    mode: Mode = "lossless",
    bound_bits: int | None = None,
    note: str | None = None,
) -> SpiralSig:
    """
    Build a SpiralSig centered on N.

    - If mode="lossless": we require M_last > N (true lossless for this N).
      We do NOT auto-set bound_bits, because the model-level proof
      M_last > 2**bound_bits - 1 is stronger than necessary.

    - If you want lossless to be provable a-posteriori without knowing N,
      pass bound_bits explicitly.
    """
    traj = spiral_trajectory(N, primes)
    xs = [x for _, x in traj]
    M_last = traj[-1][0] if traj else 1

    if mode == "lossless":
        if M_last <= N:
            raise ValueError(f"lossless requires M_last > N; got M_last={M_last} N={N}")
        # IMPORTANT: do not auto-set bound_bits here.

    return SpiralSig(
        version=1,
        primes=list(primes),
        xs=xs,
        mode=mode,
        bound_bits=bound_bits,
        created_utc=SpiralSig.now_utc_iso(),
        note=note,
    )