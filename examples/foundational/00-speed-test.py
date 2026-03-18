import asyncio
import os
import sys
import time

from dotenv import load_dotenv
from loguru import logger

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
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

load_dotenv(override=True)

# 로그 설정: 상세 시간 확인을 위해 INFO 레벨 사용
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")

class PerformanceSink(FrameProcessor):
    def __init__(self):
        super().__init__()
        self._llm_start_time = 0
        self._first_token_received = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        # LLM이 답변을 시작할 때
        if frame.__class__.__name__ == "LLMFullResponseStartFrame":
            self._llm_start_time = time.time()
            self._first_token_received = False
            print("\n[DEBUG] LLM started generating...")
            
        elif isinstance(frame, TextFrame):
            if not self._first_token_received:
                elapsed = time.time() - self._llm_start_time
                print(f"\n[DEBUG] First token received in {elapsed:.2f}s")
                print("BOT: ", end="", flush=True)
                self._first_token_received = True
            print(frame.text, end="", flush=True)

        elif frame.__class__.__name__ == "LLMFullResponseEndFrame":
            print("\n")

        await self.push_frame(frame, direction)

async def main():
    # 0. 트랜스포트 설정 (출력 전용)
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=False,
            audio_out_enabled=True,
        )
    )

    # 1. 서비스 설정
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini",
        settings=OpenAILLMService.Settings(
            system_instruction="Keep answers very brief.",
        )
    )

    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice="aura-asteria-en",
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)
    perf_sink = PerformanceSink()

    # 2. 파이프라인 구성
    pipeline = Pipeline([
        user_aggregator,
        llm,
        tts,                # 음성 합성 서비스 추가
        transport.output(),  # 스피커로 출력
        perf_sink,
        assistant_aggregator
    ])

    task = PipelineTask(pipeline)
    runner = PipelineRunner(handle_sigint=True)

    # 3. 입력 루프
    async def input_loop():
        await asyncio.sleep(1.0)
        print("\n--- Speed Test Mode (Text Input + Voice Output) ---")
        print("Type something and look at the [DEBUG] logs while listening.")
        print("--------------------------------------------------\n")
        
        while True:
            user_input = await asyncio.to_thread(input, "YOU: ")
            
            if user_input.lower() in ["exit", "quit"]:
                await task.queue_frame(EndFrame())
                break
            
            logger.info(f"Sending input: '{user_input}'")
            # 프레임 전송
            await task.queue_frames([
                UserStartedSpeakingFrame(),
                TextFrame(user_input),
                UserStoppedSpeakingFrame(),
                LLMRunFrame()
            ])

    # 4. 실행
    await asyncio.gather(runner.run(task), input_loop())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
