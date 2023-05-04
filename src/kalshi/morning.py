from typing import Optional
import kalshi
import shared
import datetime
import uuid
import logging


logging.basicConfig(level=logging.DEBUG)

def create_no_orders_for_every_contract_in_market(market_id: str, limit_price: Optional[int] = 15):
    """
    Create no order for every contract in a given market
    events dict: dictionary of events for particular market
    limit_price int: integer for number of cents for limit price
    """

    exchange_client = shared.login()
    events = exchange_client.get_event(market_id)

    order_params = {
        "action": "buy",
        "type": "limit",
        "side": "no",
        "count": 100,
        "no_price": limit_price

    }
    for event in events['markets']:
        logging.info(f"Creating {order_params['action']} order for {event['ticker']} at {order_params['no_price']}")
        exchange_client.create_order(ticker=event["ticker"], client_order_id=str(uuid.uuid4()), **order_params)

    return True


if __name__ == '__main__':
    market_id = shared.create_sp_market_id(run_date=datetime.date.today())
    shared.cancel_all_orders_for_market(market_id)
    create_no_orders_for_every_contract_in_market(market_id, 12)

