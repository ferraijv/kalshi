"""Centralized configuration loader for the Kalshi bot."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    key_id: str
    private_key_secret: str = "kalshi_api_key"
    aws_region: str = "us-east-1"
    email_sender: Optional[str] = None
    email_recipient: Optional[str] = None
    demo_mode: bool = False
    tsa_bankroll_dollars: float = 10000.0
    tsa_event_risk_pct: float = 0.015
    tsa_max_market_share_of_event: float = 0.25
    tsa_daily_max_loss_pct: Optional[float] = None
    tsa_max_contracts_per_market: Optional[int] = None
    tsa_min_contracts: int = 1


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return default if raw is None else float(raw)


def _env_optional_float(name: str) -> Optional[float]:
    raw = os.getenv(name)
    if raw is None or raw.strip().lower() in {"", "none", "null"}:
        return None
    return float(raw)


def _env_optional_int(name: str) -> Optional[int]:
    raw = os.getenv(name)
    if raw is None or raw.strip().lower() in {"", "none", "null"}:
        return None
    return int(raw)


def load_config() -> Config:
    """Load configuration from environment (optionally .env)."""
    load_dotenv()

    key_id = os.getenv("KALSHI_KEY_ID")
    if not key_id:
        raise ValueError("KALSHI_KEY_ID is not set. Add it to your environment or .env file.")

    return Config(
        key_id=key_id,
        private_key_secret=os.getenv("KALSHI_PRIVATE_KEY_SECRET", "kalshi_api_key"),
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        email_sender=os.getenv("EMAIL_SENDER"),
        email_recipient=os.getenv("EMAIL_RECIPIENT"),
        demo_mode=os.getenv("DEMO_MODE", "false").lower() == "true",
        tsa_bankroll_dollars=_env_float("TSA_BANKROLL_DOLLARS", 1000.0),
        tsa_event_risk_pct=_env_float("TSA_EVENT_RISK_PCT", 0.015),
        tsa_max_market_share_of_event=_env_float("TSA_MAX_MARKET_SHARE_OF_EVENT", 0.25),
        tsa_daily_max_loss_pct=_env_optional_float("TSA_DAILY_MAX_LOSS_PCT"),
        tsa_max_contracts_per_market=_env_optional_int("TSA_MAX_CONTRACTS_PER_MARKET"),
        tsa_min_contracts=int(_env_float("TSA_MIN_CONTRACTS", 1)),
    )
