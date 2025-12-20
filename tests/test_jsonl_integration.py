# tests/test_jsonl_integration.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

import prime_tower_clocks as ptc
from jsonl_validation import dump_signature_jsonl, load_signature_jsonl
from reconstruct import reconstruct_from_signature


def _product(xs: list[int]) -> int:
    out = 1
    for x in xs:
        out *= x
    return out


def _build_tower_signature_manual(N: int, primes: list[int]) -> ptc.TowerSignature:
    """
    Costruisce una TowerSignature senza passare da compute_tower_signature(),
    per evitare la selezione 32-bit dei primi nei test (integrazione deve essere deterministica).

    Usa la stessa logica core:
      r = N mod p
      se r != 0: e tale che 2^e ≡ r (mod p) via Pohlig–Hellman
      se r == 0: marker z (e=None)
    """
    if N < 0:
        raise ValueError("N deve essere non-negativo.")

    ps = sorted(primes)
    firme: list[ptc.Firma] = []
    M = 1

    for p in ps:
        fac = ptc.nice_prime_info(p, ptc.DEFAULT_SMOOTH_PRIMES)
        if fac is None:
            raise ValueError(f"p={p} non è 'nice' rispetto a DEFAULT_SMOOTH_PRIMES={ptc.DEFAULT_SMOOTH_PRIMES}")

        r = N % p
        if r == 0:
            e = None
        else:
            e = ptc.dlog_pohlig_hellman_base2(r, p, fac)

        firme.append(ptc.Firma(p=p, r=r, e=e, phi=p - 1, factors=fac))
        M *= p

    D = len(str(N)) if N != 0 else 1
    return ptc.TowerSignature(N=N, D=D, orologi=ps, firme=firme, M=M)


def test_jsonl_roundtrip_and_reconstruct_lossless(tmp_path: Path):
    # Torre deterministica di "nice primes" piccoli (veloce + zero flakiness)
    primes = [61, 101, 131]  # tutti 'nice' con DEFAULT_SMOOTH_PRIMES nel tuo progetto
    N = 123_456  # < 61*101*131 = 807_091 => lossless garantito

    sig = _build_tower_signature_manual(N, primes)
    jsig = ptc.tower_to_ptcsig(sig, base=2)

    p = tmp_path / "sig.jsonl"
    dump_signature_jsonl(jsig, str(p), include_summary=True)

    jsig2 = load_signature_jsonl(str(p))
    n_mod_m, M, lossless_by_bits = reconstruct_from_signature(jsig2)

    # Summary: deve esserci e deve essere coerente
    assert jsig2.M_bits is not None
    assert jsig2.N_bits is not None
    assert jsig2.lossless_claim is True
    assert lossless_by_bits is True

    # Ricostruzione: lossless => N esatto
    assert M == _product(primes)
    assert M > N
    assert n_mod_m == N


def test_jsonl_validation_rejects_bad_clock(tmp_path: Path):
    # z=true must not include e
    p = tmp_path / "bad.jsonl"
    p.write_text(
        "\n".join(
            [
                json.dumps({"type": "ptc", "version": 1, "base": 2}),
                json.dumps({"p": 61, "z": True, "e": 7}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_signature_jsonl(str(p))
