from kalshi import shared
import uuid

def create_limit_orders_for_all_contracts(likelihoods):
    """
    Create limit orders for all contracts based on their calculated likelihoods.

    This function logs into the exchange client in demo mode, retrieves the event ticker for the
    next TSA event, and generates limit orders for each contract based on the likelihood of
    either a "yes" or "no" outcome. Orders are created with a margin of safety, meaning the
    order price is adjusted to 75% of the calculated likelihood. Contracts with extreme
    likelihoods (greater than 95% or less than 5%) are excluded to avoid edge cases.

    Steps:
    1. Log into the exchange client in demo mode.
    2. Generate the event ticker for the next TSA event.
    3. Retrieve and print the existing orders for the event.
    4. Loop through each contract and create a limit order if the likelihood is between 5% and 95%.
    5. Adjust the order price to 75% of the likelihood value to include a margin of safety.
    6. Submit the order to the exchange and store the order details in a list.
    7. Return the list of created orders.

    Parameters:
    likelihoods (dict): A dictionary of contract likelihoods where each key is a contract ticker
                        and the value contains the likelihood data including 'true_value', 'side',
                        and 'floor_strike'.

    Returns:
    list: A list of dictionaries representing the created orders, including contract ticker,
          order parameters, and side of the contract.
    """
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
