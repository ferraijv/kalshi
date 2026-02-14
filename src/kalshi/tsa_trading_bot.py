import sys
from pathlib import Path
import datetime
import logging
from typing import Any, Dict, Optional, Tuple


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

def _compute_likelihoods_for_both_sources(
    prediction: Dict[str, Dict[str, float]],
    run_date: Optional[datetime.date],
) -> Tuple[Dict[str, Dict[str, Dict[str, float]]], Dict[str, str]]:
    """Compute heuristic then model likelihoods and capture per-source failures."""
    results: Dict[str, Dict[str, Dict[str, float]]] = {}
    errors: Dict[str, str] = {}
    for source in ("heuristic", "model"):
        try:
            results[source] = get_likelihoods_of_each_contract(
                prediction,
                run_date=run_date,
                prob_source=source,
            )
        except Exception as exc:
            errors[source] = str(exc)
            logging.exception("Failed computing %s likelihoods", source)
    return results, errors


def _format_email(
    prediction: Dict[str, Dict[str, float]],
    heuristic_likelihoods: Dict[str, Dict[str, Any]],
    model_likelihoods: Dict[str, Dict[str, Any]],
    errors: Dict[str, str],
    orders: Any,
) -> str:
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
        "Trading mode: heuristic (orders placed from heuristic output only)",
        "",
        "Heuristic likelihoods (sorted by floor_strike):",
    ]

    heuristic_rows = []
    for ticker, info in sorted(heuristic_likelihoods.items(), key=lambda x: x[1].get("floor_strike", 0)):
        heuristic_rows.append(
            f"{ticker:<18} | strike={info.get('floor_strike')} | side={info.get('side')} | value={as_float(info.get('true_value', 0)):.3f}"
        )

    model_lines = ["", "Model likelihoods (sorted by floor_strike):"]
    model_rows = []
    for ticker, info in sorted(model_likelihoods.items(), key=lambda x: x[1].get("floor_strike", 0)):
        model_rows.append(
            f"{ticker:<18} | strike={info.get('floor_strike')} | side={info.get('side')} | value={as_float(info.get('true_value', 0)):.3f}"
        )
    if not model_rows:
        model_rows.append("(none)")

    error_lines = []
    if errors:
        error_lines.extend(["", "Errors:"])
        for source in ("heuristic", "model"):
            if source in errors:
                error_lines.append(f"- {source}: {errors[source]}")

    order_line = orders if isinstance(orders, str) else str(orders)

    return "\n".join(summary_lines + heuristic_rows + model_lines + model_rows + error_lines + ["", "Orders:", order_line])


def main():
    """Run TSA workflow, format a clean email, and send it."""
    logfile = _init_logging()
    logging.info("Starting TSA trading bot run")

    # Optional run-date argument: YYYY-MM-DD
    run_date = None
    if len(sys.argv) > 1:
        try:
            run_date = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        except ValueError:
            logging.error("Invalid date format. Use YYYY-MM-DD.")
            sys.exit(1)
        logging.info(f"Using run date override: {run_date}")

    fetch_all_tsa_data()
    prediction = create_next_week_prediction(run_date=run_date)
    likelihoods_by_source, likelihood_errors = _compute_likelihoods_for_both_sources(prediction=prediction, run_date=run_date)
    heuristic_likelihoods = likelihoods_by_source.get("heuristic", {})
    model_likelihoods = likelihoods_by_source.get("model", {})
    logging.info(f"Prediction keys: {list(prediction.keys())}")
    logging.info(f"Computed heuristic likelihoods for {len(heuristic_likelihoods)} contracts")
    logging.info(f"Computed model likelihoods for {len(model_likelihoods)} contracts")

    if datetime.date.today().weekday() == 0:
        if not heuristic_likelihoods:
            orders = "No orders placed: heuristic likelihoods unavailable"
            logging.warning("Skipping order placement because heuristic likelihoods are empty")
        else:
            try:
                orders = create_limit_orders_for_all_contracts(heuristic_likelihoods, run_date=run_date)
                logging.info(f"Orders placed: {orders}")
            except Exception:
                orders = "No orders placed today"
                logging.exception("Order placement failed")
    else:
        orders = "No orders placed today"
        logging.info("Not Monday: skipping order placement")

    body = _format_email(
        prediction=prediction,
        heuristic_likelihoods=heuristic_likelihoods,
        model_likelihoods=model_likelihoods,
        errors=likelihood_errors,
        orders=orders,
    )
    shared.send_email(body)
    logging.info("Run complete; email sent")
    logging.info(f"Log file for this run: {logfile}")

if __name__ == "__main__":
    main()
