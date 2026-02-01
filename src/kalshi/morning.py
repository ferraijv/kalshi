from kalshi import shared
import datetime
import logging


logging.basicConfig(level=logging.DEBUG)

def main():
    """
    Creates no order for every market in daily S&P event at specified price

    :return: None
    """
    market_id = shared.create_sp_market_id(run_date=datetime.date.today())
    market_id = 'INXD-23JUL17'
    shared.cancel_all_orders_for_market(market_id, use_demo=True)
    shared.create_no_orders_for_every_contract_in_market(market_id, [], 45, use_demo=True)

if __name__ == '__main__':
    main()

