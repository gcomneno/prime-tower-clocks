from __future__ import annotations

from pathlib import Path

from ptc_bin import read_ptcbin
from ptc_convert import pack_jsonl_to_ptcbin
from ptc_jsonl import dump_signature_jsonl
from ptc_model import ClockRec, PTCSig


def test_pack_groups_by_tower_multi_dict(tmp_path: Path):
    # Two different towers => two dicts in the ptcbin file.
    sig_a = PTCSig(base=2, clocks=[ClockRec(p=19, z=False, e=17), ClockRec(p=61, z=False, e=5)], note="a")
    sig_b = PTCSig(
        base=2,
        clocks=[ClockRec(p=61, z=False, e=5), ClockRec(p=101, z=False, e=1), ClockRec(p=131, z=False, e=2)],
        note="b",
    )

    a_path = tmp_path / "a.jsonl"
    b_path = tmp_path / "b.jsonl"
    dump_signature_jsonl(sig_a, str(a_path), include_summary=False)
    dump_signature_jsonl(sig_b, str(b_path), include_summary=False)

    out_bin = tmp_path / "out.ptcbin"
    counts = pack_jsonl_to_ptcbin([str(a_path), str(b_path)], str(out_bin))

    assert out_bin.exists()
    assert sum(counts.values()) == 2
    assert len(counts) == 2

    f = read_ptcbin(str(out_bin))
    assert len(f.dicts) == 2
    assert len(f.signatures) == 2

    # Ensure dict prime sets are exactly our two towers (order independent)
    towers = {tuple(td.primes) for td in f.dicts.values()}
    assert towers == {(19, 61), (61, 101, 131)}
