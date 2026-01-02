"""High-level conversion tools between JSONL signatures and PTC-bin.

This module is the *glue* layer:
  - It may import both JSONL backend and PTC-bin backend.
  - JSONL backend and PTC-bin backend MUST NOT import each other.

CLI:

  Pack one or more JSONL files into a single .ptcbin (auto-groups by tower):

    python3 -m ptc_convert pack --out dataset.ptcbin sig1.jsonl sig2.jsonl

  Unpack a .ptcbin into JSONL files:

    python3 -m ptc_convert unpack --in dataset.ptcbin --outdir out_jsonl/

  Inspect a .ptcbin (dict stats + per-dict signature counts):

    python3 -m ptc_convert cat --in dataset.ptcbin
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from ptc_bin import DecodedSignature, PTCBinError, read_ptcbin, write_ptcbin
from ptc_jsonl import dump_signature_jsonl, load_signature_jsonl
from ptc_model import PTCSig, utc_now_iso
from tower_dict import TowerDict, TowerRegistry


def _tower_key(sig: PTCSig) -> tuple[int, ...]:
    # Canonical tower key: sorted primes
    return tuple(sorted(c.p for c in sig.clocks))


def pack_jsonl_to_ptcbin(jsonl_paths: list[str], out_path: str) -> dict[int, int]:
    """Pack JSONL files into one .ptcbin, auto-grouping by tower.

    Returns: dict_id -> number of signatures packed for that dict.
    """
    if not jsonl_paths:
        raise ValueError("No input JSONL paths")

    registry = TowerRegistry()
    sigs: list[DecodedSignature] = []
    base: int | None = None

    # group counts by dict_id
    counts: Counter[int] = Counter()

    for p in jsonl_paths:
        sig = load_signature_jsonl(p)
        if base is None:
            base = sig.base
        elif sig.base != base:
            raise ValueError(f"Mixed bases are not supported (expected base={base}, got base={sig.base} in {p})")

        primes = _tower_key(sig)
        dict_id = registry.intern(primes)
        sigs.append(DecodedSignature(dict_id=dict_id, sig=sig))
        counts[dict_id] += 1

    assert base is not None

    dicts: list[TowerDict] = registry.all_dicts()
    write_ptcbin(out_path, base=base, dicts=dicts, signatures=sigs)
    return dict(counts)


def unpack_ptcbin_to_jsonl(
    in_path: str,
    out_dir: str,
    *,
    prefix: str = "sig",
    include_summary: bool = True,
) -> list[str]:
    """Unpack a .ptcbin file into individual JSONL signature files."""
    f = read_ptcbin(in_path)
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for i, ds in enumerate(f.signatures, start=1):
        # enrich for human-friendliness (JSONL remains self-contained)
        sig = PTCSig(
            base=ds.sig.base,
            clocks=ds.sig.clocks,
            created_utc=utc_now_iso(),
            note=f"Unpacked from {Path(in_path).name} (dict_id={ds.dict_id}, idx={i})",
            M_bits=ds.sig.M_bits,
            N_bits=ds.sig.N_bits,
            lossless_claim=ds.sig.lossless_claim,
        )
        name = f"{prefix}_{i:04d}_dict{ds.dict_id}.jsonl"
        path = outp / name
        dump_signature_jsonl(sig, str(path), include_summary=include_summary)
        written.append(str(path))
    return written


def _dict_M_bits(td: TowerDict) -> int:
    # Exact bit length of M = Π p (ok for typical k; Python bigints)
    M = 1
    for p in td.primes:
        M *= p
    return M.bit_length()


def _format_flags(flags: int) -> str:
    # Keep it simple, but informative
    parts: list[str] = []
    if flags & 0x01:
        parts.append("CRC32")
    if flags & 0x02:
        parts.append("LEN")
    if flags & 0x04:
        parts.append("BITPACK_E")
    if flags & 0x08:
        parts.append("DELTA_P")
    return "|".join(parts) if parts else "none"


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="ptc_convert",
        description="Convert PTC JSONL signatures <-> PTC-bin (tower dictionary).",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_pack = sub.add_parser("pack", help="Pack JSONL signature files into one .ptcbin (group by tower)")
    p_pack.add_argument("--out", required=True, help="Output .ptcbin path")
    p_pack.add_argument("jsonl", nargs="+", help="Input JSONL paths (one signature per file)")

    p_unpack = sub.add_parser("unpack", help="Unpack a .ptcbin into JSONL signature files")
    p_unpack.add_argument("--in", dest="inp", required=True, help="Input .ptcbin path")
    p_unpack.add_argument("--outdir", required=True, help="Output directory for JSONL files")
    p_unpack.add_argument("--prefix", default="sig", help="Output filename prefix (default: sig)")
    p_unpack.add_argument("--no-summary", action="store_true", help="Do not write JSONL summary line")

    p_cat = sub.add_parser("cat", help="Inspect a .ptcbin file (dicts/signatures summary)")
    p_cat.add_argument("--in", dest="inp", required=True, help="Input .ptcbin path")

    return ap


def _cmd_pack(args: argparse.Namespace) -> int:
    counts = pack_jsonl_to_ptcbin(args.jsonl, args.out)
    total = sum(counts.values())
    nd = len(counts)
    print(f"[pack] wrote {args.out}")
    print(f"[pack] signatures={total}  dicts={nd}")

    # stable order by dict_id
    for dict_id in sorted(counts):
        c = counts[dict_id]
        pct = 100.0 * c / total if total else 0.0
        print(f"  dict_id={dict_id}  count={c}  ({pct:.1f}%)")
    return 0


def _cmd_unpack(args: argparse.Namespace) -> int:
    written = unpack_ptcbin_to_jsonl(
        args.inp,
        args.outdir,
        prefix=args.prefix,
        include_summary=not args.no_summary,
    )
    print(f"[jsonl] wrote {len(written)} file(s) into: {args.outdir}")
    return 0


def _cmd_cat(args: argparse.Namespace) -> int:
    f = read_ptcbin(args.inp)
    total = len(f.signatures)

    # count signatures per dict_id
    sig_counts: Counter[int] = Counter(ds.dict_id for ds in f.signatures)

    print(f"file: {args.inp}")
    print(
        f"base={f.header.base}  version={f.header.version}  flags=0x{f.header.flags:02x}  ({_format_flags(f.header.flags)})"
    )
    print(f"dicts={len(f.dicts)}  signatures={total}")

    for dict_id in sorted(f.dicts):
        td = f.dicts[dict_id]
        k = len(td.primes)
        pmin = td.primes[0]
        pmax = td.primes[-1]
        M_bits = _dict_M_bits(td)

        c = sig_counts.get(dict_id, 0)
        pct = 100.0 * c / total if total else 0.0
        print(f"  dict_id={dict_id}  k={k}  p∈[{pmin}..{pmax}]  M_bits={M_bits}  sigs={c}  ({pct:.1f}%)")

    return 0


def main(argv: list[str] | None = None) -> int:
    ap = build_argparser()
    args = ap.parse_args(argv)

    try:
        if args.cmd == "pack":
            return _cmd_pack(args)
        if args.cmd == "unpack":
            return _cmd_unpack(args)
        if args.cmd == "cat":
            return _cmd_cat(args)
        ap.error("unknown command")
        return 2
    except (PTCBinError, ValueError) as e:
        print(f"[error] {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
