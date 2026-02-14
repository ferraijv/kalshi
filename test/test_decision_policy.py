from src.kalshi import decision_policy


def test_entry_policy_allows_trade_when_no_gates():
    config = decision_policy.EntryPolicyConfig()
    decision = decision_policy.evaluate_entry(
        config,
        prob_yes=0.55,
        edge=0.01,
        side_price=0.48,
        spread=0.03,
    )
    assert decision.allow_trade
    assert decision.reject_reason is None


def test_entry_policy_rejects_no_trade_band():
    config = decision_policy.EntryPolicyConfig(no_trade_prob_band=0.03)
    decision = decision_policy.evaluate_entry(
        config,
        prob_yes=0.52,
        edge=0.02,
        side_price=0.49,
        spread=0.02,
    )
    assert not decision.allow_trade
    assert decision.reject_reason == "no_trade_prob_band"


def test_entry_policy_rejects_min_edge():
    config = decision_policy.EntryPolicyConfig(min_edge=0.05)
    decision = decision_policy.evaluate_entry(
        config,
        prob_yes=0.65,
        edge=0.02,
        side_price=0.45,
        spread=0.03,
    )
    assert not decision.allow_trade
    assert decision.reject_reason == "min_edge"


def test_entry_policy_rejects_price_and_spread_filters():
    config = decision_policy.EntryPolicyConfig(max_side_price=0.6, max_spread=0.05)
    too_expensive = decision_policy.evaluate_entry(
        config,
        prob_yes=0.75,
        edge=0.06,
        side_price=0.62,
        spread=0.01,
    )
    assert not too_expensive.allow_trade
    assert too_expensive.reject_reason == "max_side_price"

    too_wide = decision_policy.evaluate_entry(
        config,
        prob_yes=0.75,
        edge=0.06,
        side_price=0.58,
        spread=0.08,
    )
    assert not too_wide.allow_trade
    assert too_wide.reject_reason == "max_spread"

    missing_spread = decision_policy.evaluate_entry(
        config,
        prob_yes=0.75,
        edge=0.06,
        side_price=0.58,
        spread=None,
    )
    assert not missing_spread.allow_trade
    assert missing_spread.reject_reason == "missing_spread"
