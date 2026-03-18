import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger
from PIL import Image

from pipecat.frames.frames import (
    Frame, 
    TextFrame, 
    UserStartedSpeakingFrame, 
    UserStoppedSpeakingFrame,
    LLMRunFrame,
    EndFrame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

load_dotenv(override=True)

logger.remove()
logger.add(sys.stderr, level="ERROR")

bot_finished_event = asyncio.Event()

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

async def main():
    transport = LocalAudioTransport(LocalAudioTransportParams(audio_in_enabled=False, audio_out_enabled=True))
    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")
    tts = DeepgramTTSService(api_key=os.getenv("DEEPGRAM_API_KEY"), voice="aura-asteria-en")

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)
    output_sink = TerminalOutputSink()

    pipeline = Pipeline([user_aggregator, llm, tts, transport.output(), output_sink, assistant_aggregator])
    task = PipelineTask(pipeline)
    runner = PipelineRunner(handle_sigint=True)

    # 이미지 추가
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, "assets", "cat.jpg")
    image = Image.open(image_path)
    message = await LLMContext.create_image_message(image=image.tobytes(), format="RGB", size=image.size, text="Describe this image.")
    context.add_message(message)

    async def input_loop():
        await asyncio.sleep(1.5)
        print("\n--- Hybrid Vision (Image loaded! Ask about the cat) ---")
        # 첫 설명 시작
        bot_finished_event.clear()
        await task.queue_frames([LLMRunFrame()])
        
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
