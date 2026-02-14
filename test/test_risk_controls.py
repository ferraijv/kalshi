import datetime

from src.kalshi import risk_controls


def test_contracts_for_order_respects_event_and_market_budgets():
    cfg = risk_controls.RiskConfig(
        bankroll_dollars=100.0,
        event_risk_pct=0.10,  # event budget = 10
        max_market_share_of_event=0.50,  # market budget = 5
    )
    state = risk_controls.RiskState()
    contracts, reason = risk_controls.contracts_for_order(
        cfg,
        state,
        event_id="KXTSAW-25DEC07",
        market_ticker="KXTSAW-25DEC07-A2.45",
        side_price=0.60,
        trade_date=datetime.date(2025, 12, 1),
    )
    # floor(5 / 0.6) = 8
    assert contracts == 8
    assert reason is None


def test_contracts_for_order_rejects_daily_stop():
    cfg = risk_controls.RiskConfig(
        bankroll_dollars=1000.0,
        event_risk_pct=0.10,
        max_market_share_of_event=0.50,
        daily_max_loss_pct=0.01,
    )
    day = datetime.date(2025, 12, 1)
    state = risk_controls.RiskState(daily_realized_pnl={day: -10.0})
    contracts, reason = risk_controls.contracts_for_order(
        cfg,
        state,
        event_id="KXTSAW-25DEC07",
        market_ticker="KXTSAW-25DEC07-A2.45",
        side_price=0.50,
        trade_date=day,
    )
    assert contracts == 0
    assert reason == "daily_max_loss_stop"


def test_record_trade_updates_state():
    state = risk_controls.RiskState()
    day = datetime.date(2025, 12, 1)
    risk_controls.record_trade(
        state,
        event_id="KXTSAW-25DEC07",
        market_ticker="KXTSAW-25DEC07-A2.45",
        trade_date=day,
        side_price=0.5,
        contracts=4,
        pnl=1.2,
    )
    assert state.event_risk_used["KXTSAW-25DEC07"] == 2.0
    assert state.market_risk_used[("KXTSAW-25DEC07", "KXTSAW-25DEC07-A2.45")] == 2.0
    assert state.daily_realized_pnl[day] == 1.2
