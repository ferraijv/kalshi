""" The purpose of this file is to run every day after market closes. It consists of the following tasks:

    1. Pulls weekly S&P event prices
    2. Compares weekly S&P prices against historical S&P movement to determine if event is over/under valued
    3. Places limit yes orders for underpriced markets
    4. Places limit no orders for overpriced markets
"""
import logging

import shared
import datetime
import kalshi
import yfinance as yf
import pandas as pd

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

def get_nasdaq_current_price():
    return yf.download('^NDX', start=datetime.date.today(), end=datetime.date.today())['Close'][0]


def get_likelihood(movement_range, data):
    data = shared.create_day_of_week(data)
    historical = shared.get_percentage_change(data)
    res = historical[(historical['percentage_change'] > movement_range[0]) & (historical['percentage_change'] < movement_range[1])]
    times_happened = len(res.index)
    total_weeks = len(historical.index)

    logging.info(f"Movement range: {movement_range}")
    logging.info(f"Times occurred: {times_happened}")
    logging.info(f"Total weeks: {total_weeks}")

    return times_happened/total_weeks

def compare_yes_likelihood_to_actual_price(likelihood, market):
    logging.info(f"----------Yes Analysis for {market}----------")
    yes_price = market['yes_ask']
    likelihood = likelihood*100
    if likelihood < 1.0 :
        likelihood = 1.0
    ratio = yes_price / likelihood
    logging.info(f"Yes price: {yes_price}")
    logging.info(f"Likelihood {likelihood}")
    logging.info(f"Ratio: {ratio}")
    if yes_price < 10:
        if ratio > 3:
            logging.info("Overpriced")
        elif ratio > .5 and ratio <= 3:
            logging.info("Fairly priced")
        elif ratio <= .5 and ratio > 0:
            logging.info("Underpriced")
            shared.buy_yes_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception
    elif yes_price >= 10 and yes_price < 60:
        if ratio > 2:
            logging.info("Overpriced")
        elif ratio > .6 and ratio <= 2:
            logging.info("Fairly priced")
        elif ratio <= .6 and ratio > 0:
            logging.info("Underpriced")
            shared.buy_yes_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception
    elif yes_price >= 60:
        if ratio > 1.5:
            logging.info("Overpriced")
        elif ratio > .8 and ratio <= 2:
            logging.info("Fairly priced")
        elif ratio <= .8 and ratio > 0:
            logging.info("Underpriced")
            shared.buy_yes_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception


def compare_no_likelihood_to_actual_price(likelihood, market):
    logging.info(f"----------No Analysis for {market}----------")
    no_price = (1 - market['yes_bid']/100)*100
    # Inverse likelihood because it's for no markets
    likelihood = 1 - likelihood
    likelihood = likelihood*100
    if likelihood < 1.0 :
        likelihood = 1.0
    ratio = no_price / likelihood
    logging.info(f"No price: {no_price}")
    logging.info(f"Likelihood {likelihood}")
    logging.info(f"Ratio: {ratio}")
    if no_price < 10:
        if ratio > 3:
            logging.info("Overpriced")
        elif ratio > .5 and ratio <= 3:
            logging.info("Fairly priced")
        elif ratio <= .5 and ratio > 0:
            logging.info("Underpriced")
            shared.buy_no_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception
    elif no_price >= 10 and no_price < 60:
        if ratio > 2:
            logging.info("Overpriced")
        elif ratio > .6 and ratio <= 2:
            logging.info("Fairly priced")
        elif ratio <= .6 and ratio > 0:
            logging.info("Underpriced")
            shared.buy_no_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception
    elif no_price >= 60:
        if ratio > 1.5:
            logging.info("Overpriced")
        elif ratio > .8 and ratio <= 2:
            logging.info("Fairly priced")
        elif ratio <= .8 and ratio > 0:
            logging.info("Underpriced")
            shared.buy_no_contract_at_market(market['ticker'], 10)
        elif ratio == 0:
            logging.info("Ratio: 0")
        else:
            raise Exception


def determine_if_markets_in_event_are_fairly_priced(event, data):
    """
    For each market in the event determines if market is fairly priced based on historical data. If market is
    underpriced, it will purchase contracts
    :param event: event data
    :param data: historical data used to calculate likelihoods
    :return:
    """
    markets = event['markets']
    logging.info(markets)
    current_price = get_nasdaq_current_price()
    for market in markets:
        logging.info("************* New analysis marker *************")
        movement_range = get_percentage_change(current_price, market)
        likelihood = get_likelihood(movement_range, data)
        compare_yes_likelihood_to_actual_price(likelihood, market)
        compare_no_likelihood_to_actual_price(likelihood, market)

    return True

def main():

    timestamp = str(datetime.datetime.now())
    logname = f"../logs/logs_{timestamp}.log"

    logging.basicConfig(
        filename=logname,
        level=logging.INFO,
        force=True
    )

    # Get weekly nasdaq market id
    market_id = shared.create_weekly_nasdaq_market_id()
    logging.info(f"Market ID: {market_id}")
    exchange_client = shared.login()
    data = shared.get_nasdaq_data()
    determine_if_markets_in_event_are_fairly_priced(exchange_client.get_event(market_id), data)
    log_file_contents = shared.get_log_file_contents(logname)

    shared.send_email(log_file_contents)

if __name__ == '__main__':
    main()


