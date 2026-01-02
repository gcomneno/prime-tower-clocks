from __future__ import annotations

from pathlib import Path

import cli
from ptc_jsonl import dump_signature_jsonl
from ptc_model import ClockRec, PTCSig


def test_cli_dispatch_pack_unpack_cat(tmp_path: Path, capsys):
    # Build a tiny JSONL signature (N=276 example)
    sig = PTCSig(
        base=2,
        clocks=[
            ClockRec(p=19, z=False, e=17),
            ClockRec(p=61, z=False, e=5),
        ],
        note="test",
    )
    jsonl_path = tmp_path / "sig.jsonl"
    dump_signature_jsonl(sig, str(jsonl_path), include_summary=True)

    out_bin = tmp_path / "dataset.ptcbin"

    # pack
    rc = cli.main(["pack", "--out", str(out_bin), str(jsonl_path)])
    assert rc == 0
    assert out_bin.exists()

    # cat
    rc = cli.main(["cat", "--in", str(out_bin)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "dicts=" in out
    assert "signatures=" in out

    # unpack
    outdir = tmp_path / "unpacked"
    rc = cli.main(["unpack", "--in", str(out_bin), "--outdir", str(outdir)])
    assert rc == 0
    assert outdir.exists()
    assert any(p.suffix == ".jsonl" for p in outdir.iterdir())
