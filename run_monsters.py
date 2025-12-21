#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import json
import subprocess
import sys


def parse_summary(jsonl_path: Path) -> dict:
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("type") == "summary":
                k = obj.get("k")
                M_bits = obj.get("M_bits")
                N_bits = obj.get("N_bits")
                lossless_claim = obj.get("lossless_claim")
                return {
                    "k": k,
                    "M_bits": M_bits,
                    "N_bits": N_bits,
                    "lossless_claim": lossless_claim,
                }
    raise RuntimeError(f"No summary found in {jsonl_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("monsters_file", help="Text file: one N per line (can include leading zeros).")
    ap.add_argument("--out", default="out", help="Output directory for JSONL + summary.tsv")
    ap.add_argument("--preset", default=None, help="Preset passed to CLI (omit to use CLI default).")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    monsters = []
    for raw in Path(args.monsters_file).read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        monsters.append(raw)

    rows = []
    for raw in monsters:
        jsonl_path = outdir / f"{raw}.jsonl"

        cmd = [sys.executable, "prime_tower_clocks.py", raw, "--dump-jsonl", str(jsonl_path), "--reconstruct"]
        if args.preset is not None:
            cmd[3:3] = ["--preset", args.preset]

        print("\n>>>", " ".join(cmd))
        subprocess.run(cmd, check=True)

        summary = parse_summary(jsonl_path)
        overshoot_bits = None
        if summary["M_bits"] is not None and summary["N_bits"] is not None:
            overshoot_bits = int(summary["M_bits"]) - int(summary["N_bits"])

        rows.append({
            "raw": raw,
            "N_int": int(raw),
            "digits_raw": len(raw),
            "digits_int": len(str(int(raw))),
            "k": summary["k"],
            "M_bits": summary["M_bits"],
            "N_bits": summary["N_bits"],
            "overshoot_bits": overshoot_bits,
            "lossless_claim": summary["lossless_claim"],
            "jsonl": str(jsonl_path),
        })

    tsv = outdir / "summary.tsv"
    cols = ["raw","N_int","digits_raw","digits_int","k","M_bits","N_bits","overshoot_bits","lossless_claim","jsonl"]
    with tsv.open("w", encoding="utf-8") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r[c]) for c in cols) + "\n")

    print("\n[ok] wrote", tsv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
