import asyncio
import os
import sys

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

# 로그 설정: 대화 흐름에 방해되지 않도록 에러만 출력
logger.remove()
logger.add(sys.stderr, level="ERROR")

# 대화 종료 신호를 받기 위한 이벤트
bot_finished_event = asyncio.Event()

# --- 봇의 답변을 터미널에 출력하고 종료 신호를 처리하는 싱크 ---
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
            bot_finished_event.clear() # 답변 시작하면 이벤트 클리어
            print("BOT is thinking...", end="", flush=True)

        elif frame.__class__.__name__ == "LLMFullResponseEndFrame":
            print("\n")
            bot_finished_event.set() # 답변이 완전히 끝나면 신호 보냄

        await self.push_frame(frame, direction)

async def main():
    # 1. 트랜스포트 및 서비스 설정
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=False,
            audio_out_enabled=True,
        )
    )

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini",
        settings=OpenAILLMService.Settings(
            system_instruction="You are a helpful assistant. Keep your answers brief and friendly.",
        )
    )

    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice="aura-asteria-en",
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)
    output_sink = TerminalOutputSink()

    # 2. 파이프라인 구성
    pipeline = Pipeline([
        user_aggregator,
        llm,
        tts,
        transport.output(),
        output_sink,
        assistant_aggregator
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        )
    )
    
    runner = PipelineRunner(handle_sigint=True)

    # 3. 강화된 키보드 입력 루프
    async def input_loop():
        await asyncio.sleep(1.5) # 초기화 대기
        
        print("\n--- Hybrid Bot (Type input / Listen output) ---")
        print("Type 'exit' to quit. Talk to me!")
        print("----------------------------------------------\n")
        
        # 초기 인사 (선택 사항)
        print("BOT: Hello! I'm ready. What's your question?")
        bot_finished_event.set() # 초기 상태는 입력 가능
        
        while True:
            # 봇의 답변이 끝날 때까지 대기 (이미 끝났으면 즉시 통과)
            await bot_finished_event.wait()
            
            # 사용자 입력 받기
            user_input = await asyncio.to_thread(input, "YOU: ")
            
            if user_input.lower() in ["exit", "quit"]:
                await task.queue_frame(EndFrame())
                break
            
            if not user_input.strip():
                continue

            # 다음 입력을 위해 이벤트 클리어
            bot_finished_event.clear()
            
            # 프레임 전송 및 실행
            await task.queue_frames([
                UserStartedSpeakingFrame(),
                TextFrame(user_input),
                UserStoppedSpeakingFrame(),
                LLMRunFrame()
            ])

    # 4. 동시 실행
    try:
        await asyncio.gather(runner.run(task), input_loop())
    except Exception as e:
        print(f"\nError occurred: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
