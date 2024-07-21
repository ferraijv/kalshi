import pandas as pd
import requests
import datetime
import logging
import time

def create_request_url(year_to_process, current_year):
    """Create Request URL

    Creates a URL for fetching TSA data based on the year to process and the current year.

    Args:
        year_to_process (int): The year for which the data is to be fetched.
        current_year (int): The current year.

    Returns:
        str: The URL for fetching TSA data for the specified year.
    """

    base_url = 'https://www.tsa.gov/travel/passenger-volumes'

    if year_to_process == current_year:
        url = base_url
    else:
        url = f"{base_url}/{year_to_process}"

    return url


def fetch_year_of_tsa_data(year_to_process):
    """Fetch TSA Data for a Specific Year

    Fetches TSA (Transportation Security Administration) data for a specific year from the TSA website.

    Args:
        base_url (str): The base URL of the TSA data website.
        year_to_process (int): The year for which the data is to be fetched.

    Returns:
        pandas.DataFrame: A DataFrame containing the TSA data for the specified year.
    """

    header = {'User-Agent': 'Mozilla/5.0'}  # TSA website blocks bot traffic unless you include this
    current_year = datetime.datetime.now().year

    url = create_request_url(year_to_process, current_year)

    logging.warning(f"Processing {year_to_process}")

    r = requests.get(url, headers=header)

    df = pd.read_html(r.text)[0]

    if year_to_process == current_year:
        df = df[['Date', str(current_year)]]
        df = df.rename(columns={str(current_year): "Numbers"})

    return df

def fetch_all_tsa_data():
    """Fetch All TSA Data

    Fetches TSA (Transportation Security Administration) data for all available years
    up to the current year and merges them into a single DataFrame.

    Returns:
        pandas.DataFrame: A DataFrame containing all the TSA data for the available years.
    """

    dfs = []

    for year_to_process in range(2019, datetime.datetime.now().year+1):

        df = fetch_year_of_tsa_data(year_to_process)

        dfs.append(df)

        time.sleep(1)  # Wait in between requests to avoid

    df_merged = pd.concat(dfs, ignore_index=True, sort=False)

    df_merged.to_csv("../data/tsa_data.csv")

    return df_merged
