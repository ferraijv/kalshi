import shared
import uuid

def create_limit_orders_for_all_contracts(likelihoods):
    exchange_client = shared.login(use_demo=True)
    event_ticker = shared.create_tsa_event_id(shared.get_next_sunday())
    print(exchange_client.get_orders(event_ticker=event_ticker)['orders'])
    orders = []
    for contract_ticker, likelihood in likelihoods.items():
        if likelihood['true_value'] < .95 and likelihood['true_value'] > .05: # Things get weird at the extremes
            order_params = {
                "action": "buy",
                "type": "limit",
                "side": likelihood['side'],
                "count": 10,
                f"{likelihood['side']}_price": int(round(likelihood['true_value']*.75, 2)*100) # Margin of safety

            }
            print(order_params)
            exchange_client.create_order(ticker=contract_ticker, client_order_id=str(uuid.uuid4()), **order_params)
            order_params['ticker'] = contract_ticker
            orders.append(order_params)

    return orders
