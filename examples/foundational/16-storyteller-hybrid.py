import asyncio
import os
import sys
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
    URLImageRawFrame
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
logger.add(sys.stderr, level="ERROR")

bot_finished_event = asyncio.Event()

# --- 이미지 프롬프트를 감지하고 필터링하는 프로세서 ---
class ImagePromptProcessor(FrameProcessor):
    def __init__(self, image_gen_service):
        super().__init__()
        self._image_gen_service = image_gen_service
        self._full_response = ""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        if isinstance(frame, TextFrame):
            # "IMAGE_PROMPT:" 이전의 가독성 있는 텍스트만 통과시킴
            if "IMAGE_PROMPT:" in frame.text:
                # 프롬프트 시작 부분을 포함한 프레임이면 자름
                clean_text = frame.text.split("IMAGE_PROMPT:")[0]
                self._full_response += frame.text
                if clean_text.strip():
                    await self.push_frame(TextFrame(clean_text), direction)
                return
            
            # 이미 프롬프트 구간에 있으면 차단
            if "IMAGE_PROMPT:" in self._full_response:
                self._full_response += frame.text
                return

            self._full_response += frame.text
            await self.push_frame(frame, direction)
        
        elif frame.__class__.__name__ == "LLMFullResponseEndFrame":
            # 답변이 끝났을 때 이미지 프롬프트가 있다면 추출하여 이미지 생성 서비스로 전송
            if "IMAGE_PROMPT:" in self._full_response:
                try:
                    prompt = self._full_response.split("IMAGE_PROMPT:")[1].strip()
                    if prompt:
                        print(f"\n[SYSTEM] Creating art for: {prompt}...")
                        # 별도의 태스크로 이미지 생성 실행
                        asyncio.create_task(self._trigger_image_gen(prompt))
                except Exception as e:
                    print(f"\n[ERROR] Failed to extract prompt: {e}")
            
            self._full_response = ""
            await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)

    async def _trigger_image_gen(self, prompt):
        try:
            async for frame in self._image_gen_service.run_image_gen(prompt):
                await self.push_frame(frame)
        except Exception as e:
            print(f"\n[ERROR] Image generation failed: {e}")

# --- 결과 출력 싱크 ---
class StorytellerSink(FrameProcessor):
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
            
        elif isinstance(frame, URLImageRawFrame):
            import io
            print(f"\n[IMAGE] Masterpiece generated! Opening...")
            image = Image.open(io.BytesIO(frame.image))
            image.show()

        elif frame.__class__.__name__ == "LLMFullResponseStartFrame":
            self._is_thinking = True
            bot_finished_event.clear()
            print("AI is imagining and writing...", end="", flush=True)

        elif frame.__class__.__name__ == "LLMFullResponseEndFrame":
            print("\n")
            bot_finished_event.set()

        await self.push_frame(frame, direction)

async def main():
    async with aiohttp.ClientSession() as session:
        transport = LocalAudioTransport(LocalAudioTransportParams(audio_in_enabled=False, audio_out_enabled=True))

        llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",
            settings=OpenAILLMService.Settings(
                system_instruction="You are a professional storyteller. When a user gives a theme, write a 2-3 sentence evocative short story. After the story, END with exactly one line: 'IMAGE_PROMPT: ' followed by a descriptive visual prompt (no scary or prohibited words).",
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
        
        image_processor = ImagePromptProcessor(image_gen)
        sink = StorytellerSink()

        # 파이프라인 구성
        pipeline = Pipeline([
            user_aggregator,
            llm,
            tts,
            image_processor, 
            transport.output(),
            sink,
            assistant_aggregator
        ])

        task = PipelineTask(pipeline)
        runner = PipelineRunner(handle_sigint=True)

        async def input_loop():
            await asyncio.sleep(1.0)
            print("\n--- AI Multi-modal Storyteller (Fixed) ---")
            print("Type a theme like 'Cyberpunk library' or 'A magical forest'")
            bot_finished_event.set()
            
            while True:
                await bot_finished_event.wait()
                user_input = await asyncio.to_thread(input, "THEME: ")
                if not user_input.strip(): continue
                if user_input.lower() in ["exit", "quit"]:
                    await task.queue_frame(EndFrame()); break
                
                bot_finished_event.clear()
                # 컨텍스트 초기화 (중복 방지)
                context.messages = context.messages[:1] 
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
