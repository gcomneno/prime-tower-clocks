import json
from pathlib import Path

import pytest

from jsonl_validation import load_signature_jsonl, dump_signature_jsonl
from reconstruct import reconstruct_from_signature
from prime_tower_clocks import compute_tower_signature, tower_to_ptcsig


def test_jsonl_roundtrip_and_reconstruct_lossless(tmp_path: Path):
    # Small, friendly number. With default clocks, M should usually exceed N.
    N = 276
    sig = compute_tower_signature(N)
    jsig = tower_to_ptcsig(sig, base=2)

    p = tmp_path / "sig.jsonl"
    dump_signature_jsonl(jsig, str(p), include_summary=True)

    jsig2 = load_signature_jsonl(str(p))
    n_mod_m, M, lossless_by_bits = reconstruct_from_signature(jsig2)

    # CRT always gives congruence; when lossless, it equals N exactly.
    assert M > 0
    assert n_mod_m % M == N % M

    if jsig2.M_bits is not None and jsig2.N_bits is not None and lossless_by_bits:
        assert n_mod_m == N


def test_jsonl_validation_rejects_bad_clock(tmp_path: Path):
    # z=true must not include e
    p = tmp_path / "bad.jsonl"
    p.write_text(
        "\n".join([
            json.dumps({"type":"ptc","version":1,"base":2}),
            json.dumps({"p":61,"z":True,"e":7}),
        ]) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_signature_jsonl(str(p))
