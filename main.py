
import datetime
from getpass import getpass
from kalshi import ExchangeClient
import logging
import uuid
import calendar

logging.basicConfig(level=logging.DEBUG)

def login():
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


def create_no_orders_for_every_contract_in_market(events, limit_price=48):
    """
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

def get_todays_date():

    month = calendar.month_abbr[datetime.date.today().month].upper()
    year = str(datetime.date.today().year)[2:]
    day = datetime.date.today().day
    date_string = f"{year}{month}{day}"

    logging.debug(date_string)

    return date_string

def create_sp_market_id(todays_date):

    logging.debug(f"Day: {datetime.date.today().weekday()}")
    if datetime.date.today().weekday() == 4:
        market_id = f"INXW-{todays_date}"
    else:
        market_id = f"INXD-{todays_date}"

    logging.debug(f"Market ID: {market_id}")
    return market_id

def cancel_all_orders_for_market(market_id):

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


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # At 8
    todays_date = get_todays_date()
    exchange_client = login()
    market_id = create_sp_market_id(todays_date)
    market_id = 'INXD-23MAR27' # remove in production
    #events = exchange_client.get_event(market_id)
    # TODO Create logic to check if orders already exist
    #create_no_orders_for_every_contract_in_market(events=events, limit_price=48)

    # At 12
    #current_positions = exchange_client.get_positions(event_ticker=market_id)['market_positions']
    #check_current_order_status(current_positions, market_id)
    #cancel_all_orders_for_market(market_id)

    sell_all_contracts_for_market(market_id)




