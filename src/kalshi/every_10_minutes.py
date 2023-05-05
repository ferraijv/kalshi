import shared
import datetime

if __name__ == '__main__':
    market_id = shared.create_sp_market_id(run_date=datetime.date.today())
    fulfilled_orders = shared.check_for_fulfilled_orders(market_id)
    # exclude markets that we already have positions in
    markets_to_exclude = [x['ticker'] for x in fulfilled_orders]
    print(f"Markets to exclude: {markets_to_exclude}")
    if len(fulfilled_orders) > 0:
        # if we already have one order completed for 15 cents then we put another order in at 80 cents
        # to achieve negative risk
        shared.cancel_all_orders_for_market(market_id)
        shared.create_no_orders_for_every_contract_in_market(market_id, markets_to_exclude, 80)
        # If we have already achieved negative risk, put in orders for all markets
        if shared.check_if_negative_risk_is_met_for_market(market_id):
            shared.cancel_all_orders_for_market(market_id)
            shared.create_no_orders_for_every_contract_in_market(market_id, markets_to_exclude, 90)


