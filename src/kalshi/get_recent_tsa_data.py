import pandas as pd
import requests
import datetime
import logging
import time
from pathlib import Path
from requests.exceptions import RequestException

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


def _request_with_retries(url: str, headers: dict, max_attempts: int = 4, base_delay: float = 1.0) -> requests.Response:
    """Fetch a URL with simple exponential backoff."""
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp
        except RequestException as exc:
            if attempt == max_attempts:
                raise
            sleep_for = base_delay * (2 ** (attempt - 1))
            logging.warning(f"Fetch failed (attempt {attempt}/{max_attempts}) for {url}: {exc}. Retrying in {sleep_for:.1f}s")
            time.sleep(sleep_for)


def fetch_year_of_tsa_data(year_to_process, max_attempts: int = 4):
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

    r = _request_with_retries(url, header, max_attempts=max_attempts)

    df = pd.read_html(r.text)[0]

    logging.warning(f"DF Structure: {df.head()}")

    return df

def _load_existing_data(data_path: Path):
    """Return (df, set_of_years) from existing CSV, or (None, set()) if missing."""
    if not data_path.exists():
        return None, set()
    df = pd.read_csv(data_path)
    if "Date" not in df.columns:
        logging.warning(f"Existing TSA data missing Date column; refetching all years.")
        return None, set()
    df['year'] = pd.to_datetime(df['Date'], format='%m/%d/%Y').dt.year
    years_present = set(df['year'].unique())
    return df, years_present


def fetch_all_tsa_data(max_attempts: int = 4):
    """Fetch All TSA Data

    Fetches TSA (Transportation Security Administration) data for all available years
    up to the current year and merges them into a single DataFrame.

    Returns:
        pandas.DataFrame: A DataFrame containing all the TSA data for the available years.
    """

    dfs = []

    data_root = Path(__file__).resolve().parents[1] / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    data_path = data_root / "tsa_data.csv"

    existing_df, years_present = _load_existing_data(data_path)

    target_years = list(range(2019, datetime.datetime.now().year + 1))
    missing_years = [y for y in target_years if y not in years_present]

    logging.warning(f"Existing years: {sorted(years_present)}; missing years to fetch: {missing_years}")

    # Keep existing data if it was loadable
    if existing_df is not None:
        dfs.append(existing_df)

    for year_to_process in missing_years:

        df = fetch_year_of_tsa_data(year_to_process, max_attempts=max_attempts)

        dfs.append(df)

        time.sleep(1)  # Wait in between requests to avoid

    if not dfs:
        raise RuntimeError("No TSA data frames to merge; fetch may have failed.")

    df_merged = pd.concat(dfs, ignore_index=True, sort=False)
    # Drop duplicates on Date to avoid overlapping historical downloads
    if "Date" in df_merged.columns:
        df_merged = df_merged.drop_duplicates(subset=["Date"])
        df_merged = df_merged.sort_values(by="Date")

    logging.warning(f"Writing TSA merged data to {data_path}")
    df_merged.to_csv(data_path, index=False)

    return df_merged
