from kalshi.src.kalshi import shared
import datetime
import pandas as pd

def get_next_sunday():
    today = datetime.date.today()
    # Calculate the number of days until the next Sunday (0 is Monday, 6 is Sunday)
    days_until_sunday = (6 - today.weekday()) % 7
    print(f"today: {days_until_sunday}")
    # If today is Sunday, we want the next Sunday, so we add 7 days
    if days_until_sunday == 0:
        days_until_sunday = 0
    next_sunday = today + datetime.timedelta(days=days_until_sunday)
    next_sunday = next_sunday.strftime("%y%b%d").upper()

    return next_sunday

def create_event_id(next_sunday):
    event_id = f"TSAW-{next_sunday}"
    print(event_id)
    return event_id

def find_markets_
next_sunday = get_next_sunday()
event_id = create_event_id(next_sunday)
exchange_client = shared.login()
df = pd.json_normalize(exchange_client.get_event("TSAW-24JUL14")['markets'])
df.to_csv("../data/pd_tsa_data.csv")
print(df['floor_strike'].head())
#print(exchange_client.get_markets(status='open',limit=10, series_ticker="TSAW"))