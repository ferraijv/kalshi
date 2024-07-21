import pandas as pd
import datetime
import json

def lag_passengers():
    """
    Load TSA passenger data, process it to create lagged features, and return the processed dataframe.

    Steps:
    1. Load TSA data from a CSV file.
    2. Rename columns for clarity.
    3. Convert the date column to datetime format.
    4. Set the date column as the index and sort the index.
    5. Create a new column with passenger data from the previous year.
    6. Filter data to include only dates after June 1, 2022.
    7. Calculate a 7-day moving average of the number of passengers.
    8. Calculate a 7-day moving average of the previous year's passenger data.
    """
    # Load TSA data
    tsa_data = pd.read_csv("../data/tsa_data.csv", index_col=0)

    # Rename columns for clarity
    tsa_data.rename(columns={"Date": "date", "Numbers": "passengers"}, inplace=True)

    # Convert date column to datetime format
    tsa_data['date'] = pd.to_datetime(tsa_data['date'], format='%m/%d/%Y')

    # Set the date column as the index and sort the index
    tsa_data = tsa_data.set_index('date')
    tsa_data.sort_index(inplace=True)

    # Create a new column with passenger data from the previous year
    tsa_data['previous_year'] = tsa_data['passengers'].shift(365)

    # Filter data to include only dates after June 1, 2022
    tsa_data = tsa_data[tsa_data.index > '2022-06-01']

    # Calculate a 7-day moving average of passengers
    tsa_data['passengers_7_day_moving_average'] = tsa_data['passengers'].rolling(window=7).mean()

    # Calculate a 7-day moving average of the previous year's passenger data
    tsa_data['passengers_7_day_moving_average_previous_year'] = tsa_data['previous_year'].rolling(window=7).mean()

    return tsa_data

def get_recent_trend(tsa_data):
    """
    Calculate recent trends in TSA passenger data and create predictions based on these trends.

    Steps:
    1. Calculate the current trend as the ratio of the 7-day moving average of passengers to the previous year's 7-day moving average.
    2. Create a lagged trend feature.
    3. Generate predictions using the previous year's 7-day moving average and the lagged trend.
    """
    # Calculate the current trend
    tsa_data['current_trend'] = tsa_data['passengers_7_day_moving_average'] / tsa_data[
        'passengers_7_day_moving_average_previous_year']

    # Create a lagged trend feature (Use 2 weeks ago in case data isn't available for previous week
    tsa_data['last_weeks_trend'] = tsa_data['current_trend'].shift(2)

    # Generate predictions using the previous year's 7-day moving average and the lagged trend
    tsa_data['prediction'] = tsa_data['passengers_7_day_moving_average_previous_year'] * tsa_data['last_weeks_trend']

    return tsa_data


def get_next_market_end():
    """
    The Kalshi market always ends on Sunday. This function will determine the date of the next Sunday
    and return the date in YYYY-MM-DD format.

    :return: str
    """
    today = datetime.date.today()
    # Calculate the number of days until the next Sunday (0 is Monday, 6 is Sunday)
    days_until_sunday = (6 - today.weekday()) % 7
    # If today is Sunday, we want the next Sunday, so we add 7 days
    if days_until_sunday == 0:
        days_until_sunday = 7
    next_sunday = today + datetime.timedelta(days=days_until_sunday)
    return next_sunday

def get_prediction(tsa_data):
    """
    Generate a prediction for the next Sunday's TSA passenger numbers based on historical data and recent trends.

    Steps:
    1. Determine the date of the next Sunday.
    2. Retrieve the number of passengers from the same Sunday last year.
    3. Calculate the year-over-year (YoY) adjustment based on recent trends.
    4. Multiply last year's passenger numbers by the YoY adjustment to get the prediction.

    :param tsa_data: DataFrame containing TSA passenger data with necessary features.
    :return: Dictionary with the date of the next Sunday as the key and the predicted number of passengers as the value.
    """
    next_sunday = get_next_market_end()
    last_year = (next_sunday - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    last_years_passengers = tsa_data.loc[last_year]['passengers_7_day_moving_average']
    print(last_years_passengers)
    three_days_ago = (datetime.date.today() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    yoy_adjustment = tsa_data.loc[three_days_ago]['last_weeks_trend']
    print(yoy_adjustment)
    prediction = {}
    next_sunday = next_sunday.strftime("%Y-%m-%d")
    prediction[next_sunday] = last_years_passengers * yoy_adjustment

    print(prediction)

    return prediction

def save_prediction(prediction):
    print(prediction)
    try:
        with open("../data/tsa_traffic_predictions") as f:
            all_predictions = json.load(f)
        print(f"all predictions {all_predictions}")
        all_predictions.update(prediction)
        print(f"new prediction {prediction}")
        with open("../data/tsa_traffic_predictions", "w") as outfile:
            json.dump(all_predictions, outfile)
    except FileNotFoundError:
        with open("../data/tsa_traffic_predictions", "w") as outfile:
            json.dump(prediction, outfile)


def create_next_week_prediction():
    tsa_data = lag_passengers()
    tsa_data = get_recent_trend(tsa_data)
    prediction = get_prediction(tsa_data)
    save_prediction(prediction)

    return prediction

