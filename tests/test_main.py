from src.kalshi import main
import datetime

print(main.format_date())

def test_get_todays_date():
    date_to_test = datetime.datetime.strptime("20230801", "%Y%m%d")
    assert main.format_date(date_to_test) == "23AUG01"

def test_create_sp_market_id():
    date_to_test = datetime.datetime.strptime("20230324", "%Y%m%d")
    assert main.create_sp_market_id(date_to_test) == "INXW-23MAR24"
