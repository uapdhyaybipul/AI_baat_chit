import requests
from requests.auth import HTTPBasicAuth
from twilio.rest import Client
from pydantic import BaseModel
from fastapi import FastAPI
import uvicorn
import os


app = FastAPI()
# Twilio Credentials (Replace with actual values)
ACCOUNT_SID = "AC04f394e5f81141f3725d8ecf0536648a"  # Your Twilio Account SID
AUTH_TOKEN = "c67b1f690a2135d1155fe7f162ad4ca0"  # Your Twilio Auth Token
Recording_path = "recordings"

class CallRecordings(BaseModel):
    call_sid: str

@app.post("/get_recordings")
def get_call_recording(request:CallRecordings):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    # Get recordings for a specific call
    recordings = client.recordings.list(call_sid=request.call_sid)

    for recording in recordings:
        print(f"Recording SID: {recording.sid}")
        recording_sid = recording.sid

    RECORDING_URL = f"https://api.twilio.com/2010-04-01/Accounts/AC04f394e5f81141f3725d8ecf0536648a/Recordings/{recording_sid}.mp3"
    

    RECORDING_URL.format(recording_sid)
    # Download the recording
    response = requests.get(RECORDING_URL, auth=HTTPBasicAuth(ACCOUNT_SID, AUTH_TOKEN))
    print(response.content)
    if response.status_code == 200:
    # Save the recording locally
        recording_file_path = os.path.join(Recording_path,f"{request.call_sid}_recording.mp3")
        with open(recording_file_path, "wb") as file:
            file.write(response.content)
        print("Recording downloaded successfully.")
    else:
        print(f"Failed to download recording: {response.status_code} - {response.text}")

    return {"recordings":"Recording Saved","recording_path":recording_file_path,"recording_name":f"{request.call_sid}_recording.mp3"}


if __name__ == "__main__":
    uvicorn.run(app, port=5501)


    
