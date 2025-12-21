from __future__ import annotations

import prime_tower_clocks as ptc
from tests._helpers import build_tower_signature_manual, collect_nice_primes, product


def test_manual_small_roundtrip_lossless():
    primes = collect_nice_primes(8)
    N = 276  # classico esempio “piccolo”
    sig = build_tower_signature_manual(N, primes)

    x, M = ptc.reconstruct_from_tower_signature(sig)
    assert M == product(sorted(primes))
    assert M > N
    assert x == N


def test_manual_non_lossless_is_mod_M():
    primes = collect_nice_primes(5)  # torre volutamente piccola
    M = product(primes)

    N = 10**9 + 1234567
    sig = build_tower_signature_manual(N, primes)

    x, M2 = ptc.reconstruct_from_tower_signature(sig)
    assert M2 == M
    assert M < N
    assert x == (N % M)


def test_manual_handles_p_divides_N():
    primes = collect_nice_primes(10)
    p_div = primes[3]
    N = p_div * 123456  # garantito r=0 per quel p
    sig = build_tower_signature_manual(N, primes)

    # check che almeno una firma abbia e=None e r=0
    assert any(f.p == p_div and f.r == 0 and f.e is None for f in sig.firme)

    x, M = ptc.reconstruct_from_tower_signature(sig)
    assert M > N
    assert x == N


def test_large_number_roundtrip_lossless_decades_digits():
    primes = collect_nice_primes(25)  # prodotto enorme anche con primi piccoli
    N = int("1234567890" * 3)  # 30 cifre
    sig = build_tower_signature_manual(N, primes)

    x, M = ptc.reconstruct_from_tower_signature(sig)
    assert M > N
    assert x == N


def test_choose_orologi_for_digits_small_range():
    # Testa la logica di scelta senza il range 32-bit (che è “da demo”, non da test).
    D = 20
    chosen = ptc.choose_orologi_for_digits(
        D,
        anchor=ptc.DEFAULT_ANCHOR,
        smooth_primes=ptc.DEFAULT_SMOOTH_PRIMES,
        min_p=3,
        max_p=500_000,
    )
    ps = [p for p, _ in chosen]

    assert ps[0] == ptc.DEFAULT_ANCHOR

    M = 1
    for p, fac in chosen:
        # fac deve descrivere una fattorizzazione smooth completa di (p-1) e 2 deve essere generatore
        f2, rem = ptc.factor_smooth(p - 1, ptc.DEFAULT_SMOOTH_PRIMES)
        assert rem == 1
        assert f2 == fac
        assert ptc.is_primitive_root_2(p, fac)
        M *= p

    assert M > 10**D


def test_compute_tower_signature_smoke_single_digit():
    # IMPORTANTISSIMO: D=1 così choose_orologi_for_digits NON entra nel generatore 32-bit.
    N = 7
    sig = ptc.compute_tower_signature(N, anchor=ptc.DEFAULT_ANCHOR, smooth_primes=ptc.DEFAULT_SMOOTH_PRIMES)

    x, M = ptc.reconstruct_from_tower_signature(sig)
    assert M > N
    assert x == N
