import shared
import datetime
import pandas as pd

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

def get_current_market_prices():
    next_sunday = shared.get_next_sunday()
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


def get_likelihoods_of_each_contract(prediction):
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

    next_sunday = datetime.datetime.strptime(shared.get_next_sunday(), "%y%b%d").strftime("%Y-%m-%d")

    prediction = prediction[next_sunday]['prediction']

    print(f"Calculating likelihoods for {prediction}")

    historical_data = pd.read_csv("data/lagged_tsa_data.csv")
    historical_data = historical_data[['passengers_7_day_moving_average', 'prediction', 'day_of_week']]
    historical_data = historical_data[~historical_data['prediction'].isna()]
    historical_data['raw_error'] = historical_data['passengers_7_day_moving_average'] - historical_data['prediction']
    historical_data['percent_error'] = historical_data['passengers_7_day_moving_average']/historical_data['prediction']-1

    likelihoods = {}

    prices = get_current_market_prices()

    print(prices)

    floor_strikes = prices[['ticker', 'floor_strike']].values.tolist()
    print(f"floor strike: {floor_strikes}")

    # floor_strike[0] is the ticker
    # floor_strike[1] is the floor_strike
    for floor_strike in floor_strikes:
        if prediction > floor_strike[1]:
            likelihoods[floor_strike[0]] = {
                'floor_strike': floor_strike[1],
                'side': "yes",
                'true_value': get_likelihood_of_yes(prediction, floor_strike[1], historical_data)
            }
        elif prediction < floor_strike[1]:
            likelihoods[floor_strike[0]] = {
                'floor_strike': floor_strike[1],
                "side": "no",
                "true_value": get_likelihood_of_no(prediction, floor_strike[1], historical_data)
            }

    print(likelihoods)

    return likelihoods