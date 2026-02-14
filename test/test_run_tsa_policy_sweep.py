import pandas as pd

from src.kalshi import run_tsa_policy_sweep
from src.kalshi.decision_policy import EntryPolicyConfig


def test_parse_optional_float_grid_accepts_none_and_values():
    parsed = run_tsa_policy_sweep._parse_optional_float_grid("none,0.01,0.02", default_none=True)
    assert parsed == [None, 0.01, 0.02]


def test_select_policy_uses_gate_and_ranking():
    baseline = {"pnl_total": 10.0, "max_drawdown": 3.0, "ece": 0.08}
    candidates = pd.DataFrame(
        [
            {
                "min_edge": 0.01,
                "no_trade_prob_band": 0.0,
                "max_side_price": None,
                "max_spread": None,
                "trades": 100.0,
                "pnl_total": 10.0,
                "max_drawdown": 2.9,
                "ece": 0.08,
            },
            {
                "min_edge": 0.02,
                "no_trade_prob_band": 0.01,
                "max_side_price": None,
                "max_spread": 0.1,
                "trades": 90.0,
                "pnl_total": 10.2,
                "max_drawdown": 2.7,
                "ece": 0.07,
            },
            {
                "min_edge": 0.03,
                "no_trade_prob_band": 0.02,
                "max_side_price": 0.8,
                "max_spread": 0.1,
                "trades": 70.0,
                "pnl_total": 9.8,
                "max_drawdown": 2.0,
                "ece": 0.06,
            },
        ]
    )
    selected = run_tsa_policy_sweep._select_policy(
        candidates,
        baseline,
        pnl_tolerance=0.0,
        ece_tolerance=0.0,
    )
    assert selected is not None
    assert selected["min_edge"] == 0.02


def test_apply_policy_to_baseline_df_filters_rows():
    df = pd.DataFrame(
        [
            {"prob_yes": 0.70, "edge": 0.03, "side_price": 0.67, "spread": 0.03, "pnl": 0.1, "outcome": 1, "brier": 0.01, "logloss": 0.2, "date": "2025-12-07"},
            {"prob_yes": 0.51, "edge": 0.005, "side_price": 0.505, "spread": 0.08, "pnl": -0.2, "outcome": 0, "brier": 0.25, "logloss": 0.7, "date": "2025-12-14"},
        ]
    )
    policy = EntryPolicyConfig(min_edge=0.01, no_trade_prob_band=0.0, max_side_price=None, max_spread=0.05)
    filtered = run_tsa_policy_sweep._apply_policy_to_baseline_df(df, policy)
    assert len(filtered) == 1
    assert float(filtered.iloc[0]["prob_yes"]) == 0.70
