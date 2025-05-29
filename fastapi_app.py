# fastapi_app.py
import json

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

from pipecat_utils import run_bot  # Import from pipecat_logic.py
# from twilio_setup import initiate_twilio_call #Import from twilio_setup.py

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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