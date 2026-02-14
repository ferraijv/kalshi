from kalshi import shared
from kalshi.config import load_config
from kalshi import risk_controls
import uuid
import datetime

def create_limit_orders_for_all_contracts(likelihoods, run_date=None, risk_config=None, realized_daily_pnl=0.0):
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
    if risk_config is None:
        cfg = load_config()
        active_risk_config = risk_controls.RiskConfig(
            bankroll_dollars=cfg.tsa_bankroll_dollars,
            event_risk_pct=cfg.tsa_event_risk_pct,
            max_market_share_of_event=cfg.tsa_max_market_share_of_event,
            daily_max_loss_pct=cfg.tsa_daily_max_loss_pct,
            min_contracts=cfg.tsa_min_contracts,
            max_contracts_per_market=cfg.tsa_max_contracts_per_market,
        )
    else:
        active_risk_config = risk_config
    exchange_client = shared.login(use_demo=True)
    event_ticker = shared.create_tsa_event_id(shared.get_next_sunday(reference_date=run_date))
    trade_date = run_date or datetime.date.today()
    state = risk_controls.RiskState(daily_realized_pnl={trade_date: float(realized_daily_pnl)})
    print(exchange_client.get_orders(event_ticker=event_ticker)['orders'])
    orders = []
    for contract_ticker, likelihood in likelihoods.items():
        if likelihood['true_value'] < .95 and likelihood['true_value'] > .05: # Things get weird at the extremes
            side_price = float(round(likelihood['true_value']*.75, 2))
            contracts, reject_reason = risk_controls.contracts_for_order(
                active_risk_config,
                state,
                event_id=event_ticker,
                market_ticker=contract_ticker,
                side_price=side_price,
                trade_date=trade_date,
            )
            if contracts <= 0:
                print(f"Skipping {contract_ticker}: {reject_reason}")
                continue
            order_params = {
                "action": "buy",
                "type": "limit",
                "side": likelihood['side'],
                "count": contracts,
                f"{likelihood['side']}_price": int(side_price*100) # Margin of safety

            }
            print(order_params)
            exchange_client.create_order(ticker=contract_ticker, client_order_id=str(uuid.uuid4()), **order_params)
            order_params['ticker'] = contract_ticker
            orders.append(order_params)
            risk_controls.record_trade(
                state,
                event_id=event_ticker,
                market_ticker=contract_ticker,
                trade_date=trade_date,
                side_price=side_price,
                contracts=contracts,
                pnl=0.0,  # live realized pnl is tracked externally
            )

    return orders
