import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame, TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


# --- 봇이 호출할 가상 함수 정의 ---

async def fetch_weather(params: FunctionCallParams):
    location = params.arguments.get("location", "Seoul")
    logger.info(f"Fetching weather for {location}...")
    # 실제로는 API를 호출하겠지만, 여기서는 가상 데이터를 반환합니다.
    await params.result_callback({"conditions": "sunny", "temperature": "22°C", "location": location})


async def get_current_time(params: FunctionCallParams):
    from datetime import datetime
    now = datetime.now().strftime("%H:%M")
    logger.info(f"Getting current time: {now}")
    await params.result_callback({"time": now})


async def main():
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )
    )

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        settings=OpenAILLMService.Settings(
            system_instruction="You are a helpful voice assistant. You can check the weather and the current time using tools. Keep your responses brief and conversational. When a user asks about the weather or time, tell them you're checking it before the tool results come in.",
        ),
    )

    # 1. 함수 등록 (LLM이 어떤 함수를 쓸 수 있는지 등록)
    llm.register_function("get_weather", fetch_weather)
    llm.register_function("get_time", get_current_time)

    # 2. 함수 호출이 시작될 때 봇이 취할 행동 (예: "잠시만요, 확인해 드릴게요")
    @llm.event_handler("on_function_calls_started")
    async def on_function_calls_started(service, function_calls):
        await tts.queue_frame(TTSSpeakFrame("Sure, let me check that for you."))

    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice="aura-asteria-en",
    )

    # 3. 도구(Tools) 스키마 정의
    weather_tool = FunctionSchema(
        name="get_weather",
        description="Get the current weather for a specific location",
        properties={
            "location": {
                "type": "string",
                "description": "The city name, e.g. Seoul, London, New York",
            }
        },
        required=["location"],
    )
    time_tool = FunctionSchema(
        name="get_time",
        description="Get the current local time",
        properties={},
        required=[],
    )
    tools = ToolsSchema(standard_tools=[weather_tool, time_tool])

    context = LLMContext(tools=tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    context.add_message({"role": "user", "content": "Hello! Introduce yourself briefly."})
    await task.queue_frames([LLMRunFrame()])

    runner = PipelineRunner(handle_sigint=False if sys.platform == "win32" else True)

    logger.info("Function Calling Bot started...")
    await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
