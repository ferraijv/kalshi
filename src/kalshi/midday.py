import shared
import datetime

if __name__ == '__main__':
    market_id = shared.create_sp_market_id(run_date=datetime.date.today())
    fulfilled_orders = shared.check_for_fulfilled_orders(market_id)
    if len(fulfilled_orders) == 0:
        shared.cancel_all_orders_for_market(market_id)