import asyncio
import os
import sys
import time
import aiohttp
from dotenv import load_dotenv
from loguru import logger
from PIL import Image

from pipecat.frames.frames import (
    Frame, 
    TextFrame, 
    UserStartedSpeakingFrame, 
    UserStoppedSpeakingFrame,
    LLMRunFrame,
    EndFrame,
    URLImageRawFrame,
    StartFrame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.openai.image import OpenAIImageGenService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

load_dotenv(override=True)

# 로그 설정
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss.SSS}</green> | <level>{message}</level>", level="INFO")

bot_finished_event = asyncio.Event()

# --- 이미지 프롬프트를 감지하고 필터링하는 프로세서 ---
class TurboImageTrigger(FrameProcessor):
    def __init__(self, image_gen_service):
        super().__init__()
        self._image_gen_service = image_gen_service
        self._full_text = ""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # CRITICAL: 반드시 super().process_frame을 호출해야 StartFrame 오류가 나지 않음
        await super().process_frame(frame, direction)
        
        if isinstance(frame, TextFrame):
            self._full_text += frame.text
            
            # "IMAGE_PROMPT:" 발견된 이후는 다음 단계(TTS/Sink)로 보내지 않음
            if "IMAGE_PROMPT:" in self._full_text:
                if "IMAGE_PROMPT:" in frame.text:
                    clean_text = frame.text.split("IMAGE_PROMPT:")[0]
                    if clean_text.strip():
                        await self.push_frame(TextFrame(clean_text), direction)
                return
            
            await self.push_frame(frame, direction)
            
        elif frame.__class__.__name__ == "LLMFullResponseEndFrame":
            if "IMAGE_PROMPT:" in self._full_text:
                try:
                    prompt = self._full_text.split("IMAGE_PROMPT:")[1].strip()
                    if prompt:
                        print(f"\n[SYSTEM] Creating art for: {prompt[:50]}...")
                        asyncio.create_task(self._trigger_image_gen(prompt))
                except Exception as e:
                    print(f"\n[ERROR] Prompt extraction failed: {e}")
            
            self._full_text = ""
            await self.push_frame(frame, direction)
        
        # StartFrame이나 다른 제어 프레임들은 super()에서 이미 처리되어 전달됨
        # (이미 process_frame 상단에서 super()를 불렀으므로 TextFrame/EndFrame이 아닌 경우만 중복 방지를 위해 조심)
        elif not isinstance(frame, (TextFrame)):
            # 이미 위에서 처리되지 않은 프레임들(StartFrame 등)은 Pass-through
            # 사실 super().process_frame이 내부적으로 push_frame을 할 수도 있으므로 구조 주의
            pass

    async def _trigger_image_gen(self, prompt):
        try:
            async for frame in self._image_gen_service.run_image_gen(prompt):
                await self.push_frame(frame)
        except Exception as e:
            print(f"\n[ERROR] Image generation failed: {e}")

# --- 결과 출력 및 이미지 표시 싱크 ---
class TurboStorySink(FrameProcessor):
    def __init__(self):
        super().__init__()
        self._input_time = 0
        self._first_text_time = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, TextFrame):
            if not self._first_text_time:
                self._first_text_time = time.time()
                elapsed = self._first_text_time - self._input_time
                print(f"\n[TIME] TTFT: {elapsed:.2f}s")
                print("BOT: ", end="", flush=True)
            print(frame.text, end="", flush=True)

        elif isinstance(frame, URLImageRawFrame):
            import io
            elapsed = time.time() - self._input_time
            print(f"\n[TIME] Image Ready in {elapsed:.2f}s! Opening...")
            image = Image.open(io.BytesIO(frame.image))
            image.show()

        elif frame.__class__.__name__ == "LLMFullResponseStartFrame":
            bot_finished_event.clear()
            print("AI is imagining and writing...", end="", flush=True)

        elif frame.__class__.__name__ == "LLMFullResponseEndFrame":
            print("\n")
            bot_finished_event.set()

async def main():
    async with aiohttp.ClientSession() as session:
        transport = LocalAudioTransport(LocalAudioTransportParams(audio_in_enabled=False, audio_out_enabled=True))

        llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",
            settings=OpenAILLMService.Settings(
                system_instruction="You are a 2-sentence storyteller. Write a very brief story. END with ' IMAGE_PROMPT: ' + a visual description.",
            )
        )

        image_gen = OpenAIImageGenService(
            api_key=os.getenv("OPENAI_API_KEY"),
            aiohttp_session=session,
            model="dall-e-3",
        )

        tts = DeepgramTTSService(api_key=os.getenv("DEEPGRAM_API_KEY"), voice="aura-asteria-en")

        context = LLMContext()
        user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)
        
        trigger = TurboImageTrigger(image_gen)
        sink = TurboStorySink()

        pipeline = Pipeline([
            user_aggregator,
            llm,
            trigger,
            tts,
            transport.output(),
            sink,
            assistant_aggregator
        ])

        task = PipelineTask(pipeline)
        runner = PipelineRunner(handle_sigint=True)

        async def input_loop():
            # 파이프라인 신호가 안정될 때까지 충분히 대기
            await asyncio.sleep(2.0)
            print("\n--- TURBO Storyteller (V4: Internal Errors Fixed) ---")
            print("Theme: 'Cyberpunk ramen shop', 'Cat on Jupiter', etc.")
            bot_finished_event.set()
            
            while True:
                await bot_finished_event.wait()
                user_input = await asyncio.to_thread(input, "\nTHEME: ")
                if not user_input.strip(): continue
                if user_input.lower() in ["exit", "quit"]:
                    await task.queue_frame(EndFrame()); break
                
                sink._input_time = time.time()
                bot_finished_event.clear()
                
                await task.queue_frames([
                    UserStartedSpeakingFrame(),
                    TextFrame(user_input),
                    UserStoppedSpeakingFrame(),
                    LLMRunFrame()
                ])

        await asyncio.gather(runner.run(task), input_loop())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
