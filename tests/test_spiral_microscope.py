from __future__ import annotations

from ptc_spiral.microscope import MicroscopeConfig, run_microscope


def _cfg(*, seed: int = 123456) -> MicroscopeConfig:
    # Parametri abbastanza piccoli da essere veloci, ma stabili.
    return MicroscopeConfig(
        primes=[3, 5, 7, 11, 13, 17],
        N=5_000,
        lo=0,
        hi=1_000_000_000,
        pairs=20_000,
        seed=seed,
    )


def test_microscope_snr_multiples_of_1000_is_huge():
    cfg = _cfg()
    values = [i * 1000 for i in range(cfg.N)]

    r = run_microscope(values, mode="multiples_of_1000", config=cfg, baseline_random=True)

    assert r.signal_to_noise is not None
    assert r.noise_floor_L1 is not None
    # Con questi parametri dovrebbe essere enorme; soglia super conservativa:
    assert r.signal_to_noise > 30.0
    # Il noise floor deve restare "piccolo" (stabilità del sampling):
    assert r.noise_floor_L1 < 0.02


def test_microscope_snr_first_primes_is_strong():
    cfg = _cfg()

    # Generatore primi semplice (sufficiente per test)
    primes: list[int] = []
    x = 2
    while len(primes) < cfg.N:
        is_prime = True
        d = 2
        while d * d <= x:
            if x % d == 0:
                is_prime = False
                break
            d += 1 if d == 2 else 2
        if is_prime:
            primes.append(x)
        x += 1 if x == 2 else 2

    r = run_microscope(primes, mode="first_primes", config=cfg, baseline_random=True)

    assert r.signal_to_noise is not None
    # Anche qui segnale molto forte; soglia conservativa:
    assert r.signal_to_noise > 15.0


def test_microscope_snr_powers_of_two_is_detectable():
    cfg = _cfg()
    values = [pow(2, i, cfg.hi) for i in range(cfg.N)]

    r = run_microscope(values, mode="powers_of_2_mod_hi", config=cfg, baseline_random=True)

    assert r.signal_to_noise is not None
    # Segnale debole ma reale: soglia bassa e robusta.
    assert r.signal_to_noise > 3.0
