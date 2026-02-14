import datetime

from src.kalshi import place_tsa_orders
from src.kalshi import risk_controls


class FakeClient:
    def __init__(self):
        self.created = []

    def get_orders(self, event_ticker=None):
        return {"orders": []}

    def create_order(self, ticker=None, client_order_id=None, **kwargs):
        self.created.append({"ticker": ticker, **kwargs})
        return {"ok": True}


def test_create_limit_orders_sizes_by_risk_budget(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(place_tsa_orders.shared, "login", lambda use_demo=True: client)
    monkeypatch.setattr(place_tsa_orders.shared, "create_tsa_event_id", lambda *_args, **_kwargs: "KXTSAW-25DEC07")
    monkeypatch.setattr(place_tsa_orders.shared, "get_next_sunday", lambda reference_date=None: "25DEC07")

    likelihoods = {
        "KXTSAW-25DEC07-A2.45": {"true_value": 0.8, "side": "yes", "floor_strike": 2_450_000},
        "KXTSAW-25DEC07-A2.50": {"true_value": 0.8, "side": "yes", "floor_strike": 2_500_000},
    }
    cfg = risk_controls.RiskConfig(
        bankroll_dollars=100.0,
        event_risk_pct=0.10,  # event budget=10
        max_market_share_of_event=1.0,  # market budget=10
    )
    orders = place_tsa_orders.create_limit_orders_for_all_contracts(
        likelihoods,
        run_date=datetime.date(2025, 12, 1),
        risk_config=cfg,
    )
    # First order consumes floor(10/0.60)=16 contracts, second skipped due remaining 0.4
    assert len(orders) == 1
    assert orders[0]["count"] == 16
    assert len(client.created) == 1
