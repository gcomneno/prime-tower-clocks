#!/usr/bin/env python3
"""PTC benchmark: JSONL vs (JSONL+gzip/zstd) vs PTC-bin.

This script measures:
  - Size: sum(JSONL files), gzip(JSONL stream), zstd(JSONL stream if available), PTC-bin
  - Time: pack (JSONL -> PTC-bin), unpack (PTC-bin -> JSONL), gzip/zstd encode time

It also reports:
  - bytes/signature
  - ms/signature (avg)

Two modes:

  A) Benchmark an existing directory of JSONL signatures:
      python3 tools/bench_pack.py --jsonl-dir out/ --outdir bench_out

  B) (Optional) Generate a dataset first (calls your CLI once per N; slower):
      python3 tools/bench_pack.py --generate 1000 --digits 50 --preset fit --outdir bench_out

Notes:
  - The JSONL "stream" for gzip/zstd is built by concatenating all JSONL files (best-case for redundancy).
  - PTC-bin is produced using ptc_convert.pack_jsonl_to_ptcbin (your glue layer).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sum_bytes(paths: list[Path]) -> int:
    return sum(p.stat().st_size for p in paths)


def _collect_jsonl_files(dir_path: Path) -> list[Path]:
    if not dir_path.exists():
        raise FileNotFoundError(dir_path)
    files = sorted([p for p in dir_path.rglob("*.jsonl") if p.is_file()])
    if not files:
        raise ValueError(f"No .jsonl files found under: {dir_path}")
    return files


def _concat_jsonl(files: list[Path], out_path: Path) -> None:
    # Best-case compression: one big stream (no per-file reset).
    with out_path.open("wb") as out:
        for p in files:
            out.write(p.read_bytes())
            out.write(b"\n")


def _gzip_file(in_path: Path, out_path: Path) -> float:
    t0 = time.perf_counter()
    with in_path.open("rb") as fin, gzip.open(out_path, "wb", compresslevel=9) as fout:
        while True:
            b = fin.read(1024 * 1024)
            if not b:
                break
            fout.write(b)
    return time.perf_counter() - t0


def _zstd_available() -> bool:
    try:
        import zstandard  # noqa: F401
    except Exception:
        return False
    return True


def _zstd_file(in_path: Path, out_path: Path, level: int = 9) -> float:
    import zstandard as zstd  # type: ignore

    t0 = time.perf_counter()
    cctx = zstd.ZstdCompressor(level=level)
    with in_path.open("rb") as fin, out_path.open("wb") as fout:
        with cctx.stream_writer(fout) as zw:
            while True:
                b = fin.read(1024 * 1024)
                if not b:
                    break
                zw.write(b)
    return time.perf_counter() - t0


def _run_min_avg(fn, runs: int) -> tuple[float, float]:
    times: list[float] = []
    for _ in range(runs):
        times.append(fn())
    return (min(times), sum(times) / len(times))


def _rand_int_with_digits(rng: random.Random, digits: int) -> int:
    if digits <= 0:
        raise ValueError("digits must be > 0")
    if digits == 1:
        return rng.randint(0, 9)
    first = rng.randint(1, 9)
    rest = [str(rng.randint(0, 9)) for _ in range(digits - 1)]
    return int(str(first) + "".join(rest))


def _generate_jsonl_dataset(
    *,
    count: int,
    digits: int,
    preset: str,
    out_dir: Path,
    seed: int,
) -> list[Path]:
    """Generate JSONL files by calling your CLI once per N (slow but version-proof)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    script = ROOT / "prime_tower_clocks.py"
    if not script.exists():
        raise FileNotFoundError(f"Missing {script} (run from repo root)")

    jsonl_files: list[Path] = []
    for i in range(1, count + 1):
        N = _rand_int_with_digits(rng, digits)
        path = out_dir / f"sig_{i:05d}.jsonl"
        cmd = [
            sys.executable,
            str(script),
            str(N),
            "--preset",
            preset,
            "--dump-jsonl",
            str(path),
        ]
        # silence CLI output for bench cleanliness
        rc = os.spawnve(os.P_WAIT, sys.executable, cmd, os.environ)
        if rc != 0:
            raise RuntimeError(f"CLI generation failed (rc={rc}) on i={i} N={N}")
        jsonl_files.append(path)

    return jsonl_files


