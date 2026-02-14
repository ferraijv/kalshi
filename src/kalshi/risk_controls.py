"""Risk controls and position sizing helpers for TSA event trading."""

from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class RiskConfig:
    """Sizing and hard-risk limits for TSA trading."""

    bankroll_dollars: float = 1000.0
    event_risk_pct: float = 0.015
    max_market_share_of_event: float = 0.25
    daily_max_loss_pct: Optional[float] = None
    min_contracts: int = 1
    max_contracts_per_market: Optional[int] = None


@dataclass
class RiskState:
    """Mutable risk state used while evaluating sequential order candidates."""

    event_risk_used: Dict[str, float] = field(default_factory=dict)
    market_risk_used: Dict[Tuple[str, str], float] = field(default_factory=dict)
    daily_realized_pnl: Dict[datetime.date, float] = field(default_factory=dict)


def event_risk_budget_dollars(config: RiskConfig) -> float:
    """Return absolute dollar risk budget for one event."""
    return config.bankroll_dollars * config.event_risk_pct


def market_risk_budget_dollars(config: RiskConfig) -> float:
    """Return per-market dollar risk budget within an event."""
    return event_risk_budget_dollars(config) * config.max_market_share_of_event


def daily_max_loss_dollars(config: RiskConfig) -> Optional[float]:
    """Return optional absolute daily max loss threshold."""
    if config.daily_max_loss_pct is None:
        return None
    return config.bankroll_dollars * config.daily_max_loss_pct


def _contracts_from_budget(side_price: float, budget: float) -> int:
    if side_price <= 0.0 or budget <= 0.0:
        return 0
    return int(math.floor(budget / side_price))


def contracts_for_order(
    config: RiskConfig,
    state: RiskState,
    *,
    event_id: str,
    market_ticker: str,
    side_price: float,
    trade_date: datetime.date,
) -> tuple[int, Optional[str]]:
    """Return (contracts, reject_reason) based on risk budgets and stop rules."""
    max_loss = daily_max_loss_dollars(config)
    day_pnl = float(state.daily_realized_pnl.get(trade_date, 0.0))
    if max_loss is not None and day_pnl <= -max_loss:
        return 0, "daily_max_loss_stop"

    event_budget = event_risk_budget_dollars(config)
    market_budget = market_risk_budget_dollars(config)
    event_used = float(state.event_risk_used.get(event_id, 0.0))
    market_used = float(state.market_risk_used.get((event_id, market_ticker), 0.0))
    event_remaining = max(0.0, event_budget - event_used)
    market_remaining = max(0.0, market_budget - market_used)
    if event_remaining <= 0.0:
        return 0, "event_cap"
    if market_remaining <= 0.0:
        return 0, "market_cap"

    contracts = _contracts_from_budget(side_price=side_price, budget=min(event_remaining, market_remaining))
    if config.max_contracts_per_market is not None:
        contracts = min(contracts, config.max_contracts_per_market)
    if contracts < config.min_contracts:
        return 0, "insufficient_budget"
    return contracts, None


def record_trade(
    state: RiskState,
    *,
    event_id: str,
    market_ticker: str,
    trade_date: datetime.date,
    side_price: float,
    contracts: int,
    pnl: float,
) -> None:
    """Update risk state after accepting a trade."""
    notional_risk = side_price * contracts
    state.event_risk_used[event_id] = float(state.event_risk_used.get(event_id, 0.0) + notional_risk)
    key = (event_id, market_ticker)
    state.market_risk_used[key] = float(state.market_risk_used.get(key, 0.0) + notional_risk)
    state.daily_realized_pnl[trade_date] = float(state.daily_realized_pnl.get(trade_date, 0.0) + pnl)


def event_id_from_market_ticker(market_ticker: str) -> str:
    """Return event id prefix from market ticker."""
    if "-" not in market_ticker:
        return market_ticker
    return market_ticker.rsplit("-", 1)[0]
