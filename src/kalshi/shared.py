from kalshi import ExchangeClient
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

logging.basicConfig(level=logging.DEBUG)

def login(use_demo=False):
    """ Prompt user for Kalshi login credentials and return exchange client """
    creds = get_secret("kalshi_credentials")
    exchange_api_base = "https://trading-api.kalshi.com/trade-api/v2"
    if use_demo:
        exchange_api_base = "https://demo-api.kalshi.co/trade-api/v2"
    exchange_client = ExchangeClient(exchange_api_base, creds['kalshi_username'], creds['kalshi_password'])

    return exchange_client

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
    #exchange_client.create_order(market_id, client_order_id=str(uuid.uuid4()), **order_params)

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
