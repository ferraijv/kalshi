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
    shared.determine_if_markets_in_event_are_fairly_priced(exchange_client.get_event(market_id), data)
    log_file_contents = shared.get_log_file_contents(logname)

    shared.send_email(log_file_contents)

if __name__ == '__main__':
    main()


