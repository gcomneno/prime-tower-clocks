from __future__ import annotations

from cli import resolve_clock_strategy


def test_preset_fast_sets_expected_defaults():
    preset, min_p, max_p, pool_limit, prefer_large = resolve_clock_strategy(
        preset="fast",
        min_p=None,
        max_p=None,
        pool_limit=None,
    )
    assert preset == "fast"
    assert min_p == 3
    assert max_p == 500_000
    assert pool_limit == 20_000
    assert prefer_large is True


def test_preset_fit_sets_expected_defaults_and_strategy():
    preset, min_p, max_p, pool_limit, prefer_large = resolve_clock_strategy(
        preset="fit",
        min_p=None,
        max_p=None,
        pool_limit=None,
    )
    assert preset == "fit"
    assert min_p == 3
    assert max_p == 2_000_000
    assert pool_limit == 50_000
    assert prefer_large is False


def test_overrides_win_over_preset():
    preset, min_p, max_p, pool_limit, prefer_large = resolve_clock_strategy(
        preset="safe",
        min_p=11,
        max_p=999,
        pool_limit=123,
    )
    assert preset == "safe"
    assert min_p == 11
    assert max_p == 999
    assert pool_limit == 123
    assert prefer_large is True


def test_default_preset_is_fit_when_unspecified():
    preset, min_p, max_p, pool_limit, prefer_large = resolve_clock_strategy(
        preset=None,
        min_p=None,
        max_p=None,
        pool_limit=None,
    )
    assert preset == "fit"
    assert min_p == 3
    assert max_p == 2_000_000
    assert pool_limit == 50_000
    assert prefer_large is False
