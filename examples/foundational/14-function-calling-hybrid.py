import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.frames.frames import (
    Frame, 
    TextFrame, 
    UserStartedSpeakingFrame, 
    UserStoppedSpeakingFrame,
    LLMRunFrame,
    EndFrame,
    TTSSpeakFrame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

load_dotenv(override=True)

# 로그 설정
logger.remove()
logger.add(sys.stderr, level="ERROR")

bot_finished_event = asyncio.Event()

# --- 봇의 답변을 터미널에 출력하는 싱크 ---
class TerminalOutputSink(FrameProcessor):
    def __init__(self):
        super().__init__()
        self._is_thinking = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, TextFrame):
            if self._is_thinking:
                print("\r" + " " * 30 + "\r", end="", flush=True)
                print("BOT: ", end="", flush=True)
                self._is_thinking = False
            print(frame.text, end="", flush=True)
            
        elif frame.__class__.__name__ == "LLMFullResponseStartFrame":
            self._is_thinking = True
            bot_finished_event.clear()
            print("BOT is thinking...", end="", flush=True)

        elif frame.__class__.__name__ == "LLMFullResponseEndFrame":
            print("\n")
            bot_finished_event.set()

        await self.push_frame(frame, direction)

# --- 가상 함수 정의 ---
async def fetch_weather(params: FunctionCallParams):
    location = params.arguments.get("location", "Seoul")
    await params.result_callback({"conditions": "sunny", "temperature": "22°C", "location": location})

async def get_current_time(params: FunctionCallParams):
    from datetime import datetime
    now = datetime.now().strftime("%H:%M")
    await params.result_callback({"time": now})

async def main():
    transport = LocalAudioTransport(LocalAudioTransportParams(audio_in_enabled=False, audio_out_enabled=True))
    
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        settings=OpenAILLMService.Settings(
            system_instruction="You are a helpful assistant. Use tools to check weather or time. Keep it brief.",
        )
    )
    llm.register_function("get_weather", fetch_weather)
    llm.register_function("get_time", get_current_time)

    # 함수 호출 시 봇이 말할 멘트
    @llm.event_handler("on_function_calls_started")
    async def on_function_calls_started(service, function_calls):
        await task.queue_frame(TTSSpeakFrame("Checking that for you..."))

    tts = DeepgramTTSService(api_key=os.getenv("DEEPGRAM_API_KEY"), voice="aura-asteria-en")

    tools = ToolsSchema(standard_tools=[
        FunctionSchema(name="get_weather", description="Get weather", properties={"location": {"type": "string"}}, required=["location"]),
        FunctionSchema(name="get_time", description="Get current time", properties={}, required=[])
    ])

    context = LLMContext(tools=tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)
    output_sink = TerminalOutputSink()

    pipeline = Pipeline([user_aggregator, llm, tts, transport.output(), output_sink, assistant_aggregator])
    task = PipelineTask(pipeline)
    runner = PipelineRunner(handle_sigint=True)

    async def input_loop():
        await asyncio.sleep(1.5)
        print("\n--- Hybrid Function Calling (Type 'weather in Seoul' or 'what time is it') ---")
        bot_finished_event.set()
        
        while True:
            await bot_finished_event.wait()
            user_input = await asyncio.to_thread(input, "YOU: ")
            if user_input.lower() in ["exit", "quit"]:
                await task.queue_frame(EndFrame()); break
            bot_finished_event.clear()
            await task.queue_frames([UserStartedSpeakingFrame(), TextFrame(user_input), UserStoppedSpeakingFrame(), LLMRunFrame()])

    await asyncio.gather(runner.run(task), input_loop())

if __name__ == "__main__":
    asyncio.run(main())
