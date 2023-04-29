
import datetime
import logging
import uuid
import yfinance as yf
import boto3
import shared

logging.basicConfig(level=logging.DEBUG)

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








def create_limit_order_at_current_price_level(market_id):
    """
    Creates buy limit order at current market price for all markets in event
    :param market_id: str id of the event
    :return:
    """

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

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    exchange_client = shared.login()
    market_id = shared.create_sp_market_id(run_date=datetime.date.today())
    markets = check_for_markets_under_x_cents(0.15, market_id)
    markets = [(x['subtitle'], x['no_ask']) for x in markets]
    shared.send_email(str(markets))






