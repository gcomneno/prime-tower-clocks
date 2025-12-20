#!/usr/bin/env python3
"""
prime_tower_clocks.py — "Torre degli Orologi" (base 2) su moduli primi "nice".

Idea (riassunto):
- Scegliamo una lista di primi p_i (gli "orologi") tali che:
  1) p_i è primo (qui: <= 32-bit per default, ma funziona anche più su).
  2) p_i - 1 è "smooth" rispetto a una lista di primi piccoli (es. 2,3,5,7,11,13),
     così possiamo fare il log discreto con Pohlig–Hellman in modo efficiente.
  3) 2 è generatore mod p_i (ordine p_i-1). Così ogni residuo non nullo r mod p_i
     si scrive come r ≡ 2^e (mod p_i).

- La "firma" di N, per ogni orologio p, è:
    r = N mod p
    e = dlog_2(r) mod (p-1)  (se r != 0)
  Se r == 0, l'esponente non esiste (0 non è nel gruppo moltiplicativo), ma la firma
  conserva comunque r=0 e resta utile per la ricostruzione CRT.

- Se il prodotto M = Π p_i è > 10^D, e N ha D cifre (quindi N < 10^D), allora
  la CRT ricostruisce N esattamente (non solo N mod M).

CLI:
  python3 prime_tower_clocks.py 38491 --reconstruct
  python3 prime_tower_clocks.py 276 --anchor 61 --reconstruct

Nota:
  Questo non è "compressione lossless magica" se non metti abbastanza orologi.
  È "lossless su un range" quando M supera il massimo valore ricostruibile.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

# --- Config di default ------------------------------------------------------

DEFAULT_ANCHOR = 61
DEFAULT_SMOOTH_PRIMES: list[int] = [2, 3, 5, 7, 11, 13]
DEFAULT_32BIT_MIN_P = 1 << 31  # ~2.1e9
DEFAULT_32BIT_MAX_P = (1 << 32) - 1  # 4,294,967,295


# --- Utility aritmetiche ----------------------------------------------------


def egcd(a: int, b: int) -> tuple[int, int, int]:
    """Extended GCD: ritorna (g, x, y) con a*x + b*y = g = gcd(a,b)."""
    if b == 0:
        return (abs(a), 1 if a >= 0 else -1, 0)
    g, x1, y1 = egcd(b, a % b)
    return (g, y1, x1 - (a // b) * y1)


def modinv(a: int, m: int) -> int:
    """Inverso molare di a mod m (se gcd(a,m)=1)."""
    a %= m
    g, x, _ = egcd(a, m)
    if g != 1:
        raise ValueError(f"modinv: a={a} non invertibile mod {m} (gcd={g})")
    return x % m


def crt_pair(a1: int, m1: int, a2: int, m2: int) -> tuple[int, int]:
    """
    CRT per moduli coprimi:
      x ≡ a1 (mod m1)
      x ≡ a2 (mod m2)
    ritorna (x mod lcm, lcm) con lcm=m1*m2.
    """
    if m1 <= 0 or m2 <= 0:
        raise ValueError("CRT: moduli devono essere positivi.")
    g = math.gcd(m1, m2)
    if g != 1:
        raise ValueError(f"CRT: moduli non coprimi (gcd={g}). m1={m1}, m2={m2}")

    # a1 + m1*t ≡ a2 (mod m2)  =>  m1*t ≡ (a2-a1) (mod m2)
    t = ((a2 - a1) % m2) * modinv(m1 % m2, m2) % m2
    x = a1 + m1 * t
    return (x % (m1 * m2), m1 * m2)


def crt_many(residues: Sequence[int], moduli: Sequence[int]) -> tuple[int, int]:
    """CRT iterativa (moduli coprimi)."""
    if len(residues) != len(moduli):
        raise ValueError("CRT: lunghezze diverse.")
    x, m = residues[0] % moduli[0], moduli[0]
    for a, mod in zip(residues[1:], moduli[1:]):
        x, m = crt_pair(x, m, a % mod, mod)
    return x, m


# --- Primalità (Miller-Rabin) ----------------------------------------------


def _mr_decompose(n: int) -> tuple[int, int]:
    """n-1 = d * 2^s con d dispari."""
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    return d, s


def is_probable_prime(n: int) -> bool:
    """
    Miller–Rabin deterministico per n < 2^64 usando basi note.
    (Per i nostri 32-bit è più che sufficiente.)
    """
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if n == p:
            return True
        if n % p == 0:
            return False

    d, s = _mr_decompose(n)

    # Basi deterministiche per < 2^64
    bases = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)
    for a in bases:
        a %= n
        if a == 0:
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        composite = True
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                composite = False
                break
        if composite:
            return False
    return True


# --- Smoothness / "nice primes" --------------------------------------------


def factor_smooth(n: int, primes: Sequence[int]) -> tuple[dict[int, int], int]:
    """
    Fattorizza n usando solo i primi in `primes`.
    Ritorna (fattori, resto). Se resto=1 => completamente smooth.
    """
    f: dict[int, int] = {}
    for p in primes:
        if n == 1:
            break
        if n % p == 0:
            e = 0
            while n % p == 0:
                n //= p
                e += 1
            f[p] = e
    return f, n


def is_primitive_root_2(p: int, factors_p_minus_1: dict[int, int]) -> bool:
    """True se 2 ha ordine p-1 modulo p."""
    if p <= 2:
        return False
    phi = p - 1
    for q in factors_p_minus_1.keys():
        if pow(2, phi // q, p) == 1:
            return False
    return True


def nice_prime_info(p: int, smooth_primes: Sequence[int]) -> dict[int, int] | None:
    """
    Se p è "nice", ritorna la fattorizzazione smooth di (p-1) come dict {q:exp},
    altrimenti None.
    """
    if not is_probable_prime(p):
        return None
    fac, rem = factor_smooth(p - 1, smooth_primes)
    if rem != 1:
        return None
    if not is_primitive_root_2(p, fac):
        return None
    return fac


def _gen_smooth_ms_in_range(
    primes: Sequence[int],
    min_m: int,
    max_m: int,
) -> Iterable[tuple[int, dict[int, int]]]:
    """
    Genera m "smooth" in [min_m, max_m] come (m, factor_dict).
    Implementazione ricorsiva con pruning su max_m.
    """
    primes = list(primes)

    def rec(i: int, cur: int, fac: dict[int, int]) -> None:
        if cur > max_m:
            return
        if i == len(primes):
            if min_m <= cur <= max_m:
                # copia leggera
                yield_items.append((cur, dict(fac)))
            return
        p = primes[i]
        e = 0
        v = cur
        while v <= max_m:
            if e > 0:
                fac[p] = e
            else:
                fac.pop(p, None)
            rec(i + 1, v, fac)
            e += 1
            v *= p
        fac.pop(p, None)

    yield_items: list[tuple[int, dict[int, int]]] = []
    rec(0, 1, {})
    # qui yieldiamo ordinati decrescenti: vogliamo primi grandi (meno orologi)
    yield_items.sort(key=lambda t: t[0], reverse=True)
    yield from yield_items


def generate_nice_primes_32(
    smooth_primes: Sequence[int],
    min_p: int = DEFAULT_32BIT_MIN_P,
    max_p: int = DEFAULT_32BIT_MAX_P,
    limit: int = 2000,
) -> Iterable[tuple[int, dict[int, int]]]:
    """
    Genera fino a `limit` primi "nice" 32-bit nell'intervallo [min_p, max_p],
    usando la costruzione p = m + 1 con m smooth.
    """
    min_m = max(1, min_p - 1)
    max_m = max_p - 1

    found = 0
    for m, fac in _gen_smooth_ms_in_range(smooth_primes, min_m, max_m):
        p = m + 1
        # m è già p-1, quindi fac è fattorizzazione di p-1
        if not is_probable_prime(p):
            continue
        if not is_primitive_root_2(p, fac):
            continue
        yield p, fac
        found += 1
        if found >= limit:
            return


# --- Log discreto (Pohlig–Hellman) -----------------------------------------


def dlog_prime_power(
    g: int,
    h: int,
    p: int,
    q: int,
    exp: int,
) -> int:
    """
    Risolve g^x ≡ h (mod p) con ordine(g)=q^exp, e restituisce x mod q^exp.
    Lifting digit-by-digit in base q.
    """
    if exp <= 0:
        raise ValueError("exp deve essere positivo.")
    n = q**exp
    g %= p
    h %= p
    if g == 0 or h == 0:
        raise ValueError("dlog_prime_power: g,h devono essere non-zero in F_p*")
    # precompute: d = g^{q^{exp-1}} ha ordine q
    d = pow(g, q ** (exp - 1), p)

    x = 0
    for k in range(exp):
        # c = (h * g^{-x})^{q^{exp-1-k}}  (mod p)
        gx = pow(g, x, p)
        inv_gx = modinv(gx, p)
        c = pow((h * inv_gx) % p, q ** (exp - 1 - k), p)

        # trova a_k in [0,q-1] tale che d^{a_k} = c
        a_k: int | None = None
        cur = 1
        for cand in range(q):
            if cur == c:
                a_k = cand
                break
            cur = (cur * d) % p
        if a_k is None:
            raise ValueError(f"Discrete log lifting fallito (q={q}, exp={exp})")

        x += a_k * (q**k)

    return x % n


def dlog_pohlig_hellman_base2(h: int, p: int, factors_p_minus_1: dict[int, int]) -> int:
    """
    Risolve 2^x ≡ h (mod p), assumendo che 2 sia generatore (ordine p-1),
    usando fattorizzazione di p-1 (smooth).
    Ritorna x mod (p-1).
    """
    h %= p
    if h == 0:
        raise ValueError("dlog: h=0 non appartiene a F_p* (nessun esponente).")

    phi = p - 1
    congr_a: list[int] = []
    congr_m: list[int] = []

    for q, exp in factors_p_minus_1.items():
        m_i = q**exp
        # riduci al sottogruppo di ordine m_i
        g_i = pow(2, phi // m_i, p)
        h_i = pow(h, phi // m_i, p)
        x_i = dlog_prime_power(g_i, h_i, p, q, exp)
        congr_a.append(x_i)
        congr_m.append(m_i)

    x, _ = crt_many(congr_a, congr_m)
    return x % phi


# --- Strutture dati "firma" ------------------------------------------------


@dataclass(frozen=True)
class Firma:
    p: int
    r: int
    e: int | None  # esponente (mod p-1) se r != 0; altrimenti None
    phi: int
    factors: dict[int, int] | None


@dataclass(frozen=True)
class TowerSignature:
    N: int
    D: int
    orologi: list[int]
    firme: list[Firma]
    M: int  # prodotto moduli

    def residues(self) -> list[int]:
        out: list[int] = []
        for f in self.firme:
            if f.e is None:
                out.append(0)
            else:
                out.append(pow(2, f.e, f.p))
        return out


# --- Core API ---------------------------------------------------------------


def choose_orologi_for_digits(
    D: int,
    anchor: int = DEFAULT_ANCHOR,
    smooth_primes: Sequence[int] = DEFAULT_SMOOTH_PRIMES,
    # scegli orologi grandi (32-bit) per ridurre il numero di orologi:
    min_p: int = DEFAULT_32BIT_MIN_P,
    max_p: int = DEFAULT_32BIT_MAX_P,
) -> list[tuple[int, dict[int, int]]]:
    """
    Sceglie una lista di orologi (p, factors(p-1)) tale che M = Π p > 10^D.
    L'anchor viene messo per primo.
    """
    if D <= 0:
        raise ValueError("D deve essere positivo.")
    target = 10**D

    anchor_f = nice_prime_info(anchor, smooth_primes)
    if anchor_f is None:
        raise ValueError(f"anchor={anchor} non è un orologio 'nice' (serve p-1 smooth e 2 generatore).")

    chosen: list[tuple[int, dict[int, int]]] = [(anchor, anchor_f)]
    M = anchor

    used = {anchor}

    # Generatore di "nice primes" 32-bit
    for p, fac in generate_nice_primes_32(smooth_primes, min_p=min_p, max_p=max_p, limit=5000):
        if p in used:
            continue
        chosen.append((p, fac))
        used.add(p)
        M *= p
        if M > target:
            return chosen

    raise RuntimeError(
        "Pool di primi 'nice' insufficiente nel range 32-bit scelto. "
        "Prova ad abbassare min_p, aumentare il set smooth_primes, o alzare il limite."
    )


def compute_tower_signature(
    N: int,
    anchor: int = DEFAULT_ANCHOR,
    smooth_primes: Sequence[int] = DEFAULT_SMOOTH_PRIMES,
) -> TowerSignature:
    """
    Calcola la firma 'Torre degli Orologi' per N:
    - seleziona orologi in modo che M > 10^D
    - per ogni p: r = N mod p; se r != 0 calcola e con Pohlig–Hellman (base 2)
    """
    if N < 0:
        raise ValueError("N deve essere non-negativo.")
    D = len(str(N)) if N != 0 else 1

    chosen = choose_orologi_for_digits(D, anchor=anchor, smooth_primes=smooth_primes)
    orologi = [p for p, _ in chosen]
    M = 1
    firme: list[Firma] = []

    for p, fac in chosen:
        M *= p
        r = N % p
        if r == 0:
            firme.append(Firma(p=p, r=0, e=None, phi=p - 1, factors=fac))
            continue
        e = dlog_pohlig_hellman_base2(r, p, fac)
        firme.append(Firma(p=p, r=r, e=e, phi=p - 1, factors=fac))

    return TowerSignature(N=N, D=D, orologi=orologi, firme=firme, M=M)


def reconstruct_from_tower_signature(sig: TowerSignature) -> tuple[int, int]:
    """
    Ricostruisce N_mod_M usando CRT sulle residue (0 oppure 2^e mod p).
    Ritorna (N_mod_M, M).
    """
    residues = sig.residues()
    moduli = sig.orologi
    x, M = crt_many(residues, moduli)
    return x, M


# --- CLI --------------------------------------------------------------------


def _parse_primes_csv(s: str) -> list[int]:
    if not s.strip():
        return []
    out: list[int] = []
    for tok in s.split(","):
        tok = tok.strip()
        if not tok:
            continue
        out.append(int(tok))
    if not out:
        raise ValueError("Lista primi vuota.")
    out = sorted(set(out))
    if out[0] < 2:
        raise ValueError("I primi devono essere >= 2.")
    return out


# ---------------------------------------------------------------------
# JSONL bridge: TowerSignature -> PTCSig (minimal, decodabile nel tempo)
# ---------------------------------------------------------------------
try:
    from jsonl_validation import ClockRec, PTCSig, _utc_now_iso
except Exception:  # pragma: no cover
    PTCSig = None  # type: ignore
    ClockRec = None  # type: ignore
    _utc_now_iso = None  # type: ignore


def tower_to_ptcsig(sig: TowerSignature, base: int = 2) -> PTCSig:
    """Convert a TowerSignature to a minimal JSONL signature container (PTCSig)."""
    if PTCSig is None or ClockRec is None or _utc_now_iso is None:
        raise RuntimeError("jsonl_validation.py non disponibile: impossibile esportare JSONL")

    clocks: list[ClockRec] = []
    for f in sig.firme:
        if f.r == 0 or f.e is None:
            clocks.append(ClockRec(p=f.p, z=True, e=None))
        else:
            clocks.append(ClockRec(p=f.p, z=False, e=int(f.e)))

    M_bits = sig.M.bit_length()
    N_bits = sig.N.bit_length()
    return PTCSig(
        base=base,
        clocks=sorted(clocks, key=lambda c: c.p),
        created_utc=_utc_now_iso(),
        note="Prime Tower Clocks signature",
        M_bits=M_bits,
        N_bits=N_bits,
        lossless_claim=(M_bits > N_bits),
    )


if __name__ == "__main__":
    from cli import main

    raise SystemExit(main())
