
import calendar
from typing import Optional
from botocore.exceptions import ClientError
import json
import boto3
import datetime
import logging
import uuid
import yfinance as yf
import requests
import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from clients import ExchangeClient




logging.basicConfig(level=logging.DEBUG)

def login(use_demo=False):
    """ Prompt user for Kalshi login credentials and return exchange client """

    # Load environment variables from .env file
    load_dotenv()

    # Fetch the Key ID from the environment
    KEYID = os.getenv("KALSHI_KEY_ID")

    if not KEYID:
        raise ValueError("KALSHI_KEY_ID is not set. Check your .env file.")
    
    # Get private key from AWS Secrets Manager
    session = boto3.session.Session()
    client = session.client('secretsmanager')
    try:
        secret_value = client.get_secret_value(SecretId='kalshi_api_key')
        secret_key = secret_value['SecretString']
    except ClientError as e:
        raise Exception(f"Error retrieving private key from Secrets Manager: {str(e)}")
# Load private key
    try:
        private_key = serialization.load_pem_private_key(
            secret_key.encode('utf-8'),
            password=None  # Provide a password if your key is encrypted
        )
    except Exception as e:
        raise Exception(f"Error loading private key: {str(e)}")

    # Initialize the Kalshi HTTP client
    client = ExchangeClient(
        exchange_api_base='https://api.elections.kalshi.com/trade-api/v2',
        key_id=KEYID,
        private_key=private_key
    )
    
    return client

def send_email(body):
    SENDER = "ferraioloj@gmail.com"

    # Replace recipient@example.com with a "To" address. If your account
    # is still in the sandbox, this address must be verified.
    RECIPIENT = "ferraioloj@gmail.com"

    # The subject line for the email.
    SUBJECT = "Amazon SES Test (SDK for Python)"

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = body

    # The HTML body of the email.
    BODY_HTML = f"""<html>
    {body}
    </html>
                """

    # The character encoding for the email.
    CHARSET = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses')

    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])

