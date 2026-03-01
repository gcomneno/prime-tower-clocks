from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

Mode = Literal["lossless", "lossy"]


@dataclass(frozen=True)
class SpiralSig:
    """
    Spiral signature centered on an (implicit) integer N.

    primes: p_1..p_k
    xs:     x_k = N mod M_k where M_k = Π_{i<=k} p_i

    Spiral property (must always hold):
        x_{k+1} % M_k == x_k

    mode:
      - "lossless": intended to allow exact recovery of N once M_k exceeds a known bound.
      - "lossy":    valid spiral, but only identifies N modulo M_k.

    bound_bits (optional):
      If provided and mode=="lossless", we enforce M_last > 2**bound_bits - 1,
      which guarantees the final residue uniquely identifies N in [0, 2**bound_bits).
    """

    version: int
    primes: list[int]
    xs: list[int]
    mode: Mode = "lossless"
    bound_bits: int | None = None
    created_utc: str | None = None
    note: str | None = None

    @staticmethod
    def now_utc_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("version must be >= 1")
        if len(self.primes) != len(self.xs):
            raise ValueError("primes and xs must have the same length")
        if self.mode not in ("lossless", "lossy"):
            raise ValueError(f"invalid mode: {self.mode}")

        # Spiral coherence check: x_{k+1} % M_k == x_k
        M = 1
        prev_M: int | None = None
        prev_x: int | None = None

        for p, x in zip(self.primes, self.xs):
            if p <= 1:
                raise ValueError(f"invalid prime: {p}")
            M *= p

            if prev_M is not None and prev_x is not None:
                if x % prev_M != prev_x:
                    raise ValueError("spiral property violated")

            prev_M = M
            prev_x = x

        # Lossless provability check (only if bound_bits is provided)
        if self.mode == "lossless" and self.bound_bits is not None and self.k > 0:
            if self.bound_bits < 0:
                raise ValueError("bound_bits must be >= 0")
            max_n = (1 << self.bound_bits) - 1
            if self.M_last() <= max_n:
                raise ValueError(
                    "lossless requires M_last > 2**bound_bits - 1; "
                    f"got M_last={self.M_last()} bound_bits={self.bound_bits}"
                )

    def Ms(self) -> list[int]:
        Ms: list[int] = []
        M = 1
        for p in self.primes:
            M *= p
            Ms.append(M)
        return Ms

    def M_last(self) -> int:
        M = 1
        for p in self.primes:
            M *= p
        return M

    @property
    def k(self) -> int:
        return len(self.primes)