def _pack_ptcbin(jsonl_paths: list[Path], out_path: Path) -> tuple[float, dict[int, int]]:
    from ptc_convert import pack_jsonl_to_ptcbin

    t0 = time.perf_counter()
    counts = pack_jsonl_to_ptcbin([str(p) for p in jsonl_paths], str(out_path))
    dt = time.perf_counter() - t0
    return dt, counts


def _unpack_ptcbin(in_path: Path, out_dir: Path) -> float:
    from ptc_convert import unpack_ptcbin_to_jsonl

    if out_dir.exists():
        for p in out_dir.glob("*.jsonl"):
            p.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    unpack_ptcbin_to_jsonl(str(in_path), str(out_dir), prefix="unpack", include_summary=True)
    return time.perf_counter() - t0


def _write_docs(out_path: Path, report_md: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md, encoding="utf-8")


def _md_table_row(cols: list[Any]) -> str:
    return "| " + " | ".join(str(c) for c in cols) + " |"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Benchmark JSONL vs gzip/zstd vs PTC-bin.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--jsonl-dir", type=str, help="Directory containing *.jsonl signatures")
    src.add_argument("--generate", type=int, help="Generate COUNT JSONL signatures first (slow)")

    ap.add_argument("--digits", type=int, default=50, help="Digits for generated N (generate mode). Default: 50")
    ap.add_argument("--preset", type=str, default="fit", help="Preset for generation. Default: fit")
    ap.add_argument("--seed", type=int, default=12345, help="RNG seed (generate mode)")
    ap.add_argument("--outdir", type=str, default="bench_out", help="Output directory for artifacts")
    ap.add_argument("--runs", type=int, default=3, help="Number of runs per timed operation (min+avg). Default: 3")
    ap.add_argument("--write-docs", action="store_true", help="Write docs/bench.md with the results")
    args = ap.parse_args(argv)

    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    # dataset source
    if args.jsonl_dir:
        jsonl_files = _collect_jsonl_files(ROOT / args.jsonl_dir)
        dataset_tag = f"dir:{args.jsonl_dir}"
    else:
        gen_dir = outdir / "generated_jsonl"
        jsonl_files = _generate_jsonl_dataset(
            count=int(args.generate),
            digits=int(args.digits),
            preset=str(args.preset),
            out_dir=gen_dir,
            seed=int(args.seed),
        )
        dataset_tag = f"gen:{args.generate}x{args.digits}d preset={args.preset} seed={args.seed}"

    n_sigs = len(jsonl_files)

    def bps(x: int) -> str:
        return f"{(x / n_sigs):.1f}" if n_sigs else "n/a"

    def msps(avg_s: float) -> str:
        return f"{(avg_s * 1000.0 / n_sigs):.3f}" if n_sigs else "n/a"

    # sizes
    jsonl_total = _sum_bytes(jsonl_files)

    concat_path = outdir / "dataset.concat.jsonl"
    _concat_jsonl(jsonl_files, concat_path)
    concat_bytes = concat_path.stat().st_size

    gz_path = outdir / "dataset.concat.jsonl.gz"
    zst_path = outdir / "dataset.concat.jsonl.zst"

    # gzip timing
    gz_min, gz_avg = _run_min_avg(lambda: _gzip_file(concat_path, gz_path), args.runs)
    gz_bytes = gz_path.stat().st_size

    # zstd timing (optional)
    zstd_ok = _zstd_available()
    if zstd_ok:
        zst_min, zst_avg = _run_min_avg(lambda: _zstd_file(concat_path, zst_path, level=9), args.runs)
        zst_bytes = zst_path.stat().st_size
    else:
        zst_min = zst_avg = 0.0
        zst_bytes = 0

    # ptcbin timing
    ptcbin_path = outdir / "dataset.ptcbin"
    pack_min, pack_avg = _run_min_avg(lambda: _pack_ptcbin(jsonl_files, ptcbin_path)[0], args.runs)
    ptcbin_bytes = ptcbin_path.stat().st_size

    # unpack timing
    unpack_dir = outdir / "unpacked_jsonl"
    unpack_min, unpack_avg = _run_min_avg(lambda: _unpack_ptcbin(ptcbin_path, unpack_dir), args.runs)

    # report
    env = {
        "python": sys.version.split()[0],
        "platform": os.uname().sysname + " " + os.uname().release,
        "cwd": str(ROOT),
    }

    lines: list[str] = []
    lines.append("# PTC benchmark results")
    lines.append("")
    lines.append(f"- Dataset: `{dataset_tag}`")
    lines.append(f"- Files: {n_sigs} JSONL signature file(s)")
    lines.append(f"- Python: `{env['python']}`")
    lines.append(f"- Platform: `{env['platform']}`")
    lines.append(f"- Runs per operation: {args.runs} (reported min+avg)")
    lines.append("")
    lines.append("## Sizes")
    lines.append("")
    lines.append("| Artifact | Bytes | Bytes/sig | Notes |")
    lines.append("|---|---:|---:|---|")
    lines.append(_md_table_row(["JSONL files (sum)", jsonl_total, bps(jsonl_total), "sum of per-signature files"]))
    lines.append(_md_table_row(["JSONL concat", concat_bytes, bps(concat_bytes), "single stream (best-case)"]))
    lines.append(
        _md_table_row(["gzip(JSONL concat)", gz_bytes, bps(gz_bytes), f"gzip -9; sha256={_sha256(gz_path)[:12]}…"])
    )
    if zstd_ok:
        lines.append(
            _md_table_row(
                ["zstd(JSONL concat)", zst_bytes, bps(zst_bytes), f"zstd -9; sha256={_sha256(zst_path)[:12]}…"]
            )
        )
    else:
        lines.append(_md_table_row(["zstd(JSONL concat)", "n/a", "n/a", "install `zstandard` to enable"]))
    lines.append(_md_table_row(["PTC-bin", ptcbin_bytes, bps(ptcbin_bytes), f"sha256={_sha256(ptcbin_path)[:12]}…"]))
    lines.append("")
    lines.append("## Timings")
    lines.append("")
    lines.append("| Operation | min (s) | avg (s) | ms/sig (avg) | Notes |")
    lines.append("|---|---:|---:|---:|---|")
    lines.append(
        _md_table_row(["gzip encode", f"{gz_min:.4f}", f"{gz_avg:.4f}", msps(gz_avg), "dataset.concat.jsonl -> .gz"])
    )
    if zstd_ok:
        lines.append(
            _md_table_row(
                ["zstd encode", f"{zst_min:.4f}", f"{zst_avg:.4f}", msps(zst_avg), "dataset.concat.jsonl -> .zst"]
            )
        )
    else:
        lines.append(_md_table_row(["zstd encode", "n/a", "n/a", "n/a", "install `zstandard` to enable"]))
    lines.append(
        _md_table_row(["pack", f"{pack_min:.4f}", f"{pack_avg:.4f}", msps(pack_avg), "JSONL files -> dataset.ptcbin"])
    )
    lines.append(
        _md_table_row(
            ["unpack", f"{unpack_min:.4f}", f"{unpack_avg:.4f}", msps(unpack_avg), "dataset.ptcbin -> JSONL files"]
        )
    )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- gzip/zstd numbers are for a *single concatenated stream* (best-case for text redundancy).")
    lines.append("- PTC-bin includes tower dictionary frames + CRC32; unpack writes one JSONL per signature.")
    lines.append("- If you benchmark a directory, file ordering is lexicographic by path (stable).")
    lines.append("")

    report = "\n".join(lines)

    print(report)

    if args.write_docs:
        docs_path = ROOT / "docs" / "bench.md"
        _write_docs(docs_path, report + "\n")
        print(f"[docs] wrote: {docs_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
