import shared
import datetime
import pandas as pd

def get_floor_strike_and_prices(event_id):
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

    next_sunday = datetime.datetime.strptime(shared.get_next_sunday(), "%y%b%d").strftime("%Y-%m-%d")

    prediction = prediction[next_sunday]['prediction']

    print(f"Calculating likelihoods for {prediction}")

    historical_data = pd.read_csv("data/lagged_tsa_data.csv")
    historical_data = historical_data[['passengers_7_day_moving_average', 'prediction']]
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