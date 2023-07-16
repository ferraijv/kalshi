from src.kalshi import shared, kalshi
import datetime


def test_get_todays_date():
    date_to_test = datetime.datetime.strptime("20230801", "%Y%m%d")
    assert shared.format_date(date_to_test) == "23AUG01"

def test_create_sp_market_id():
    date_to_test = datetime.datetime.strptime("20230324", "%Y%m%d")
    assert shared.create_sp_market_id(date_to_test) == "INXW-23MAR24"
