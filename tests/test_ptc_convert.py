from __future__ import annotations

from ptc_convert import pack_jsonl_to_ptcbin, unpack_ptcbin_to_jsonl
from ptc_jsonl import dump_signature_jsonl, load_signature_jsonl
from ptc_model import ClockRec, PTCSig


def test_jsonl_to_ptcbin_to_jsonl_roundtrip(tmp_path):
    sig = PTCSig(
        base=2,
        clocks=[
            ClockRec(p=19, z=False, e=17),
            ClockRec(p=61, z=False, e=5),
        ],
        created_utc="2025-12-21T00:00:00Z",
        note="test",
    )

    in_jsonl = tmp_path / "sig.jsonl"
    dump_signature_jsonl(sig, str(in_jsonl), include_summary=True)

    out_bin = tmp_path / "sig.ptcbin"
    pack_jsonl_to_ptcbin([str(in_jsonl)], str(out_bin))

    out_dir = tmp_path / "out"
    written = unpack_ptcbin_to_jsonl(str(out_bin), str(out_dir), prefix="u", include_summary=True)
    assert len(written) == 1

    sig2 = load_signature_jsonl(written[0])
    assert sig2.base == 2
    assert [(c.p, c.z, c.e) for c in sig2.clocks] == [(19, False, 17), (61, False, 5)]
