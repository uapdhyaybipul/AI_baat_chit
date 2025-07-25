# twilio_setup.py
import os
from twilio.rest import Client
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
from pydantic import BaseModel





app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


load_dotenv(override=True) # Load .env file

# Twilio credentials
account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
TO_NUMBER = "+918957819309"  # Replace with your actual number
TWILIO_NUMBER = os.environ["TWILIO_PHONE_NUMBER"]

client = Client(account_sid, auth_token)

class CallRequest(BaseModel):
    to_number: str = "+91"
    candidate_name: str
    List_of_question: list[str]

@app.post("/make_call")
async def make_call(request: CallRequest):
    try:
        call = client.calls.create(
            twiml=open("templates/streams.xml").read(),
            to=request.to_number,
            from_=TWILIO_NUMBER
        )
        print(call.sid)
        return {"message": "Call initiated", "call_sid": call.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
