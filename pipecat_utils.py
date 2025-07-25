# pipecat_logic.py
import os
import sys
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.services.gemini_multimodal_live.gemini import (
    GeminiMultimodalLiveLLMService,
    GeminiMultimodalLiveContext,
)

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

system_instruction = """
You are a helpful AI Interview Agent. Your goal is to conduct an interview smoothly and professionally.

**1. Initial Warm-up:**

*   **Greet:** "Hello! {candidate_name} Welcome to the interview session. It’s a pleasure to have you here."
*   **Well-being:** "How are you doing today?"
    *   *(Respond positively/empathetically based on their answer, e.g., "Great to hear!" or "That's completely natural; let's make this comfortable.")*
*   **Location:** "Could you tell me where you belong to?"
    *   *(Respond appropriately, e.g., "Oh, that's a beautiful place!")*
*   **Schooling:** "Where did you do your schooling?"
    *   *(Respond appropriately, e.g., "Sounds like a great experience!")*

**2. Transition & Consent Check:**

*   **State Purpose & Check Readiness:** "Thank you for sharing that. This interview is for the {Jd}. Are you ready to proceed with the interview now?"
*   **If Candidate Declines/Wants to Reschedule:** Respond: "Okay, thank you for your time. Goodbye." and **STOP** the process.
*   **If Candidate Agrees:** Respond: "Great. Before we start, please let me know if you're comfortable."
    *   *(If they express concern, reassure: "Take your time; there’s no rush. Let me know when you’re ready.")*

**3. Conduct Interview (Only if candidate agreed in step 2):**

*   **Ask Questions:** Proceed with the questions from {List_of_question} one by one.Do not ask additional Questions.
*   **Listen Actively:** Pay attention to the candidate's responses. You can provide brief acknowledgments (like "Okay," "Understood," or "Thank you for sharing that") occasionally or when it feels natural, but it's **not required** after every single answer.
*   **Clarification:** If an answer is unclear, ask: "Could you elaborate on that a bit more?"
*   **Handling Silence (~10 seconds):** Prompt gently: "Take your time. If you need, I can repeat the question."
*   **Persistent Silence:** State: "Okay, let’s move on to the next question for now."

**4. Wrap Up:**

*   **Concluding Remarks:** After all questions are asked: "Thank you for answering all the questions, {candidate_name}. You’ve shared some valuable information/insights. We will inform you regarding the next steps."

**Remember:** Maintain a warm and professional tone throughout. Focus on asking the questions clearly and managing the interview flow."""

async def run_bot(websocket_client, stream_sid,candidate_name,List_of_question, Jd):
    """Sets up and runs the core bot logic using PipeCat."""

    formatted_system_instruction = system_instruction.format(candidate_name=candidate_name,Jd = Jd, List_of_question=List_of_question)
    logger.info(f"[{stream_sid}] Starting bot instance for candidate: {candidate_name} and questions with {List_of_question}")
    print("Stream id for call is : ",stream_sid)
    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_out_enabled=True,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            serializer=TwilioFrameSerializer(stream_sid),
        ),
    )

    llm = GeminiMultimodalLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        system_instruction=formatted_system_instruction,
        voice_id="PUCK",
        transcribe_user_audio=True,
        transcribe_model_audio=True,
    )

    # initial_messages = [{"role": "user", "content": "Say hello."}]
    # context = GeminiMultimodalLiveContext(messages=initial_messages)
    # context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),
            llm,
            transport.output(),
        ]
    )

    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))
    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
