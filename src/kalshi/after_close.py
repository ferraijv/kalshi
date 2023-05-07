""" The purpose of this file is to run every day after market closes. It consists of the following tasks:

    1. Pulls weekly S&P event prices
    2. Compares weekly S&P prices against historical S&P movement to determine if event is over/under valued
    3. Places limit yes orders for underpriced markets
    4. Places limit no orders for overpriced markets
"""
import shared
import datetime
import kalshi
import yfinance as yf


def get_percentage_change(current_price, market):
    if market.get("floor_strike"):
        lower_bound = market['floor_strike']/current_price
    else:
        lower_bound = 0
    if market.get("cap_strike"):
        upper_bound = market['cap_strike']/current_price
    else:
        upper_bound = 9999999

    results = (lower_bound, upper_bound)

    return results

def get_sp_current_price():
    return yf.download('^GSPC', start=datetime.date.today(), end=datetime.date.today())['Close'][0]


def get_sp_likelihood(movement_range, sp_data):
    sp_data = shared.create_day_of_week(sp_data)
    sp_historical = shared.get_sp_percentage_change(sp_data)
    res = sp_historical[(sp_historical['percentage_change'] > movement_range[0]) & (sp_historical['percentage_change'] < movement_range[1])]
    times_happened = len(res.index)
    total_weeks = len(sp_historical.index)

    print(f"Times occurred: {times_happened}")
    print(f"Total weeks: {total_weeks}")

    return times_happened/total_weeks

def compare_likelihood_to_actual_price(likelihood, market):
    yes_price = market['yes_ask']
    likelihood = likelihood*100
    if likelihood < 1.0 :
        likelihood = 1.0
    ratio = yes_price / likelihood
    print(f"Yes price: {yes_price}")
    print(f"Ratio: {ratio}")
    if yes_price < 10:
        if ratio > 3:
            print("Overpriced")
        elif ratio > .5 and ratio <= 3:
            print("Fairly priced")
        elif ratio <= .5:
            print("Underpriced")
        else:
            raise Exception
    elif yes_price >= 10 and yes_price < 60:
        if ratio > 2:
            print("Overpriced")
        elif ratio > .6 and ratio <= 2:
            print("Fairly priced")
        elif ratio <= .6:
            print("Underpriced")
        else:
            raise Exception
    elif yes_price >= 60:
        if ratio > 1.5:
            print("Overpriced")
        elif ratio > .8 and ratio <= 2:
            print("Fairly priced")
        elif ratio <= .8:
            print("Underpriced")
        else:
            raise Exception


def determine_if_markets_in_event_are_fairly_priced(event, sp_data):
    markets = event['markets']
    print(markets)
    current_price = get_sp_current_price()
    for market in markets:
        print(f"Market {market['subtitle']}")
        movement_range = get_percentage_change(current_price, market)
        print(f"Movement range: {movement_range}")
        likelihood = get_sp_likelihood(movement_range, sp_data)
        print(f"Likelihood {likelihood}")
        compare_likelihood_to_actual_price(likelihood, market)



if __name__ == '__main__':
    market_id = shared.create_sp_market_id(run_date=datetime.date.today())
    exchange_client = shared.login()
    sp_data = shared.get_s_and_p_data()
    determine_if_markets_in_event_are_fairly_priced(exchange_client.get_event("INXW-23MAY12"), sp_data)