def get_secret(secret_name):

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager'
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("The requested secret " + secret_name + " was not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            print("The request was invalid due to:", e)
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            print("The request had invalid params:", e)
        elif e.response['Error']['Code'] == 'DecryptionFailure':
            print("The requested secret can't be decrypted using the provided KMS key:", e)
        elif e.response['Error']['Code'] == 'InternalServiceError':
            print("An error occurred on service side:", e)
    else:
        # Secrets Manager decrypts the secret value using the associated KMS CMK
        # Depending on whether the secret was a string or binary, only one of these fields will be populated
        if 'SecretString' in get_secret_value_response:
            text_secret_data = get_secret_value_response['SecretString']
        else:
            binary_secret_data = get_secret_value_response['SecretBinary']

    return json.loads(get_secret_value_response['SecretString'])

def format_date(date_to_format = datetime.date.today()):
    """ Create today's date in format '99MAR21' """

    month = calendar.month_abbr[date_to_format.month].upper()
    year = str(date_to_format.year)[2:]
    day = date_to_format.strftime("%d")
    date_string = f"{year}{month}{day}"

    logging.debug(date_string)

    return date_string

def create_sp_market_id(run_date = datetime.date.today()):
    """ Create market id for S&P 500 market """

    run_date_formatted = format_date(run_date)
    logging.debug(f"Day: {run_date.weekday()}")
    if run_date.weekday() == 4:
        market_id = f"INXW-{run_date_formatted}"
    else:
        market_id = f"INXD-{run_date_formatted}"

    logging.debug(f"Market ID: {market_id}")
    return market_id

def create_nasdaq_event_id(run_date = datetime.date.today()):
    """ Create market id for S&P 500 market """

    run_date_formatted = format_date(run_date)
    logging.debug(f"Day: {run_date.weekday()}")
    if run_date.weekday() == 4:
        event_id = f"NASDAQ100W-{run_date_formatted}"
    else:
        event_id = f"NASDAQ100D-{run_date_formatted}"

    logging.debug(f"Market ID: {event_id}")
    return event_id

def create_weekly_sp_market_id():
    """ Create market id for S&P 500 market """
    today = datetime.date.today()
    friday = today + datetime.timedelta( (4-today.weekday()) % 7 )
    friday_formatted = format_date(friday)
    market_id = f"INXW-{friday_formatted}"

    return market_id

def create_weekly_nasdaq_market_id():
    """ Create market id for S&P 500 market """
    today = datetime.date.today()
    friday = today + datetime.timedelta( (4-today.weekday()) % 7 )
    friday_formatted = format_date(friday)
    market_id = f"NASDAQ100W-{friday_formatted}"

    return market_id

def cancel_all_orders_for_market(market_id, use_demo=False):
    """ Iterates through each currently open order for a given market and decreases remaining count to 0 """

    exchange_client = login(use_demo)
    all_orders = exchange_client.get_orders(event_ticker=market_id)['orders']
    logging.debug(all_orders)
    orders_to_cancel = [(e['order_id'], e['remaining_count']) for e in all_orders if e['remaining_count'] > 0]

    orders_cancelled = []
    for order in orders_to_cancel:
        logging.debug(f"Canceling order id: {order[0]}")
        exchange_client.decrease_order(order_id=order[0], reduce_by=order[1])
        orders_cancelled.append(order)
        logging.debug(f"{order[0]} cancelled")

    logging.debug("Done canceling existing orders")

    send_email(f"Orders Cancelled: {str(orders_cancelled)}")

    return True


def sell_all_contracts_for_market(market_id):

    exchange_client = login()
    order_params = {
        "action": "sell",
        "type": "market",
        "side": "no",

    }

    contracts_sold = []
    for event in exchange_client.get_positions(event_ticker=market_id)['market_positions']:
        exchange_client.create_order(
            event['ticker'],
            client_order_id=str(uuid.uuid4()),
            count=event['total_traded']
        )
        contracts_sold.append(event)

    send_email(f"Sold orders created: {str(contracts_sold)}")


def check_for_fulfilled_orders(event_id):
    """
    Creates list of completely fulfilled orders
    :param str event_id: ID for the event to check for fulfilled orders
    :return:
    """
    exchange_client = login()
    fulfilled_orders = []
    for market in exchange_client.get_positions(event_ticker=event_id)['market_positions']:
        print(market)
        if market["total_traded"] > 0 and market["resting_orders_count"] == 0:
            fulfilled_orders.append(market)

    return fulfilled_orders

def create_no_orders_for_every_contract_in_market(
        market_id: str,
        exclude_tickers: list,
        limit_price: Optional[int] = 15,
        use_demo=False
):
    """
    Create no order for every contract in a given market
    events dict: dictionary of events for particular market
    limit_price int: integer for number of cents for limit price
    """

    exchange_client = login(use_demo)
    events = exchange_client.get_event(market_id)

    order_params = {
        "action": "buy",
        "type": "limit",
        "side": "no",
        "count": 100,
        "no_price": limit_price

    }
    for event in events['markets']:
        if event['ticker'] not in exclude_tickers:
            logging.info(f"Creating {order_params['action']} order for {event['ticker']} at {order_params['no_price']}")
            exchange_client.create_order(ticker=event["ticker"], client_order_id=str(uuid.uuid4()), **order_params)

    return True


def check_if_negative_risk_is_met_for_market(event_id):
    """
    Gets all positions in a given event and checks if negative risk has already been met
    :param str event_id: Event id to check for negative risk
    :return: boolean for whether negative risk has been met or not
    """
    exchange_client = login()
    exposure = exchange_client.get_positions(event_ticker=event_id)['event_positions'][0]['event_exposure']
    if exposure <= 0:
        return True
    elif exposure > 0:
        return False
    else:
        raise Exception

def get_s_and_p_data():
    return yf.download('SPY', start='2020-01-01', end=datetime.date.today())

def get_nasdaq_data():
    return yf.download('QQQ', start='2020-01-01', end=datetime.date.today())

def create_day_of_week(data):
    """
    Creates various date variables in dataframe
    :param df data: historical stock data
    :return: df with date variables
    """
    data['day_of_week'] = data.index.dayofweek
    data['year'] = data.index.year
    data['week'] = data.index.isocalendar().week
    data['year_week'] = data['year'].astype(str) + data['week'].astype(str)
    return data


def get_percentage_change(data, day_of_week=1):
    """
    Calculates the percentage change for historical data only for day of week specific (Always compares to Friday)

    :param data: historical dataset
    :param day_of_week: day of week that will be compared against Friday
    :return: Returns dataframe containing all historical data for that day of week and the resulting change on Friday
    """
    subset = data[(data['day_of_week'] == day_of_week) | (data['day_of_week'] == 4)]
    subset['friday_close'] = subset.groupby(["year_week"])['Close'].shift(-1)
    subset = subset[(subset['day_of_week'] == day_of_week)]
    subset['percentage_change'] = subset["Close"]/subset["friday_close"]
    return subset

def get_likelihood_of_similar_change(data, percentage_window):
    """
    Determines what percentage of instances in the past fall in percentage change bucket

    :param data: historical dataset with percentage change field
    :param percentage_window: tuple containing two values representing the range
    :return: percentage of times that event occurred
    """
    df = data[(data["percentage_change"] >= percentage_window[0]) & (data["percentage_change"] <= percentage_window[1])]
    return len(df.index)/len(data.index)


def get_current_day_of_week():

    return datetime.datetime.now().weekday()


def buy_yes_contract_at_market(market_id, dollar_amount):
    exchange_client = login()
    market = exchange_client.get_market(market_id)['market']
    yes_ask = market['yes_ask']
    quantity = dollar_amount / (yes_ask / 100)

    order_params = {
        "action": "buy",
        "type": "market",
        "side": "yes",
        "count": quantity,

    }

    print(f"Buying {quantity} shares of YES for {market_id}")
    exchange_client.create_order(market_id, client_order_id=str(uuid.uuid4()), **order_params)

def buy_no_contract_at_market(market_id, dollar_amount):
    exchange_client = login()
    market = exchange_client.get_market(market_id)['market']
    print(f"Market: {market}")
    no_ask = 1 - market['yes_bid']
    quantity = dollar_amount / (no_ask / 100)

    order_params = {
        "action": "buy",
        "type": "market",
        "side": "no",
        "count": quantity,

    }

    print(f"Buying {quantity} shares of NO for {market_id}")
    #exchange_client.create_order(market_id, client_order_id=str(uuid.uuid4()), **order_params)

def get_log_file_contents(log_file):
    """
    Get contents of logfile as string

    :param log_file:
    :return:
    """
    with open(log_file) as f:
        lines = f.readlines()

    return str(lines)

def get_percentage_change_for_market(current_price, market):
    if market.get("floor_strike"):
        lower_bound = market['floor_strike']/current_price
    else:
        lower_bound = 0
    if market.get("cap_strike"):
        upper_bound = market['cap_strike']/current_price
    else:
        upper_bound = 9999999

    results = (lower_bound, upper_bound)

    return results

def get_sp_current_price():
    return yf.download('^GSPC', start=datetime.date.today(), end=datetime.date.today())['Close'][0]

def get_nasdaq_current_price():
    return yf.download('^NDX', start=datetime.date.today(), end=datetime.date.today())['Close'][0]


def get_likelihood(movement_range, data):
    data = create_day_of_week(data)
    historical = get_percentage_change(data)
    res = historical[(historical['percentage_change'] > movement_range[0]) & (historical['percentage_change'] < movement_range[1])]
    times_happened = len(res.index)
    total_weeks = len(historical.index)

    logging.info(f"Movement range: {movement_range}")
    logging.info(f"Times occurred: {times_happened}")
    logging.info(f"Total weeks: {total_weeks}")

    return times_happened/total_weeks

def compare_yes_likelihood_to_actual_price(likelihood, market):
    logging.info(f"----------Yes Analysis for {market}----------")
    yes_price = market['yes_ask']
    likelihood = likelihood*100
    if likelihood < 1.0 :
        likelihood = 1.0
    ratio = yes_price / likelihood
    logging.info(f"Yes price: {yes_price}")
    logging.info(f"Likelihood {likelihood}")
    logging.info(f"Ratio: {ratio}")
    if yes_price < 10:
        if ratio > 3:
            logging.info("Overpriced")
        elif ratio > .5 and ratio <= 3:
            logging.info("Fairly priced")
        elif ratio <= .5 and ratio > 0:
            logging.info("Underpriced")
            buy_yes_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception
    elif yes_price >= 10 and yes_price < 60:
        if ratio > 2:
            logging.info("Overpriced")
        elif ratio > .6 and ratio <= 2:
            logging.info("Fairly priced")
        elif ratio <= .6 and ratio > 0:
            logging.info("Underpriced")
            buy_yes_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception
    elif yes_price >= 60:
        if ratio > 1.5:
            logging.info("Overpriced")
        elif ratio > .8 and ratio <= 2:
            logging.info("Fairly priced")
        elif ratio <= .8 and ratio > 0:
            logging.info("Underpriced")
            buy_yes_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception


def compare_no_likelihood_to_actual_price(likelihood, market):
    logging.info(f"----------No Analysis for {market}----------")
    no_price = (1 - market['yes_bid']/100)*100
    # Inverse likelihood because it's for no markets
    likelihood = 1 - likelihood
    likelihood = likelihood*100
    if likelihood < 1.0 :
        likelihood = 1.0
    ratio = no_price / likelihood
    logging.info(f"No price: {no_price}")
    logging.info(f"Likelihood {likelihood}")
    logging.info(f"Ratio: {ratio}")
    if no_price < 10:
        if ratio > 3:
            logging.info("Overpriced")
        elif ratio > .5 and ratio <= 3:
            logging.info("Fairly priced")
        elif ratio <= .5 and ratio > 0:
            logging.info("Underpriced")
            buy_no_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception
    elif no_price >= 10 and no_price < 60:
        if ratio > 2:
            logging.info("Overpriced")
        elif ratio > .6 and ratio <= 2:
            logging.info("Fairly priced")
        elif ratio <= .6 and ratio > 0:
            logging.info("Underpriced")
            buy_no_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception
    elif no_price >= 60:
        if ratio > 1.5:
            logging.info("Overpriced")
        elif ratio > .8 and ratio <= 2:
            logging.info("Fairly priced")
        elif ratio <= .8 and ratio > 0:
            logging.info("Underpriced")
            buy_no_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception


def determine_if_markets_in_event_are_fairly_priced(event, data):
    """
    For each market in the event determines if market is fairly priced based on historical data. If market is
    underpriced, it will purchase contracts
    :param event: event data
    :param data: historical data used to calculate likelihoods
    :return:
    """
    markets = event['markets']
    logging.info(markets)
    current_price = get_nasdaq_current_price()
    for market in markets:
        logging.info("************* New analysis marker *************")
        movement_range = get_percentage_change_for_market(current_price, market)
        likelihood = get_likelihood(movement_range, data)
        compare_yes_likelihood_to_actual_price(likelihood, market)
        compare_no_likelihood_to_actual_price(likelihood, market)

    return True


def get_markets_with_yes_price_below_threshold(event_id, threshold, exclude_tickers, use_demo=False):
    exchange_client = login(use_demo)
    markets = exchange_client.get_event(event_id)['markets']
    for market in markets:
        if market['ticker'] not in exclude_tickers:
            movement_range = get_percentage_change_for_market(get_nasdaq_current_price(), market)
            print(movement_range)
            if ((movement_range[0] > .99 and movement_range[0] < 1.01) \
                    or (movement_range[1] > .99 and movement_range[1] < 1.01)):
                if market['yes_ask'] < threshold:
                    buy_yes_contract_at_market(market['ticker'], 10)

def get_next_sunday(skip_today_if_sunday=False):
    today = datetime.date.today()
    # Calculate the number of days until the next Sunday (0 is Monday, 6 is Sunday)
    days_until_sunday = (6 - today.weekday()) % 7
    print(f"today: {days_until_sunday}")
    # If today is Sunday, we want the next Sunday, so we add 7 days
    if days_until_sunday == 0:
        if skip_today_if_sunday:
            days_until_sunday = 7
        else:
            days_until_sunday = 0
    next_sunday = today + datetime.timedelta(days=days_until_sunday)
    next_sunday = next_sunday.strftime("%y%b%d").upper()

    return next_sunday

def create_tsa_event_id(next_sunday):
    event_id = f"KXTSAW-{next_sunday}"
    print(event_id)
    return event_id