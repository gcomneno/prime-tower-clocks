#!/usr/bin/env python3
"""CLI for Prime Tower Clocks.

Usage examples:
  - Build signature + dump JSONL:
      python3 prime_tower_clocks.py 276 --dump-jsonl sig.jsonl

  - Load JSONL + reconstruct:
      python3 prime_tower_clocks.py --load-jsonl sig.jsonl --reconstruct
"""

from __future__ import annotations

import argparse

from jsonl_validation import dump_signature_jsonl, load_signature_jsonl
from prime_tower_clocks import (
    DEFAULT_32BIT_MAX_P,
    DEFAULT_32BIT_MIN_P,
    DEFAULT_ANCHOR,
    DEFAULT_SMOOTH_PRIMES,
    _parse_primes_csv,
    compute_tower_signature,
    reconstruct_from_tower_signature,
    tower_to_ptcsig,
)
from reconstruct import reconstruct_from_signature as reconstruct_from_jsonl


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Torre degli Orologi (Prime Tower Clocks) — base 2 + CRT.")
    ap.add_argument("N", nargs="?", help="Numero N (decimale). Omettilo se usi --load-jsonl.")
    ap.add_argument(
        "--anchor",
        type=int,
        default=DEFAULT_ANCHOR,
        help=f"Primo orologio (default {DEFAULT_ANCHOR}).",
    )
    ap.add_argument(
        "--smooth-primes",
        default=",".join(map(str, DEFAULT_SMOOTH_PRIMES)),
        help="Lista di primi per la smoothness di (p-1), CSV. Default: 2,3,5,7,11,13",
    )
    ap.add_argument(
        "--min-p",
        type=int,
        default=None,
        help="Minimo p per la ricerca degli orologi. Default: range 32-bit (2^31).",
    )
    ap.add_argument(
        "--max-p",
        type=int,
        default=None,
        help="Massimo p per la ricerca degli orologi. Default: range 32-bit (2^32-1).",
    )
    ap.add_argument(
        "--pool-limit",
        type=int,
        default=5000,
        help="Numero massimo di candidati 'nice' provati per costruire la torre (default: 5000).",
    )

    ap.add_argument("--dump-jsonl", metavar="PATH", help="Salva la firma (minima) in JSONL.")
    ap.add_argument("--load-jsonl", metavar="PATH", help="Carica firma JSONL.")
    ap.add_argument("--reconstruct", action="store_true", help="Esegue CRT: ricostruisce N (o N mod M).")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_argparser()
    args = ap.parse_args(argv)

    # --- LOAD MODE ---------------------------------------------------------
    if args.load_jsonl:
        jsig = load_signature_jsonl(args.load_jsonl)

        print(f"[jsonl] base={jsig.base} clocks={len(jsig.clocks)}")
        if jsig.created_utc:
            print(f"[jsonl] created_utc={jsig.created_utc}")
        if jsig.note:
            print(f"[jsonl] note={jsig.note}")

        if args.reconstruct:
            n_mod_m, M, lossless = reconstruct_from_jsonl(jsig)
            print()
            print(f"CRT: N ≡ {n_mod_m} (mod {M})")
            if jsig.M_bits is not None and jsig.N_bits is not None:
                print(f"lossless_by_bits={lossless} (M_bits={jsig.M_bits}, N_bits={jsig.N_bits})")
            else:
                print("lossless_by_bits=UNKNOWN (manca M_bits/N_bits nel summary)")
        return 0

    # --- NORMAL MODE -------------------------------------------------------
    if args.N is None:
        ap.error("Devi fornire N oppure usare --load-jsonl")

    N = int(args.N)
    smooth_primes = _parse_primes_csv(args.smooth_primes)

    min_p = DEFAULT_32BIT_MIN_P if args.min_p is None else int(args.min_p)
    max_p = DEFAULT_32BIT_MAX_P if args.max_p is None else int(args.max_p)

    sig = compute_tower_signature(
        N,
        anchor=args.anchor,
        smooth_primes=smooth_primes,
        min_p=min_p,
        max_p=max_p,
        pool_limit=int(args.pool_limit),
    )

    print(f"N={sig.N}  (D={sig.D} cifre)")
    print(f"anchor={args.anchor}  smooth_primes={smooth_primes}")
    print(f"range_p=[{min_p}..{max_p}]  pool_limit={int(args.pool_limit)}")
    print(f"orologi={sig.orologi}")
    print(f"M=Πp = {sig.M}")
    print()
    print("Firma per orologio (p):")
    print("  p          r=N mod p    e (se r!=0)   note")
    print("  ------------------------------------------------------------")
    for f in sig.firme:
        if f.r == 0:
            note = "p divide N -> e non esiste"
            e_str = "-"
        else:
            note = ""
            e_str = str(f.e)
        print(f"  {f.p:<10d} {f.r:<11d} {e_str:<12s} {note}")

    if args.dump_jsonl:
        jsig = tower_to_ptcsig(sig, base=2)
        dump_signature_jsonl(jsig, args.dump_jsonl, include_summary=True)
        print()
        print(f"[jsonl] wrote: {args.dump_jsonl}")

    if args.reconstruct:
        x, M = reconstruct_from_tower_signature(sig)
        print()
        print(f"CRT: N ≡ {x} (mod {M})")
        if M > sig.N:
            print(f"Ricostruzione su range OK: N = {x}")
        else:
            print("Ricostruzione completa NON garantita: M <= N (serve più orologi o orologi più grandi).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())