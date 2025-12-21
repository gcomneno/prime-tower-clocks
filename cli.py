#!/usr/bin/env python3
"""CLI for Prime Tower Clocks.

Usage examples:
  - Build signature + dump JSONL:
      python3 prime_tower_clocks.py 276 --dump-jsonl sig.jsonl

  - Load JSONL + reconstruct:
      python3 prime_tower_clocks.py --load-jsonl sig.jsonl --reconstruct

  - Compare presets quickly:
      python3 prime_tower_clocks.py 276 --preset fast --dump-jsonl fast.jsonl --reconstruct
      python3 prime_tower_clocks.py 276 --preset safe --dump-jsonl safe.jsonl --reconstruct
      python3 prime_tower_clocks.py 276 --preset fit --dump-jsonl fit.jsonl --reconstruct
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


def resolve_clock_strategy(
    *,
    preset: str | None,
    min_p: int | None,
    max_p: int | None,
    pool_limit: int | None,
) -> tuple[str, int, int, int, bool]:
    """Resolve preset + overrides.

    Returns: (preset_effective, min_p, max_p, pool_limit, prefer_large)
    """
    presets: dict[str, tuple[int, int, int, bool]] = {
        # few big clocks (default behavior)
        "minimal": (DEFAULT_32BIT_MIN_P, DEFAULT_32BIT_MAX_P, 5000, True),
        # small/medium clocks, quick
        "fast": (3, 500_000, 20_000, True),
        # more chances to find clocks (bigger range + pool)
        "safe": (3, 2_000_000, 100_000, True),
        # intentionally small clocks first (more clocks, smaller numbers in JSONL)        # "fit": tailor-made last step (minimize overshoot when possible)
        "fit": (3, 2_000_000, 50_000, False),
    }

    preset_eff = "fit" if preset is None else preset
    if preset_eff not in presets:
        raise ValueError(f"Unknown preset: {preset_eff!r}")

    p_min, p_max, lim, prefer_large = presets[preset_eff]

    # Explicit overrides always win
    if min_p is not None:
        p_min = int(min_p)
    if max_p is not None:
        p_max = int(max_p)
    if pool_limit is not None:
        lim = int(pool_limit)

    if p_min < 3:
        raise ValueError("min_p deve essere >= 3")
    if p_max < p_min:
        raise ValueError("max_p deve essere >= min_p")
    if lim <= 0:
        raise ValueError("pool_limit deve essere positivo")

    return preset_eff, p_min, p_max, lim, prefer_large


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Prime Tower Clocks — base 2 + CRT (firma modulare).")
    ap.add_argument("N", nargs="?", help="Numero N (decimale). Omettilo se usi --load-jsonl.")
    ap.add_argument("--dump-jsonl", help="Scrivi firma su JSONL (percorso file).")
    ap.add_argument("--load-jsonl", help="Carica firma da JSONL (percorso file).")
    ap.add_argument(
        "--reconstruct",
        action="store_true",
        help="Ricostruisci N (o N mod M) e stampa un riepilogo.",
    )
    ap.add_argument(
        "--anchor",
        type=int,
        default=DEFAULT_ANCHOR,
        help=f"Primo orologio fisso (default {DEFAULT_ANCHOR}).",
    )
    ap.add_argument(
        "--smooth-primes",
        default=",".join(map(str, DEFAULT_SMOOTH_PRIMES)),
        help="Primi ammessi nella fattorizzazione di (p-1), CSV. Default: 2,3,5,7,11,13",
    )

    ap.add_argument(
        "--preset",
        choices=["minimal", "fast", "safe", "fit"],
        default="fit",
        help=(
            "Preset di torre: minimal (default 32-bit, pochi orologi), "
            "fast (range basso), safe (range più ampio), fit (primi piccoli, più orologi). "
            "I flag --min-p/--max-p/--pool-limit vincono sempre."
        ),
    )
    ap.add_argument("--min-p", type=int, default=None, help="Override: minimo p per gli orologi.")
    ap.add_argument("--max-p", type=int, default=None, help="Override: massimo p per gli orologi.")
    ap.add_argument(
        "--pool-limit",
        type=int,
        default=None,
        help="Override: massimo numero di candidati 'nice primes' da scandire.",
    )

    return ap


def _print_signature_summary(*, N: int, M: int, k: int) -> None:
    N_bits = N.bit_length()
    M_bits = M.bit_length()
    lossless_by_bits = M_bits > N_bits
    print(f"[ptc] k={k}  M_bits={M_bits}  N_bits={N_bits}  lossless_by_bits={lossless_by_bits}")


def main(argv: list[str] | None = None) -> int:
    ap = build_argparser()
    args = ap.parse_args(argv)

    if args.load_jsonl:
        sig = load_signature_jsonl(args.load_jsonl)
        if args.reconstruct:
            n_mod_m, M, lossless_by_bits = reconstruct_from_jsonl(sig)
            k = len(sig.clocks)
            # Here N is unknown (by design). We print what we can.
            print(
                f"[ptc] loaded clocks k={k}  M_bits={sig.M_bits}  N_bits={sig.N_bits}  lossless_by_bits={lossless_by_bits}"
            )
            print(f"[crt] N_mod_M={n_mod_m}")
            print(f"[crt] M={M}")
        return 0

    if args.N is None:
        ap.error("Devi passare N oppure usare --load-jsonl.")

    N = int(args.N)
    smooth_primes = _parse_primes_csv(args.smooth_primes)

    preset_eff, min_p, max_p, pool_limit, prefer_large = resolve_clock_strategy(
        preset=args.preset,
        min_p=args.min_p,
        max_p=args.max_p,
        pool_limit=args.pool_limit,
    )

    sig = compute_tower_signature(
        N,
        anchor=int(args.anchor),
        smooth_primes=smooth_primes,
        min_p=min_p,
        max_p=max_p,
        pool_limit=pool_limit,
        prefer_large=prefer_large,
    )

    print(
        f"[ptc] preset={preset_eff}  min_p={min_p}  max_p={max_p}  pool_limit={pool_limit}  prefer_large={prefer_large}"
    )
    _print_signature_summary(N=N, M=sig.M, k=len(sig.firme))

    if args.dump_jsonl:
        dump_signature_jsonl(tower_to_ptcsig(sig), args.dump_jsonl)
        print(f"[io] wrote {args.dump_jsonl}")

    if args.reconstruct:
        n_mod_m, M = reconstruct_from_tower_signature(sig)
        print(f"[crt] N_mod_M={n_mod_m}")
        print(f"[crt] M={M}")
        # If signature is lossless we can assert reconstruction == N
        if M > N:
            print(f"[crt] reconstructed N={n_mod_m}  (lossless: M>N)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
