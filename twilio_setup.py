# twilio_setup.py
import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv(override=True) # Load .env file

# Twilio credentials
account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
TO_NUMBER = "+918957819309"  # Replace with your actual number
TWILIO_NUMBER = os.environ["TWILIO_PHONE_NUMBER"]

client = Client(account_sid, auth_token)

TO_NUMBER = "+919783596594"  #  number

call = client.calls.create(
    record=True,
    twiml=open("templates/streams.xml").read(),
    to=TO_NUMBER,
    from_=os.environ["TWILIO_PHONE_NUMBER"]
)

print(call.sid)