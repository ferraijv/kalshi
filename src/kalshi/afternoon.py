from kalshi import shared
import datetime

if __name__ == '__main__':
    market_id = shared.create_sp_market_id(run_date=datetime.date.today())
    shared.sell_all_contracts_for_market(market_id)
