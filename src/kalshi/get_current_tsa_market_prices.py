import shared
import datetime
import pandas as pd

def get_next_sunday():
    today = datetime.date.today()
    # Calculate the number of days until the next Sunday (0 is Monday, 6 is Sunday)
    days_until_sunday = (6 - today.weekday()) % 7
    print(f"today: {days_until_sunday}")
    # If today is Sunday, we want the next Sunday, so we add 7 days
    if days_until_sunday == 0:
        days_until_sunday = 0
    next_sunday = today + datetime.timedelta(days=days_until_sunday)
    next_sunday = next_sunday.strftime("%y%b%d").upper()

    return next_sunday

def create_event_id(next_sunday):
    event_id = f"TSAW-{next_sunday}"
    print(event_id)
    return event_id

def get_floor_strike_and_prices(event_id):
    exchange_client = shared.login()
    df = pd.json_normalize(exchange_client.get_event(event_id)['markets'])
    prices = df[['floor_strike', 'yes_ask', 'no_ask']]

    return prices

def get_current_market_prices():
    next_sunday = get_next_sunday()
    event_id = create_event_id(next_sunday)

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

    next_sunday = datetime.datetime.strptime(get_next_sunday(), "%y%b%d").strftime("%Y-%m-%d")

    prediction = prediction[next_sunday]['prediction']

    print(f"Calculating likelihoods for {prediction}")

    historical_data = pd.read_csv("data/lagged_tsa_data.csv")
    historical_data = historical_data[['passengers_7_day_moving_average', 'prediction']]
    historical_data = historical_data[~historical_data['prediction'].isna()]
    historical_data['raw_error'] = historical_data['passengers_7_day_moving_average'] - historical_data['prediction']
    historical_data['percent_error'] = historical_data['passengers_7_day_moving_average']/historical_data['prediction']-1

    likelihoods = {}

    prices = get_current_market_prices()

    floor_strikes = list(prices['floor_strike'])
    print(floor_strikes)

    for floor_strike in floor_strikes:
        if prediction > floor_strike:
            likelihoods[floor_strike] = {"yes": get_likelihood_of_yes(prediction, floor_strike, historical_data)}
        elif prediction < floor_strike:
            likelihoods[floor_strike] = {"no": get_likelihood_of_no(prediction, floor_strike, historical_data)}

    print(likelihoods)

    return likelihoods



