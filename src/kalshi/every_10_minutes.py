import shared
import datetime

if __name__ == '__main__':
    # If any order fulfilled, create limit buy no order
    market_id = shared.create_sp_market_id(run_date=datetime.date.today())
    fulfilled_orders = shared.check_for_fulfilled_orders(market_id)
    print(fulfilled_orders)
    markets_to_exclude = [x['ticker'] for x in fulfilled_orders]
    print(f"Markets to exclude: {markets_to_exclude}")
    if len(fulfilled_orders) > 0:
        shared.create_no_orders_for_every_contract_in_market(market_id, markets_to_exclude, 80)


