
import datetime
from getpass import getpass
from kalshi import ExchangeClient
import logging
import uuid
import calendar
from typing import Optional
import yfinance as yf
import boto3
from botocore.exceptions import ClientError


logging.basicConfig(level=logging.DEBUG)

def login():
    """ Prompt user for Kalshi login credentials and return exchange client """
    email = getpass("Email: ")
    password = getpass("Password: ")
    exchange_api_base = "https://demo-api.kalshi.co/trade-api/v2"

    exchange_client = ExchangeClient(exchange_api_base, email, password)

    print(exchange_client.user_id)

    return exchange_client

def get_all_markets(exchange_client):
    i = 0
    all_markets = []
    cursor = None
    while i < 10:
        markets = exchange_client.get_markets(cursor=cursor)
        cursor = markets['cursor']
        logging.info(f"Cursor: {cursor}")
        logging.info(f"Count markets: {len(markets['markets'])}")
        all_markets = all_markets + markets["markets"]
        i = i+1

    return all_markets


def create_no_orders_for_every_contract_in_market(events: dict, limit_price: Optional[int] = 48):
    """
    Create no order for every contract in a given market
    events dict: dictionary of events for particular market
    limit_price int: integer for number of cents for limit price
    """
    order_params = {
        "action": "buy",
        "type": "limit",
        "side": "no",
        "count": 100,
        "no_price": limit_price

    }
    for event in events['markets']:
        exchange_client.create_order(ticker=event["ticker"], client_order_id=str(uuid.uuid4()), **order_params)


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


def cancel_all_orders_for_market(market_id: uuid):
    """ Iterates through each currently open order for a given market and decreases remaining count to 0 """

    all_orders = exchange_client.get_orders(event_ticker=market_id)['orders']
    logging.debug(all_orders)
    orders_to_cancel = [(e['order_id'], e['remaining_count']) for e in all_orders if e['remaining_count'] > 0]

    for order in orders_to_cancel:
        logging.debug(f"Canceling order id: {order[0]}")
        exchange_client.decrease_order(order_id=order[0], reduce_by=order[1])
        logging.debug(f"{order[0]} cancelled")


def create_limit_order_at_current_price_level(market_id):

    order_params = {
        "action": "buy",
        "type": "limit",
        "side": "no",
        "count": 100,

    }

    for event in exchange_client.get_event(market_id)['markets']:
        ticker = event['ticker']
        limit_price = event['no_ask']-1
        exchange_client.create_order(
            ticker=event["ticker"],
            client_order_id=str(uuid.uuid4()),
            limit_price=limit_price,
            **order_params
        )

    return True

def sell_all_contracts_for_market(market_id):

    order_params = {
        "action": "sell",
        "type": "market",
        "side": "no",

    }

    for event in exchange_client.get_positions(event_ticker=market_id)['market_positions']:
        exchange_client.create_order(
            event['ticker'],
            client_order_id=str(uuid.uuid4()),
            count=event['total_traded']
        )


def check_current_order_status(current_positions, market_id):

    # Check if no orders have been completed
    if all([event['total_traded'] == 0 for event in current_positions]):
        logging.debug("No orders completed. Canceling all orders")
        cancel_all_orders_for_market(market_id)
    # Check if one order was completed
    if len([e['ticker'] for e in current_positions if e['resting_orders_count']==0 and e['total_traded'] > 0]) == 1:
        logging.debug("One order was completed. No additional actions taken")
    # Check if two or more orders completed
    if len([e['ticker'] for e in current_positions if e['resting_orders_count']==0 and e['total_traded'] > 0]) > 1:
        logging.debug("Two or more orders completed. Canceling all existing orders and replacing with new price")
        cancel_all_orders_for_market(market_id)
        create_limit_order_at_current_price_level(market_id)
    # Check for one partial order
    if len([e['ticker'] for e in current_positions if e['resting_orders_count'] > 0 and e['total_traded'] > 0]) == 1:
        print("One partial order completed. Cancel all existing orders and sell contracts")
        cancel_all_orders_for_market(market_id)
        sell_all_contracts_for_market(market_id)

def get_s_and_p_data():
    return yf.download('SPY', start='2023-01-01', end=datetime.date.today())

def create_day_of_week(sp_data):
    sp_data['day_of_week'] = sp_data.index.dayofweek
    sp_data['year'] = sp_data.index.year
    sp_data['week'] = sp_data.index.isocalendar().week
    sp_data['year_week'] = sp_data['year'].astype(str) + sp_data['week'].astype(str)
    return sp_data

def get_sp_percentage_change(sp_data, day_of_week=1):
    subset = sp_data[(sp_data['day_of_week'] == day_of_week) | (sp_data['day_of_week'] == 4)]
    subset['friday_close'] = subset.groupby(["year_week"])['Close'].shift(-1)
    subset = subset[(subset['day_of_week'] == day_of_week)]
    subset['percentage_change'] = subset["Close"]/subset["friday_close"]
    return subset

def get_likelihood_of_similar_change(data, percentage_window):
    df = data[(data["percentage_change"] >= percentage_window[0]) & (data["percentage_change"] <= percentage_window[1])]
    return len(df.index)/len(data.index)

def check_for_markets_under_x_cents(threshold, event_id):
    event_id = 'INXD-23MAY01'
    markets = exchange_client.get_event(event_id)['markets']
    markets = [x for x in markets if x['no_ask'] < threshold]
    return markets

def send_text():
    sns = boto3.client('sns')
    number = '+18049298620'
    sns.publish(PhoneNumber=number, Message='example text message')

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
    BODY_HTML = """<html>
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

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    exchange_client = login()
    market_id = create_sp_market_id(run_date=datetime.date.today())
    markets = check_for_markets_under_x_cents(0.15, market_id)
    print(markets)
    send_email(str(markets))






