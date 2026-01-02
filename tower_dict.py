"""Tower dictionary utilities (format-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TowerDict:
    dict_id: int
    primes: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.dict_id <= 0:
            raise ValueError("dict_id must be > 0")
        if not self.primes:
            raise ValueError("primes must be non-empty")
        if tuple(sorted(self.primes)) != self.primes:
            raise ValueError("primes must be sorted ascending")
        if any(p < 3 for p in self.primes):
            raise ValueError("all primes must be >= 3")


def delta_encode_primes(primes: tuple[int, ...]) -> list[int]:
    """Encode primes as [p0, d1, d2, ...] where di = p[i]-p[i-1]."""
    if not primes:
        raise ValueError("empty primes")
    out = [int(primes[0])]
    for a, b in zip(primes[1:], primes[:-1]):
        out.append(int(a - b))
    return out


def delta_decode_primes(deltas: list[int]) -> tuple[int, ...]:
    """Decode primes from [p0, d1, d2, ...]."""
    if not deltas:
        raise ValueError("empty deltas")
    ps: list[int] = [int(deltas[0])]
    cur = ps[0]
    for d in deltas[1:]:
        cur += int(d)
        ps.append(cur)
    return tuple(ps)


class TowerRegistry:
    """Assign stable dict_id for each distinct primes tuple (in-process)."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[int, ...], int] = {}
        self._dicts: dict[int, TowerDict] = {}
        self._next_id = 1

    def intern(self, primes: tuple[int, ...]) -> int:
        primes = tuple(primes)
        if tuple(sorted(primes)) != primes:
            raise ValueError("primes must be sorted ascending")
        if primes in self._by_key:
            return self._by_key[primes]
        dict_id = self._next_id
        self._next_id += 1
        td = TowerDict(dict_id=dict_id, primes=primes)
        self._by_key[primes] = dict_id
        self._dicts[dict_id] = td
        return dict_id

    def get(self, dict_id: int) -> TowerDict:
        return self._dicts[dict_id]

    def all_dicts(self) -> list[TowerDict]:
        return [self._dicts[i] for i in sorted(self._dicts)]


__all__ = ["TowerDict", "TowerRegistry", "delta_encode_primes", "delta_decode_primes"]
