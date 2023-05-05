from typing import Optional
import kalshi
import shared
import datetime
import uuid
import logging


logging.basicConfig(level=logging.DEBUG)


if __name__ == '__main__':
    market_id = shared.create_sp_market_id(run_date=datetime.date.today())
    shared.cancel_all_orders_for_market(market_id)
    shared.create_no_orders_for_every_contract_in_market(market_id, [], 15)

