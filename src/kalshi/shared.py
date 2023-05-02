from kalshi import ExchangeClient
import calendar
from typing import Optional
from botocore.exceptions import ClientError
import json
import boto3
import datetime
import logging
import uuid

logging.basicConfig(level=logging.DEBUG)

def login():
    """ Prompt user for Kalshi login credentials and return exchange client """
    creds = get_secret("kalshi_credentials")
    exchange_api_base = "https://trading-api.kalshi.com/trade-api/v2"
    exchange_client = ExchangeClient(exchange_api_base, creds['kalshi_username'], creds['kalshi_password'])

    return exchange_client

def send_email(body):
    SENDER = "ferraioloj@gmail.com"

    # Replace recipient@example.com with a "To" address. If your account
    # is still in the sandbox, this address must be verified.
    RECIPIENT = "ferraioloj@gmail.com"

    # The subject line for the email.
    SUBJECT = "Amazon SES Test (SDK for Python)"

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = body

    # The HTML body of the email.
    BODY_HTML = f"""<html>
    {body}
    </html>
                """

    # The character encoding for the email.
    CHARSET = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses')

    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])

def get_secret(secret_name):

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager'
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("The requested secret " + secret_name + " was not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            print("The request was invalid due to:", e)
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            print("The request had invalid params:", e)
        elif e.response['Error']['Code'] == 'DecryptionFailure':
            print("The requested secret can't be decrypted using the provided KMS key:", e)
        elif e.response['Error']['Code'] == 'InternalServiceError':
            print("An error occurred on service side:", e)
    else:
        # Secrets Manager decrypts the secret value using the associated KMS CMK
        # Depending on whether the secret was a string or binary, only one of these fields will be populated
        if 'SecretString' in get_secret_value_response:
            text_secret_data = get_secret_value_response['SecretString']
        else:
            binary_secret_data = get_secret_value_response['SecretBinary']

    return json.loads(get_secret_value_response['SecretString'])

def format_date(date_to_format = datetime.date.today()):
    """ Create today's date in format '99MAR21' """

    month = calendar.month_abbr[date_to_format.month].upper()
    year = str(date_to_format.year)[2:]
    day = date_to_format.strftime("%d")
    date_string = f"{year}{month}{day}"

    logging.debug(date_string)

    return date_string

def create_sp_market_id(run_date = datetime.date.today()):
    """ Create market id for S&P 500 market """

    run_date_formatted = format_date(run_date)
    logging.debug(f"Day: {run_date.weekday()}")
    if run_date.weekday() == 4:
        market_id = f"INXW-{run_date_formatted}"
    else:
        market_id = f"INXD-{run_date_formatted}"

    logging.debug(f"Market ID: {market_id}")
    return market_id

def cancel_all_orders_for_market(market_id):
    """ Iterates through each currently open order for a given market and decreases remaining count to 0 """

    exchange_client = login()
    all_orders = exchange_client.get_orders(event_ticker=market_id)['orders']
    logging.debug(all_orders)
    orders_to_cancel = [(e['order_id'], e['remaining_count']) for e in all_orders if e['remaining_count'] > 0]

    orders_cancelled = []
    for order in orders_to_cancel:
        logging.debug(f"Canceling order id: {order[0]}")
        exchange_client.decrease_order(order_id=order[0], reduce_by=order[1])
        orders_cancelled.append(order)
        logging.debug(f"{order[0]} cancelled")

    logging.debug("Done canceling existing orders")

    send_email(f"Orders Cancelled: {str(orders_cancelled)}")

    return True


def sell_all_contracts_for_market(market_id):

    exchange_client = login()
    order_params = {
        "action": "sell",
        "type": "market",
        "side": "no",

    }

    contracts_sold = []
    for event in exchange_client.get_positions(event_ticker=market_id)['market_positions']:
        exchange_client.create_order(
            event['ticker'],
            client_order_id=str(uuid.uuid4()),
            count=event['total_traded']
        )
        contracts_sold.append(event)

    send_email(f"Sold orders created: {str(contracts_sold)}")


