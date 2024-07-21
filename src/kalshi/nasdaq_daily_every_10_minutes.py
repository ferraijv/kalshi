from kalshi.src.kalshi import shared


def main():
    """
    Every 10 mins:
        1. Check if any yes markets within 1% of current price are selling below $0.03
        2. If any meet above condition: buy and set limit sell order for $x
    :return:
    """
    event_id = shared.create_nasdaq_event_id()
    fulfilled_orders = shared.check_for_fulfilled_orders(event_id)
    markets_to_exclude = [x['ticker'] for x in fulfilled_orders]
    shared.get_markets_with_yes_price_below_threshold(event_id, markets_to_exclude, 5)


if __name__ == '__main__':
    main()