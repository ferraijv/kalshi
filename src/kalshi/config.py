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
    )

