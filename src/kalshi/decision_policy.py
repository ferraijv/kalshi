"""Entry-policy configuration and gating rules for TSA contract decisions.

This module is intentionally small and explicit so policy behavior is easy to reason about.
The backtest and live code should use the same gating semantics whenever possible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EntryPolicyConfig:
    """Configurable trade-entry gates for probability-driven decisions.

    Field semantics:
    - ``min_edge``:
      Minimum required expected edge for a trade, where edge is
      ``side_probability - side_price``. ``None`` disables this gate.
    - ``no_trade_prob_band``:
      Half-width around ``0.5`` for P(YES) where trades are blocked.
      Example: ``0.02`` blocks ``[0.48, 0.52]``.
    - ``max_side_price``:
      Maximum allowed entry price for the chosen side.
      Example: if side is ``yes``, side_price is YES price; if side is ``no``,
      side_price is NO price.
    - ``max_spread``:
      Maximum allowed YES bid/ask spread from market data.
      If this is set and spread is unavailable, the trade is rejected.

    Defaults are permissive to preserve backward behavior:
    no gate blocks a trade unless explicitly configured.
    """

    min_edge: Optional[float] = None
    no_trade_prob_band: float = 0.0
    max_side_price: Optional[float] = None
    max_spread: Optional[float] = None


@dataclass(frozen=True)
class EntryDecision:
    """Decision result for whether a candidate trade passes entry gates.

    ``reject_reason`` is one of:
    - ``no_trade_prob_band``
    - ``min_edge``
    - ``max_side_price``
    - ``missing_spread``
    - ``max_spread``
    """

    allow_trade: bool
    reject_reason: Optional[str] = None


def evaluate_entry(
    config: EntryPolicyConfig,
    *,
    prob_yes: float,
    edge: float,
    side_price: float,
    spread: Optional[float],
) -> EntryDecision:
    """Return whether a candidate trade passes configured entry gates.

    Gate evaluation order matters and is fixed:
    1) no-trade probability band
    2) minimum edge
    3) max side price
    4) max spread (or missing spread if spread is required)

    The first failing rule determines ``reject_reason``.
    """
    if config.no_trade_prob_band > 0.0 and abs(prob_yes - 0.5) <= config.no_trade_prob_band:
        return EntryDecision(allow_trade=False, reject_reason="no_trade_prob_band")
    if config.min_edge is not None and edge < config.min_edge:
        return EntryDecision(allow_trade=False, reject_reason="min_edge")
    if config.max_side_price is not None and side_price > config.max_side_price:
        return EntryDecision(allow_trade=False, reject_reason="max_side_price")
    if config.max_spread is not None:
        if spread is None:
            return EntryDecision(allow_trade=False, reject_reason="missing_spread")
        if spread > config.max_spread:
            return EntryDecision(allow_trade=False, reject_reason="max_spread")
    return EntryDecision(allow_trade=True)
