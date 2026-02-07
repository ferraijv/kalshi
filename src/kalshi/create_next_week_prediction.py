from __future__ import annotations

import pandas as pd
import datetime
import json
import logging
from kalshi import shared

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
    # Load TSA data (path relative to repo root)
    from pathlib import Path
    data_path = Path(__file__).resolve().parents[1] / "data" / "tsa_data.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"TSA data file not found at {data_path}. Populate it before running.")
    tsa_data = pd.read_csv(data_path, index_col=0)

    # Rename columns for clarity
    tsa_data.rename(columns={"Date": "date", "Numbers": "passengers"}, inplace=True)

    # Prepare for day of week YoY shift
    tsa_data['date'] = pd.to_datetime(tsa_data['date'], format='%m/%d/%Y')

    tsa_data['day_of_week'] = tsa_data['date'].dt.day_name()

    tsa_data['week_number'] = tsa_data['date'].dt.isocalendar().week

    tsa_data['year'] = tsa_data['date'].dt.year

    tsa_data['last_year_date'] = pd.to_datetime(
        (tsa_data['year']-1).astype(str) + "-" + tsa_data['week_number'].astype(str) + "-" + tsa_data['day_of_week'],
        format='%Y-%W-%A'
    )

    tsa_data = tsa_data.merge(
        tsa_data[['date', 'passengers', 'day_of_week']],
        left_on='last_year_date',
        right_on='date',
        suffixes=('', '_last_year')
    )

    tsa_data.rename(columns={"passengers_last_year": "previous_year"}, inplace=True)

    # Set the date column as the index and sort the index
    tsa_data = tsa_data.set_index('date')
    tsa_data.sort_index(inplace=True)

    # Filter data to include only dates after June 1, 2022
    tsa_data = tsa_data[tsa_data.index > '2022-06-01']

    # Calculate a 7-day moving average of passengers
    tsa_data['passengers_7_day_moving_average'] = tsa_data['passengers'].rolling(window=7).mean()

    # Calculate a 7-day moving average of the previous year's passenger data
    tsa_data['passengers_7_day_moving_average_previous_year'] = tsa_data['previous_year'].rolling(window=7).mean()

    return tsa_data

def calculate_days_until_sunday(run_date: datetime.date | None = None) -> int:
    """
    Return the number of days from the given date (or today) to the next Sunday,
    counting a same-day Sunday as 6 days to target the following week.
    """
    date_to_calculate = run_date or datetime.date.today()
    days_until_sunday = (6 - date_to_calculate.weekday()) % 7

    logging.info(f"Days until Sunday: {days_until_sunday}")

    if days_until_sunday == 0:
        days_until_sunday = 6

    # Data is delayed by one day, but we still want "days until Sunday" to reflect
    # calendar distance (Monday -> 6, Tuesday -> 5, Sunday -> 6 for next week).
    return days_until_sunday

def get_recent_trend(tsa_data, use_weighting=False):
    """
    Calculate recent trends in TSA passenger data and create predictions based on these trends.

    Steps:
    1. Calculate the current trend as the ratio of the 7-day moving average of passengers to the previous year's 7-day moving average.
    2. Create a lagged trend feature.
    3. Generate predictions using the previous year's 7-day moving average and the lagged trend.
    """
    # Calculate the current trend
    tsa_data['current_trend_1_day'] = tsa_data['passengers'] / tsa_data[
        'previous_year']

    tsa_data['current_trend_1_day_lagged'] = tsa_data['current_trend_1_day'].shift(1)

    tsa_data['current_trend'] = tsa_data['passengers_7_day_moving_average'] / tsa_data[
        'passengers_7_day_moving_average_previous_year']

    # Create a lagged trend feature.
    tsa_data['last_weeks_trend'] = tsa_data['current_trend'].shift(calculate_days_until_sunday())

    # Generate predictions using the previous year's 7-day moving average and the lagged trend
    if use_weighting:
        tsa_data['prediction'] = (
                tsa_data['passengers_7_day_moving_average_previous_year']
                * ((tsa_data['last_weeks_trend'] * .8) + (tsa_data['current_trend_1_day_lagged'] * .2))
        )
    else:
        tsa_data['prediction'] = (
                    tsa_data['passengers_7_day_moving_average_previous_year'] * tsa_data['last_weeks_trend'])

    from pathlib import Path
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    tsa_data.to_csv(data_dir / "lagged_tsa_data.csv")

    return tsa_data

def get_max_date(tsa_data):
    most_recent_date = tsa_data.index.max()

    logging.warning(f"Using {most_recent_date} as most recent date")

    return most_recent_date

def get_same_date_last_year_day_of_week_adjusted(current_year_date):
    """
    Return the same ISO week/day from the prior calendar year as a datetime.
    """
    iso_year, iso_week, iso_weekday = current_year_date.isocalendar()
    target_date = datetime.date.fromisocalendar(iso_year - 1, iso_week, iso_weekday)
    logging.warning(
        f"{current_year_date} entered as current date. {target_date} output as same day of week last year"
    )
    return datetime.datetime.combine(target_date, datetime.time())

def get_prediction(tsa_data, run_date=None):
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
    next_sunday = datetime.datetime.strptime(shared.get_next_sunday(reference_date=run_date), "%y%b%d")
    last_year = get_same_date_last_year_day_of_week_adjusted(next_sunday).strftime("%Y-%m-%d")
    last_years_passengers = tsa_data.loc[last_year]['passengers_7_day_moving_average']
    logging.warning(last_years_passengers)

    most_recent_date = get_max_date(tsa_data).strftime("%Y-%m-%d")

    day_7_trend = tsa_data.loc[most_recent_date]['current_trend']

    day_1_trend = tsa_data.loc[most_recent_date]['current_trend_1_day']

    yoy_adjustment = (
            day_7_trend*.8 # Weight 7-day average heavier
            +day_1_trend*.2 # Weight single day less
    )
    logging.warning(yoy_adjustment)
    prediction = {}
    next_sunday = next_sunday.strftime("%Y-%m-%d")
    prediction[next_sunday] = {
        "last_year_passengers": last_years_passengers,
        "yoy_adjustment": yoy_adjustment,
        "day_1_trend": day_1_trend,
        "day_7_trend": day_7_trend,
        "prediction": last_years_passengers*yoy_adjustment,
        "most_recent_date": most_recent_date,
        "days_until_sunday": calculate_days_until_sunday(run_date)
    }

    logging.warning(prediction)

    return prediction

def save_prediction(prediction):
    logging.warning(prediction)
    try:
        with open("data/tsa_traffic_predictions") as f:
            all_predictions = json.load(f)
        logging.warning(f"all predictions {all_predictions}")
        all_predictions.update(prediction)
        logging.warning(f"new prediction {prediction}")
        with open("data/tsa_traffic_predictions", "w") as outfile:
            json.dump(all_predictions, outfile)
    except FileNotFoundError:
        with open("data/tsa_traffic_predictions", "w") as outfile:
            json.dump(prediction, outfile)


def create_next_week_prediction(run_date=None):
    tsa_data = lag_passengers()
    tsa_data = get_recent_trend(tsa_data, True)
    prediction = get_prediction(tsa_data, run_date)
    save_prediction(prediction)

    return prediction
