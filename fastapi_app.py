# fastapi_app.py
from http import client
import json

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
from pydantic import BaseModel
from pipecat_utils import run_bot  # Import from pipecat_logic.py
# from twilio_setup import initiate_twilio_call #Import from twilio_setup.py
from dotenv import load_dotenv
import os
from twilio.rest import Client
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
        return {"message": "Call initiated", "call_sid": call.sid,"candidate_name":request.candidate_name,"List_of_question":request.List_of_question}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/")
async def start_call():
    """Handles Twilio's initial request; returns TwiML."""
    return HTMLResponse(content=open("templates/streams.xml").read(), media_type="application/xml")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles the WebSocket connection from Twilio."""
    await websocket.accept()
    start_data = websocket.iter_text()
    await start_data.__anext__()  # Wait for the "start" message
    call_data = json.loads(await start_data.__anext__())
    stream_sid = call_data["start"]["streamSid"]
    print("Stream iD in websocket: ",stream_sid)
    await run_bot(websocket, stream_sid)



if __name__ == "__main__":
    # initiate_twilio_call() # Initiate call first!
    uvicorn.run(app, port=5500)