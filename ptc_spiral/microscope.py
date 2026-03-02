from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from random import Random
from typing import Sequence
import math


@dataclass(frozen=True)
class LevelStats:
    k: int
    p: int
    M: int
    non_empty: int
    coverage: float
    max_bucket: int
    top3: list[tuple[int, int]]

    # theoretical metrics
    expected_mean: float
    sigma: float
    z_max_bucket: float
    peak_amplification: float


@dataclass(frozen=True)
class MicroscopeConfig:
    primes: list[int]
    N: int
    lo: int
    hi: int
    pairs: int
    seed: int


@dataclass(frozen=True)
class MicroscopeReport:
    mode: str
    config: MicroscopeConfig
    levels: list[LevelStats]
    kstar_counts: dict[str, int]
    kstar_fractions: dict[str, float]
    baseline_random_0: dict[str, float] | None = None
    baseline_random_1: dict[str, float] | None = None
    anomaly_score_L1: float | None = None
    noise_floor_L1: float | None = None
    signal_to_noise: float | None = None
    verdict: dict[str, object] | None = None


def cumulative_products(primes: list[int]) -> list[int]:
    Ms: list[int] = []
    m = 1
    for p in primes:
        m *= p
        Ms.append(m)
    return Ms


def coverage_ratio(non_empty: int, N: int, M: int) -> float:
    denom = min(N, M)
    return 0.0 if denom == 0 else non_empty / denom


def level_bucket_stats(values: Sequence[int], primes: list[int]) -> list[LevelStats]:
    Ms = cumulative_products(primes)
    out: list[LevelStats] = []
    N = len(values)

    for k, (p, M) in enumerate(zip(primes, Ms), start=1):
        buckets = Counter(v % M for v in values)
        non_empty = len(buckets)
        max_bucket = max(buckets.values()) if buckets else 0
        top3 = buckets.most_common(3)

        p_uniform = 1.0 / M if M > 0 else 0.0
        expected_mean = N * p_uniform
        sigma = math.sqrt(N * p_uniform * (1 - p_uniform)) if p_uniform > 0 else 0.0

        # z-score valido solo in regime non sparso
        if expected_mean >= 5 and sigma > 0:
            z_max_bucket = (max_bucket - expected_mean) / sigma
        else:
            z_max_bucket = 0.0

        peak_amplification = (max_bucket / expected_mean) if expected_mean > 0 else 0.0

        out.append(
            LevelStats(
                k=k,
                p=p,
                M=M,
                non_empty=non_empty,
                coverage=coverage_ratio(non_empty, N, M),
                max_bucket=max_bucket,
                top3=top3,
                expected_mean=expected_mean,
                sigma=sigma,
                z_max_bucket=z_max_bucket,
                peak_amplification=peak_amplification,
            )
        )
    return out


def sample_kstar_depths(values: Sequence[int], primes: list[int], *, pairs: int, seed: int) -> Counter[int]:
    rng = Random(seed)
    Ms = cumulative_products(primes)

    def kstar(a: int, b: int) -> int:
        d = a - b
        ks = 0
        for k, M in enumerate(Ms, start=1):
            if d % M == 0:
                ks = k
            else:
                break
        return ks

    depth = Counter()
    n = len(values)
    if n < 2:
        return depth

    for _ in range(pairs):
        i = rng.randrange(n)
        j = rng.randrange(n - 1)
        if j >= i:
            j += 1
        depth[kstar(values[i], values[j])] += 1

    return depth


def depth_fingerprint(depths: Counter[int], K: int) -> dict[str, float]:
    total = sum(depths.values()) or 1
    return {str(k): depths.get(k, 0) / total for k in range(0, K + 1)}


def l1_distance(fp: dict[str, float], base: dict[str, float]) -> float:
    keys = set(fp) | set(base)
    return sum(abs(fp.get(k, 0.0) - base.get(k, 0.0)) for k in keys)


def top_delta_levels(
    fp: dict[str, float],
    base: dict[str, float],
    *,
    K: int,
    topn: int = 3,
) -> list[dict[str, object]]:
    items: list[tuple[int, float]] = []
    for k in range(0, K + 1):
        d = fp.get(str(k), 0.0) - base.get(str(k), 0.0)
        items.append((k, d))
    items.sort(key=lambda t: abs(t[1]), reverse=True)
    out: list[dict[str, object]] = []
    for k, d in items[:topn]:
        out.append({"k": k, "delta": d})
    return out


