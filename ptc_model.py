"""PTC core data model (format-agnostic).

This module contains only the minimal dataclasses used by the JSONL backend
and the PTC-bin backend. No file I/O lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ClockRec:
    """One clock record for a modulus p.

    If z=True then p divides N and e must be None.
    If z=False then e is an exponent such that base^e ≡ (N mod p) (mod p).
    """

    p: int
    z: bool
    e: int | None = None


@dataclass(frozen=True)
class PTCSig:
    """A Prime Tower Clocks signature (format-agnostic)."""

    base: int
    clocks: list[ClockRec]
    created_utc: str | None = None
    note: str | None = None
    # optional summary hints (not required for reconstruction)
    M_bits: int | None = None
    N_bits: int | None = None
    lossless_claim: bool | None = None


def utc_now_iso() -> str:
    """UTC now in ISO format without microseconds, suffixed with 'Z'."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def e_bit_width_for_prime(p: int) -> int:
    """Bit width for encoding an exponent e in [0 .. p-2].

    Equivalent to ceil(log2(p-1)), but without floats:
      w = bit_length(p-2)
    """
    if p < 3:
        raise ValueError("p must be >= 3")
    return (p - 2).bit_length()


__all__ = ["ClockRec", "PTCSig", "utc_now_iso", "e_bit_width_for_prime"]
