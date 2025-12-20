from __future__ import annotations

import prime_tower_clocks as ptc


def product(xs: list[int]) -> int:
    out = 1
    for x in xs:
        out *= x
    return out

def collect_nice_primes(k: int, *, max_p: int = 300_000) -> list[int]:
    """
    Prende i primi k 'nice primes' trovati in [3..max_p], usando la definizione del progetto:
    - p primo
    - p-1 smooth rispetto a DEFAULT_SMOOTH_PRIMES
    - 2 generatore mod p
    """
    out: list[int] = []
    for p in range(3, max_p + 1):
        info = ptc.nice_prime_info(p, ptc.DEFAULT_SMOOTH_PRIMES)
        if info is not None:
            out.append(p)
            if len(out) >= k:
                return out
    raise RuntimeError(f"Non ho trovato {k} nice primes entro max_p={max_p}")

def build_tower_signature_manual(N: int, primes: list[int]) -> ptc.TowerSignature:
    """
    Costruisce una TowerSignature senza usare choose_orologi_for_digits (evita il generatore 32-bit di default).
    Usa la stessa logica: r=N mod p, se r!=0 calcola e con Pohlig–Hellman base 2.
    """
    if N < 0:
        raise ValueError("N deve essere non-negativo.")

    ps = sorted(primes)
    firme: list[ptc.Firma] = []
    M = 1

    for p in ps:
        fac = ptc.nice_prime_info(p, ptc.DEFAULT_SMOOTH_PRIMES)
        if fac is None:
            raise ValueError(f"p={p} non è 'nice' con smooth_primes={ptc.DEFAULT_SMOOTH_PRIMES}")

        r = N % p
        if r == 0:
            e = None
        else:
            e = ptc.dlog_pohlig_hellman_base2(r, p, fac)

        firme.append(ptc.Firma(p=p, r=r, e=e, phi=p - 1, factors=fac))
        M *= p

    D = len(str(N)) if N != 0 else 1
    return ptc.TowerSignature(N=N, D=D, orologi=ps, firme=firme, M=M)