def diagnose_from_report(
    *,
    fp: dict[str, float],
    base: dict[str, float] | None,
    anomaly: float | None,
    noise: float | None,
    snr: float | None,
    levels: list[LevelStats],
    K: int,
) -> dict[str, object]:

    verdict = "unknown"
    notes: list[str] = []
    hypothesis: list[str] = []
    evidence: list[str] = []

    # --- theoretical sigma detection ---
    max_level = max(
        levels,
        key=lambda s: s.z_max_bucket,
        default=None,
    )

    if max_level is not None:
        max_z = max_level.z_max_bucket
        max_k = max_level.k
        max_M = max_level.M
    else:
        max_z = 0.0
        max_k = None
        max_M = None
        
    if snr is None:
        verdict = "no_baseline"
        notes.append("baseline non calcolata (usa --baseline-random)")
    else:
        if snr < 2.0:
            verdict = "random_like"
        elif snr < 5.0:
            verdict = "weak_structure"
        else:
            verdict = "structured"

    # --- override using theoretical z ---
    if max_z >= 10:
        verdict = "structured"
        notes.append(
            f"extreme_modular_bias_detected "
            f"(max_z={max_z:.2f} at k={max_k}, M={max_M})"
        )
    elif max_z >= 6:
        verdict = "structured"
        notes.append(
            f"strong_modular_bias_detected "
            f"(max_z={max_z:.2f} at k={max_k}, M={max_M})"
        )
    elif max_z >= 3 and verdict == "random_like":
        verdict = "weak_structure"
        notes.append(
            f"moderate_modular_bias_detected "
            f"(max_z={max_z:.2f} at k={max_k}, M={max_M})"
        )

    return {
        "verdict": verdict,
        "snr": snr,
        "anomaly_score_L1": anomaly,
        "noise_floor_L1": noise,
        "max_z_over_levels": max_z,
        "notes": notes,
        "hypothesis": hypothesis,
        "evidence": evidence,
    }


def random_fingerprint(*, primes: list[int], N: int, lo: int, hi: int, pairs: int, seed: int) -> dict[str, float]:
    rng = Random(seed)
    values = [rng.randrange(lo, hi) for _ in range(N)]
    depths = sample_kstar_depths(values, primes, pairs=pairs, seed=seed + 1)
    return depth_fingerprint(depths, len(primes))


def run_microscope(
    values: Sequence[int],
    *,
    mode: str,
    config: MicroscopeConfig,
    baseline_random: bool = False,
) -> MicroscopeReport:

    levels = level_bucket_stats(values, config.primes)
    depths = sample_kstar_depths(values, config.primes, pairs=config.pairs, seed=config.seed + 1)

    K = len(config.primes)
    fp = depth_fingerprint(depths, K)
    kstar_counts = {str(k): depths.get(k, 0) for k in range(0, K + 1)}

    if not baseline_random:
        return MicroscopeReport(
            mode=mode,
            config=config,
            levels=levels,
            kstar_counts=kstar_counts,
            kstar_fractions=fp,
        )

    fp0 = random_fingerprint(
        primes=config.primes,
        N=config.N,
        lo=config.lo,
        hi=config.hi,
        pairs=config.pairs,
        seed=config.seed + 1000,
    )

    fp1 = random_fingerprint(
        primes=config.primes,
        N=config.N,
        lo=config.lo,
        hi=config.hi,
        pairs=config.pairs,
        seed=config.seed + 2000,
    )

    anomaly = l1_distance(fp, fp0)
    noise = l1_distance(fp0, fp1)
    snr = (anomaly / noise) if noise > 0 else float("inf")

    verdict = diagnose_from_report(
        fp=fp,
        base=fp0,
        anomaly=anomaly,
        noise=noise,
        snr=snr,
        levels=levels,
        K=K,
    )

    return MicroscopeReport(
        mode=mode,
        config=config,
        levels=levels,
        kstar_counts=kstar_counts,
        kstar_fractions=fp,
        baseline_random_0=fp0,
        baseline_random_1=fp1,
        anomaly_score_L1=anomaly,
        noise_floor_L1=noise,
        signal_to_noise=snr,
        verdict=verdict,
    )


def report_to_dict(r: MicroscopeReport) -> dict:
    d = {
        "mode": r.mode,
        "config": {
            "primes": r.config.primes,
            "N": r.config.N,
            "lo": r.config.lo,
            "hi": r.config.hi,
            "pairs": r.config.pairs,
            "seed": r.config.seed,
        },
        "levels": [
            {
                "k": s.k,
                "p": s.p,
                "M": s.M,
                "non_empty": s.non_empty,
                "coverage": s.coverage,
                "max_bucket": s.max_bucket,
                "top3": s.top3,
                "expected_mean": s.expected_mean,
                "sigma": s.sigma,
                "z_max_bucket": s.z_max_bucket,
                "peak_amplification": s.peak_amplification,
            }
            for s in r.levels
        ],
        "kstar": r.kstar_counts,
        "kstar_fractions": r.kstar_fractions,
    }

    if r.verdict is not None:
        d["verdict"] = r.verdict

    if r.baseline_random_0 is not None:
        d["baseline_random"] = {
            "kstar_fractions_0": r.baseline_random_0,
            "kstar_fractions_1": r.baseline_random_1,
            "anomaly_score_L1": r.anomaly_score_L1,
            "noise_floor_L1": r.noise_floor_L1,
            "signal_to_noise": r.signal_to_noise,
        }

    return d
