import sys
from pathlib import Path
import datetime
import pandas as pd


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

def main():
    """
    Main function to execute the TSA traffic prediction workflow.

    This function performs the following steps:
    1. Retrieves the most recent TSA traffic data.
    2. Generates a prediction for the TSA traffic for the next week based on the retrieved data.
    3. Sends an email containing the prediction result.

    The function does not return any value.

    Usage:
    This function is typically called when running the script directly. It will execute the entire workflow for TSA traffic prediction and result notification.
    """

    ## Get recent TSA data
    #fetch_all_tsa_data()

    ## Create next week TSA prediction
    prediction = create_next_week_prediction()

    ## Retrieve current market prices from Kalshi
    likelihoods = get_likelihoods_of_each_contract(prediction)

    # Place orders
    # If today is Monday (aka 0 of 6), then place trades
    if datetime.date.today().weekday() == 0:
        try:
            orders = create_limit_orders_for_all_contracts(likelihoods)
        except Exception:
            orders = "No orders placed today"
    else:
        orders = "No orders placed today"

    ## Email prediction result
    shared.send_email(str(prediction)+"\n"+str(likelihoods)+"\n"+str(orders))

if __name__ == "__main__":
    main()

