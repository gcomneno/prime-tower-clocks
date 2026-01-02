from __future__ import annotations

from ptc_bin import DecodedSignature, read_ptcbin, write_ptcbin
from ptc_model import ClockRec, PTCSig
from reconstruct import reconstruct_from_signature
from tower_dict import TowerDict


def test_ptcbin_roundtrip_small_lossless(tmp_path):
    # N=276 with clocks p=19 (e=17) and p=61 (e=5)
    sig = PTCSig(
        base=2,
        clocks=[
            ClockRec(p=19, z=False, e=17),
            ClockRec(p=61, z=False, e=5),
        ],
        M_bits=11,
        N_bits=9,
        lossless_claim=True,
    )
    td = TowerDict(dict_id=1, primes=(19, 61))

    out = tmp_path / "one.ptcbin"
    write_ptcbin(str(out), base=2, dicts=[td], signatures=[DecodedSignature(dict_id=1, sig=sig)])
    f = read_ptcbin(str(out))

    assert f.header.base == 2
    assert f.dicts[1].primes == (19, 61)
    assert len(f.signatures) == 1

    sig2 = f.signatures[0].sig
    assert [(c.p, c.z, c.e) for c in sig2.clocks] == [(19, False, 17), (61, False, 5)]

    n_mod_m, M, _ = reconstruct_from_signature(sig2)
    assert M > 276
    assert n_mod_m == 276


def test_ptcbin_roundtrip_with_z_marker(tmp_path):
    # N=305 divisible by 61, and N mod 19 = 1 => e=0 works (2^0=1)
    sig = PTCSig(
        base=2,
        clocks=[
            ClockRec(p=19, z=False, e=0),
            ClockRec(p=61, z=True, e=None),
        ],
    )
    td = TowerDict(dict_id=1, primes=(19, 61))

    out = tmp_path / "z.ptcbin"
    write_ptcbin(str(out), base=2, dicts=[td], signatures=[DecodedSignature(dict_id=1, sig=sig)])
    f = read_ptcbin(str(out))

    sig2 = f.signatures[0].sig
    assert [(c.p, c.z, c.e) for c in sig2.clocks] == [(19, False, 0), (61, True, None)]

    n_mod_m, M, _ = reconstruct_from_signature(sig2)
    assert M > 305
    assert n_mod_m == 305
