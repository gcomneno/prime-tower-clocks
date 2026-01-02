from __future__ import annotations

from ptc_bin import DecodedSignature, PTCBinError, read_ptcbin, write_ptcbin
from ptc_model import ClockRec, PTCSig
from tower_dict import TowerDict


def test_ptcbin_crc32_detects_corruption(tmp_path):
    sig = PTCSig(
        base=2,
        clocks=[
            ClockRec(p=19, z=False, e=17),
            ClockRec(p=61, z=False, e=5),
        ],
    )
    td = TowerDict(dict_id=1, primes=(19, 61))

    out = tmp_path / "c.ptcbin"
    write_ptcbin(str(out), base=2, dicts=[td], signatures=[DecodedSignature(dict_id=1, sig=sig)])

    data = bytearray(out.read_bytes())
    # flip a byte somewhere after the header (5 bytes)
    data[12] ^= 0x01
    bad = tmp_path / "bad.ptcbin"
    bad.write_bytes(bytes(data))

    try:
        read_ptcbin(str(bad))
    except PTCBinError as e:
        assert "CRC32 mismatch" in str(e)
        return

    raise AssertionError("expected CRC error")
