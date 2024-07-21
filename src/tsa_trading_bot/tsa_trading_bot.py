from kalshi.src.kalshi import shared
import get_recent_tsa_data
import create_next_week_prediction
def main():
    """

    :return:
    """

    ## Get recent TSA data
    get_recent_tsa_data()

    ## Create next week TSA prediction
    prediction = create_next_week_prediction()

    ## Email prediction result
    shared.send_email(prediction)




