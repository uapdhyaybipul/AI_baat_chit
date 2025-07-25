from http import client
import json
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
from pydantic import BaseModel
from pipecat_utils import run_bot  # Import from pipecat_logic.py
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

load_dotenv(override=True)  # Load .env file

# Twilio credentials
account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
TO_NUMBER = "+918957819309"  # Replace with your actual number
TWILIO_NUMBER = os.environ["TWILIO_PHONE_NUMBER"]

client = Client(account_sid, auth_token)

# Temporary storage for call data
call_data_store = {}

class CallRequest(BaseModel):
    to_number: str = "+91"
    candidate_name: str
    List_of_question: list[str]
    Jd : str

@app.post("/make_call")
async def make_call(request: CallRequest):
    try:
        call = client.calls.create(
            record = True,
            twiml=open("templates/streams.xml").read(),
            to=request.to_number,
            from_=TWILIO_NUMBER
        )
        # Store candidate_name and List_of_question with call_sid
        call_data_store[call.sid] = {
            "candidate_name": request.candidate_name,
            "List_of_question": request.List_of_question,
            "Jd":request.Jd
        }
        print(call.sid)
        print(call_data_store)
        return {"message": "Call initiated", "call_sid": call.sid, "candidate_name": request.candidate_name, "List_of_question": request.List_of_question, "Jd":request.Jd}
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
    call_sid = call_data["start"]["callSid"]  # Get call_sid from Twilio's start message
    print("Stream ID in websocket: ", stream_sid)
    
    # Retrieve candidate_name and List_of_question from storage
    call_info = call_data_store.get(call_sid, {})
    candidate_name = call_info["candidate_name"]
    List_of_question = call_info.get("List_of_question", [])
    Jd = call_info["Jd"]
    
    # Pass candidate_name and List_of_question to run_bot
    await run_bot(websocket, stream_sid, candidate_name, List_of_question, Jd)
    
    # Optionally clean up after the call ends
    call_data_store.pop(call_sid, None)

if __name__ == "__main__":
    uvicorn.run(app, port=5500)