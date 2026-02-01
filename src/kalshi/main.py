
import datetime
import logging
import uuid
from kalshi import shared

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

def check_for_markets_under_x_cents(threshold, event_id):
    markets = exchange_client.get_event(event_id)['markets']
    markets = [x for x in markets if x['no_ask'] < threshold]
    return markets


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    exchange_client = shared.login()
    market_id = shared.create_sp_market_id(run_date=datetime.date.today())
    markets = check_for_markets_under_x_cents(0.15, market_id)
    markets = [(x['subtitle'], x['no_ask']) for x in markets]
    shared.send_email(str(markets))





