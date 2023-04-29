import shared
import datetime

if __name__ == '__main__':
    market_id = shared.create_sp_market_id(run_date=datetime.date.today())
    shared.cancel_all_orders_for_market(market_id)