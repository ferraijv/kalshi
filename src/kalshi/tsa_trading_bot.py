import sys
from pathlib import Path
import datetime
import pandas as pd
import logging


def _ensure_imports():
    """Allow running both as module (-m kalshi.tsa_trading_bot) and as a script."""
    global shared, fetch_all_tsa_data, create_next_week_prediction, get_likelihoods_of_each_contract, create_limit_orders_for_all_contracts

    if __package__:
        from . import shared  # type: ignore
        from .get_recent_tsa_data import fetch_all_tsa_data  # type: ignore
        from .create_next_week_prediction import create_next_week_prediction  # type: ignore
        from .get_current_tsa_market_prices import get_likelihoods_of_each_contract  # type: ignore
        from .place_tsa_orders import create_limit_orders_for_all_contracts  # type: ignore
    else:
        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        import shared  # type: ignore
        from get_recent_tsa_data import fetch_all_tsa_data  # type: ignore
        from create_next_week_prediction import create_next_week_prediction  # type: ignore
        from get_current_tsa_market_prices import get_likelihoods_of_each_contract  # type: ignore
        from place_tsa_orders import create_limit_orders_for_all_contracts  # type: ignore


_ensure_imports()

def _init_logging():
    """Configure run-specific log file under repo logs/."""
    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile = logs_dir / f"tsa_bot_{timestamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(logfile, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    logging.info("Logging initialized")
    logging.info(f"Log file: {logfile}")
    return logfile

def _format_email(prediction: dict, likelihoods: dict, orders) -> str:
    """Create a readable plaintext summary for email."""
    # prediction dict is keyed by date string
    date_key = next(iter(prediction))
    pred = prediction[date_key]
    def as_float(val):
        try:
            return float(val)
        except Exception:
            return val

    summary_lines = [
        f"Prediction date: {date_key}",
        f"Predicted passengers: {as_float(pred.get('prediction', 0)):,}",
        f"YoY adj: {as_float(pred.get('yoy_adjustment', 0)):.3f}",
        f"Day-1 trend: {as_float(pred.get('day_1_trend', 0)):.3f}",
        f"Day-7 trend: {as_float(pred.get('day_7_trend', 0)):.3f}",
        f"Last year (same weekday avg): {as_float(pred.get('last_year_passengers', 0)):,}",
        f"Days until Sunday: {pred.get('days_until_sunday')}",
        f"Most recent data date: {pred.get('most_recent_date')}",
        "",
        "Contract likelihoods (sorted by floor_strike):",
    ]

    rows = []
    for ticker, info in sorted(likelihoods.items(), key=lambda x: x[1].get("floor_strike", 0)):
        rows.append(
            f"{ticker:<18} | strike={info.get('floor_strike')} | side={info.get('side')} | value={as_float(info.get('true_value', 0)):.3f}"
        )

    order_line = orders if isinstance(orders, str) else str(orders)

    return "\n".join(summary_lines + rows + ["", "Orders:", order_line])


def main():
    """Run TSA workflow, format a clean email, and send it."""
    logfile = _init_logging()
    logging.info("Starting TSA trading bot run")

    fetch_all_tsa_data()
    prediction = create_next_week_prediction()
    likelihoods = get_likelihoods_of_each_contract(prediction)
    logging.info(f"Prediction keys: {list(prediction.keys())}")
    logging.info(f"Computed likelihoods for {len(likelihoods)} contracts")

    if datetime.date.today().weekday() == 0:
        try:
            orders = create_limit_orders_for_all_contracts(likelihoods)
            logging.info(f"Orders placed: {orders}")
        except Exception:
            orders = "No orders placed today"
            logging.exception("Order placement failed")
    else:
        orders = "No orders placed today"
        logging.info("Not Monday: skipping order placement")

    body = _format_email(prediction, likelihoods, orders)
    shared.send_email(body)
    logging.info("Run complete; email sent")
    logging.info(f"Log file for this run: {logfile}")

if __name__ == "__main__":
    main()
