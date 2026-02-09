import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from kalshi import contract_probability_model
from kalshi import shared

def get_floor_strike_and_prices(event_id):
    """
    Fetch market data for a specific event and extract relevant pricing information.

    This function logs into the exchange client, retrieves market data for the given event,
    and normalizes the response into a pandas DataFrame. It then selects and returns the
    'ticker', 'floor_strike', 'yes_ask', and 'no_ask' columns.

    Parameters:
    event_id (str or int): The ID of the event for which market data is being retrieved.

    Returns:
    pandas.DataFrame: A DataFrame containing the columns 'ticker', 'floor_strike', 'yes_ask',
                      and 'no_ask' with corresponding market data for the event.
    """
    exchange_client = shared.login()
    df = pd.json_normalize(exchange_client.get_event(event_id)['markets'])
    prices = df[['ticker', 'floor_strike', 'yes_ask', 'no_ask']]

    return prices

def get_current_market_prices(run_date=None):
    next_sunday = shared.get_next_sunday(reference_date=run_date)
    event_id = shared.create_tsa_event_id(next_sunday)

    prices = get_floor_strike_and_prices(event_id)

    return prices

def get_likelihood_of_yes(prediction, floor_strike, historical_data):

    percent_difference = prediction / floor_strike - 1

    num_records_below_threshold = len(
        historical_data[historical_data['percent_error'] < percent_difference].index
    )
    total_cases = len(historical_data)
    likelihood = num_records_below_threshold / total_cases
    print(f"Likelihood of similar size difference: {likelihood}")

    return likelihood


def get_likelihood_of_no(prediction, floor_strike, historical_data):
    """
    This is used when prediction is less than the floor strike. This calculates the likelihood
    that the actual value NOT exceed the floor strike given the prediction. This represents the
    true value of the NO contract

    :param prediction: The predicted value
    :param floor_strike: The current floor strike from Kalshi
    :param historical_data: Historical TSA traffic data
    :return:
    """
    percent_difference = prediction / floor_strike - 1
    num_records_with_larger_discrepancy = len(
        historical_data[historical_data['percent_error'] > percent_difference].index
    )
    total_cases = len(historical_data)
    likelihood = num_records_with_larger_discrepancy / total_cases
    print(f"Likelihood of similar size difference: {likelihood}")

    return likelihood


def _load_historical_likelihood_data() -> pd.DataFrame:
    """Load historical percent-error data used by heuristic fallback."""
    data_path = Path(__file__).resolve().parents[1] / "data" / "lagged_tsa_data.csv"
    historical_data = pd.read_csv(data_path)
    historical_data = historical_data[['passengers_7_day_moving_average', 'prediction', 'day_of_week']]
    historical_data = historical_data[~historical_data['prediction'].isna()]
    historical_data['raw_error'] = historical_data['passengers_7_day_moving_average'] - historical_data['prediction']
    historical_data['percent_error'] = historical_data['passengers_7_day_moving_average']/historical_data['prediction']-1
    return historical_data


def get_likelihoods_of_each_contract(
    prediction: Dict[str, Dict[str, float]],
    run_date: Optional[datetime.date] = None,
    model_bundle_path: Optional[Path] = None,
    prob_source: str = "model",
) -> Dict[str, Dict[str, float]]:
    """
    Calculate the likelihood of each contract being correct based on a prediction and historical data.

    This function retrieves the prediction for the upcoming Sunday, calculates the likelihood
    of each contract's outcome (yes or no) using historical data, and compares it against current
    market prices.

    Steps:
    1. Get the date of the next Sunday and extract the prediction value for that date.
    2. Load historical TSA data, compute raw and percent error based on predictions, and filter out
       missing values.
    3. Retrieve current market prices and floor strike values.
    4. For each contract, determine whether the prediction is above or below the floor strike.
    5. Calculate the likelihood for either the "yes" or "no" side of the contract based on historical data.
    6. Store the likelihoods for each contract in a dictionary and return it.

    Parameters:
    prediction (dict): A dictionary containing predictions for various dates, including the next Sunday.

    Returns:
    dict: A dictionary where each key is a contract ticker and the value is a dictionary containing:
          - 'floor_strike': The floor strike value for the contract.
          - 'side': The side of the contract ('yes' or 'no').
          - 'true_value': The calculated likelihood of that side being correct.
    """

    next_sunday = datetime.datetime.strptime(shared.get_next_sunday(reference_date=run_date), "%y%b%d").strftime("%Y-%m-%d")

    if next_sunday not in prediction:
        raise ValueError(f"Prediction date {next_sunday} missing from prediction dict; aborting likelihood calc")

    prediction_payload = prediction[next_sunday]
    prediction_value = float(prediction_payload['prediction'])

    print(f"Calculating likelihoods for {prediction_value}")

    if prob_source not in {"model", "heuristic"}:
        raise ValueError(f"Unsupported prob_source: {prob_source}")

    likelihoods = {}
    historical_data = None

    prices = get_current_market_prices(run_date)

    print(prices)

    floor_strikes = prices[['ticker', 'floor_strike']].values.tolist()
    print(f"floor strike: {floor_strikes}")

    # floor_strike[0] is the ticker
    # floor_strike[1] is the floor_strike
    as_of_date = run_date or datetime.date.today()
    bundle_path = model_bundle_path or contract_probability_model.DEFAULT_MODEL_BUNDLE
    for floor_strike in floor_strikes:
        ticker = floor_strike[0]
        strike = floor_strike[1]
        prob_yes = contract_probability_model.predict_yes_probability(
            prediction_passengers=prediction_value,
            floor_strike=strike,
            run_date=as_of_date,
            prediction_context=prediction_payload,
            model_bundle_path=bundle_path,
        ) if prob_source == "model" else None

        if prob_source == "model" and prob_yes is None:
            raise RuntimeError(
                f"Model inference failed for ticker={ticker} strike={strike}; "
                "refusing heuristic fallback in model mode."
            )

        if prob_source == "heuristic":
            if historical_data is None:
                historical_data = _load_historical_likelihood_data()
            if prediction_value > strike:
                prob_yes = get_likelihood_of_yes(prediction_value, strike, historical_data)
            elif prediction_value < strike:
                prob_yes = 1.0 - get_likelihood_of_no(prediction_value, strike, historical_data)
            else:
                prob_yes = 0.5
        side, true_value = contract_probability_model.map_yes_probability_to_side(prob_yes)
        likelihoods[ticker] = {
            'floor_strike': strike,
            'side': side,
            'true_value': true_value,
            'prob_yes': prob_yes,
        }

    print(likelihoods)

    return likelihoods
