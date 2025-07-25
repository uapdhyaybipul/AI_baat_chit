# AI Baat Chit

AI Baat Chit is a Python-based voice-interview assistant that integrates Twilio telephony with Google's Gemini AI for real-time conversational interviews. Using the Pipecat framework, it orchestrates live audio streaming between Twilio and Gemini to conduct natural spoken conversations. The system also downloads each call recording, runs speech-to-text transcription, and produces a PDF report with charts analyzing the call. There is no web frontend - the entire solution is a backend service (built with FastAPI) and a report generator using ReportLab. Pipecat is "an open-source Python framework for building real-time voice and multimodal conversational agents"[^1], and we use it to connect Twilio's audio stream to Gemini's Live API.

## Features

*   **Real-time Voice AI**: Conduct live voice calls where the caller talks to Google's Gemini AI through Twilio. Gemini's Multimodal Live API is designed for low-latency, two-way spoken conversations[^2]. The caller hears Gemini's synthesized responses in real time.
*   **Twilio Integration**: Uses Twilio's Programmable Voice and **Media Streams** to handle phone calls. When a call is received, Twilio executes a `<Stream>` TwiML instruction to fork the call's raw audio into a WebSocket stream[^3]. Our FastAPI app handles this WebSocket, forwarding audio to Gemini.
*   **Pipecat Pipeline**: Leverages Pipecat to simplify audio transport. Pipecat pipelines route the live audio from Twilio to Gemini and send Gemini's audio back out. This modular pipeline approach makes it easy to insert processing steps (e.g. pre-processing, analytics) if needed.
*   **Automated Reporting**: After each call, the recording is fetched via the Twilio API. A Python script transcribes the speech (using Google's Speech-to-Text) and generates a PDF report. The report, created with ReportLab, includes the call transcript and a pie chart (or other visual) summarizing call metrics and behavior.
*   **Backend Only**: No frontend UI is provided. Interaction is entirely via phone (Twilio) and the backend scripts. Reports are saved as PDF files for review. All code is in Python, and ReportLab is used for PDF generation.

## Installation and Setup

1.  **Clone the repository and install dependencies.**
    ```bash
    git clone https://github.com/uapdhyaybipul/AI_baat_chit.git
    cd AI_baat_chit
    python3 -m venv venv         # optional but recommended
    source venv/bin/activate
    pip install -r requirements.txt
    pip install pipecat-ai # install Pipecat if not included in requirements
    ```

2.  **Configure environment variables.** Rename the provided `.env.template` or create a new `.env` file in the repo root. Set the following keys:
    *   **`GOOGLE_API_KEY`**: Your Google Cloud API key for the Gemini (Vertex AI) and Speech-to-Text services.
    *   **`TWILIO_ACCOUNT_SID`** and **`TWILIO_AUTH_TOKEN`**: Your Twilio Account SID and Auth Token (from the Twilio Console).
    *   **`TWILIO_PHONE_NUMBER`**: The phone number (in E.164 format) you purchased on Twilio.
    *   **`NGROK_URL`** (or your public URL): The HTTPS URL for your server (e.g. the ngrok domain). For example, if you run `ngrok http 5500`, use the ngrok HTTPS URL here.
    *   **`PORT`**: The port on which FastAPI will run (default is `5500`).
    *   **`PUBLIC_URL`**: Your public domain or ngrok host (without protocol). Twilio will use this to reach your webhooks.
    *   **`Recording_path`**, **`Pie_image_path`**, **`Report_path`**: Local directories where call recordings, pie charts, and PDF reports will be saved. Adjust these to valid paths on your system.

    For example, your `.env` might contain lines like:
    ```dotenv
    GOOGLE_API_KEY=YOUR_GOOGLE_KEY
    TWILIO_ACCOUNT_SID=AC123456789abcdef
    TWILIO_AUTH_TOKEN=your_twilio_token
    TWILIO_PHONE_NUMBER=+1234567890
    NGROK_URL=https://abcd1234.ngrok-free.app
    PORT=5500
    PUBLIC_URL=abcd1234.ngrok-free.app
    Recording_path=/home/user/ai_baat_chit/recordings
    Pie_image_path=/home/user/ai_baat_chit/pie_charts
    Report_path=/home/user/ai_baat_chit/Recording_Reports
    ```

3.  **Set up Twilio phone and webhooks.** In the Twilio Console, purchase or use an existing phone number. For the **Voice & Fax** configuration of that number, set the "A CALL COMES IN" webhook to point to your FastAPI app. For example:
    ```
    https://<PUBLIC_URL>/calls
    ```
    (You will run the FastAPI server at this URL/port; using ngrok or your own domain is recommended for a publicly accessible endpoint.)

4.  **Update the TwiML template.** The TwiML response is defined in `templates/streams.xml`. This template tells Twilio to start streaming the call audio. For example, it will include a snippet like:
    ```xml
    <Response>
        <Start><Stream url="wss://<YOUR_NGROK_HOST>/ws" /></Start>
        <Say>Connecting you to the AI interviewer.</Say>
    </Response>
    ```
    This causes Twilio to send the live audio to the WebSocket endpoint `/ws` of your FastAPI server. (See Twilio's documentation on the `<Stream>` verb for details[^3].)

5.  **Run the FastAPI server.** Launch the app so it can receive calls and WebSocket streams:
    ```bash
    uvicorn fastapi_app:app --reload --port ${PORT}
    ```
    Ensure that the `PORT` matches what you set in `.env`, and that your `NGROK_URL` or domain is pointing to this port. Your app should now accept incoming Twilio webhook requests and handle the WebSocket audio stream.

## How It Works

When a caller dials your Twilio number, the following sequence occurs:

1.  **Twilio starts streaming audio.** Twilio receives the call and executes the TwiML `<Start><Stream>` instruction. This forks the raw audio of the call and streams it, in real time, over a WebSocket to your server[^3]. (In other words, Twilio opens a WebSocket connection to `wss://<YOUR_HOST>/ws` and sends the live audio bytes.)
2.  **Server (Pipecat pipeline) processes audio.** The FastAPI app's WebSocket endpoint (using Pipecat under the hood) receives the audio frames. The pipeline forwards these audio chunks to Google's Gemini Live (bidirectional) API. We effectively proxy the stream into Gemini, allowing Gemini to hear the caller in real time.
3.  **Gemini generates spoken responses.** Google's Gemini Live API listens to the incoming speech and produces a spoken reply. This is a bidirectional (two-way) stream, so Gemini can send back audio frames as it "thinks". Gemini supports interruption (it will pause to listen if the caller speaks) and returns back-and-forth natural dialogue.
4.  **Server streams response back to Twilio.** The FastAPI app takes Gemini's audio output and sends it back over the WebSocket to Twilio. Twilio then plays these audio frames immediately to the caller. This creates a seamless live conversation between the caller and Gemini.

In summary, the live loop is: **Caller ↔ Twilio (WebSocket + Pipecat) ↔ Gemini Live API**. Pipecat handles the orchestration of audio transport, and Gemini provides the AI voice. This setup allows a natural voice conversation without pre-recorded prompts.

## Reporting and Transcription

After the call ends, the system generates a report:

*   **Download the recording.** Use the `download_recordings.py` script (or Twilio's console) to retrieve the call recording file. This script uses your Twilio SID/auth to list and download recent call recordings into the `recordings/` folder.
*   **Transcribe and analyze.** Run `generate_reports.py` on the downloaded audio. This script uses Google Speech-to-Text to convert the audio into text. It then performs any desired analysis (e.g. calculating talk-time ratios, sentiment, keywords).
*   **Generate PDF report.** Using the ReportLab library, the script composes a PDF report (saved in `Recording_Reports/`) that includes the text transcript and a pie chart (from `pie_charts/`) showing conversation metrics. ReportLab is an open-source PDF generation toolkit for Python, used here to create the final report programmatically.

Each report provides HR an overview of the call content and caller behavior (for example, speaker interruptions or emotion tone). You can customize `generate_reports.py` to add more charts or analytics as needed.

## Usage Example

1.  **Start your server:**
    ```bash
    uvicorn fastapi_app:app --port 5500
    ```
2.  **Expose to internet:** If testing locally, run `ngrok http 5500` and set the `NGROK_URL` / `PUBLIC_URL` accordingly.
3.  **Place a call to your Twilio number.** Twilio will hit your `/calls` webhook, which returns the streaming TwiML. You should hear the AI responding as you talk.
4.  **Check recordings:** After hanging up, run the recording download and report generation scripts.
    ```bash
    python download_recordings.py
    python generate_reports.py
    ```

## Dependencies

*   **Python 3.8+**
*   **FastAPI** - Python web framework for serving the API and WebSocket.
*   **Pipecat** - Pipeline framework for multimodal voice AI (we use it to connect Twilio and Gemini).
*   **Twilio Python SDK** – to download call recordings via API.
*   **ReportLab** – for creating PDF reports.
*   **Google Cloud libraries** – to access Gemini Live API and Speech-to-Text (set up via `GOOGLE_API_KEY`).

Install with `pip install -r requirements.txt`. Make sure your environment variables (especially Twilio keys and Google API key) are set before running.

## References

This system leverages several external services and libraries. For more information, see: Pipecat documentation (for building streaming voice agents)[^1], Twilio Media Streams documentation (the `<Stream>` TwiML verb)[^3], and Google Gemini Live API docs (real-time voice AI)[^2]. These provide background on how the audio streaming and AI integration works.

---
[^1]: **GitHub - pipecat-ai/pipecat: Open Source framework for voice and multimodal conversational AI**  
    <https://github.com/pipecat-ai/pipecat>

[^2]: **Get started with Live API | Gemini API | Google AI for Developers**  
    <https://ai.google.dev/gemini-api/docs/live>

[^3]: **TwiML™ Voice: <Stream> | Twilio**  
    <https://www.twilio.com/docs/voice/twiml/stream>