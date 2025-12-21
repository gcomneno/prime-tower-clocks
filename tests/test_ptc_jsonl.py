from __future__ import annotations

import json

import pytest

import prime_tower_clocks as ptc
from jsonl_validation import dump_signature_jsonl, load_signature_jsonl
from reconstruct import reconstruct_from_signature
from tests._helpers import build_tower_signature_manual, collect_nice_primes


def test_jsonl_roundtrip_and_reconstruct(tmp_path):
    primes = collect_nice_primes(25)
    N = int("3141592653589793238462643383")  # 28 cifre circa
    sig = build_tower_signature_manual(N, primes)

    jsig = ptc.tower_to_ptcsig(sig, base=2)
    path = tmp_path / "sig.jsonl"

    dump_signature_jsonl(jsig, str(path), include_summary=True)

    loaded = load_signature_jsonl(str(path))
    x, M, lossless_by_bits = reconstruct_from_signature(loaded)

    assert M > N
    assert x == N
    assert lossless_by_bits is True
    assert loaded.lossless_claim is True


def test_jsonl_duplicate_p_rejected(tmp_path):
    path = tmp_path / "bad.jsonl"
    lines = [
        {"type": "ptc", "version": 1, "base": 2},
        {"p": 61, "z": True},
        {"p": 61, "z": False, "e": 0},  # duplicato
    ]
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_signature_jsonl(str(path))
