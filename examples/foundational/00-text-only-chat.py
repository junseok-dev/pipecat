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
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.openai.llm import OpenAILLMService

load_dotenv(override=True)

# 로그 설정: 에러만 출력
logger.remove()
logger.add(sys.stderr, level="ERROR")

# --- 봇의 답변을 터미널에 출력하는 싱크 ---
class TerminalOutputSink(FrameProcessor):
    def __init__(self):
        super().__init__()
        self._is_thinking = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        # 봇이 텍스트(답변)를 보내기 시작하면
        if isinstance(frame, TextFrame):
            if self._is_thinking:
                # "Thinking..." 메시지를 지우고 "BOT: " 헤더 출력
                print("\r" + " " * 30 + "\r", end="", flush=True)
                print("BOT: ", end="", flush=True)
                self._is_thinking = False
            print(frame.text, end="", flush=True)
            
        # LLM이 답변을 생성하기 시작할 때 (Pipecat 내부 프레임 사용)
        elif frame.__class__.__name__ == "LLMFullResponseStartFrame":
            self._is_thinking = True
            print("BOT is thinking...", end="", flush=True)

        # LLM이 답변을 모두 마쳤을 때
        elif frame.__class__.__name__ == "LLMFullResponseEndFrame":
            print("\n")

        await self.push_frame(frame, direction)

async def main():
    # 1. 서비스 및 컨텍스트 설정
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini",
        settings=OpenAILLMService.Settings(
            system_instruction="You are a helpful assistant. Keep your answers brief and friendly.",
        )
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)
    output_sink = TerminalOutputSink()

    # 2. 파이프라인 구성
    pipeline = Pipeline([
        user_aggregator,
        llm,
        output_sink,
        assistant_aggregator
    ])

    task = PipelineTask(pipeline)
    runner = PipelineRunner(handle_sigint=True)

    # 3. 사용자 입력 루프
    async def input_loop():
        await asyncio.sleep(1) # 파이프라인 시작 대기
        
        print("\n--- Text-only Pipecat Bot ---")
        print("Type your message and press Enter ('exit' to quit)")
        print("-----------------------------\n")
        
        while True:
            # 터미널 입력 받기
            user_input = await asyncio.to_thread(input, "YOU: ")
            
            if user_input.lower() in ["exit", "quit"]:
                await task.queue_frame(EndFrame())
                break
            
            # 봇에게 텍스트와 실행 명령 전송
            await task.queue_frames([
                UserStartedSpeakingFrame(), # 발화 시작 알림 (VAD 대용)
                TextFrame(user_input),      # 실제 입력된 텍스트
                UserStoppedSpeakingFrame(), # 발화 종료 알림
                LLMRunFrame()               # 답변 생성 즉시 시작!
            ])

    # 4. 실행
    # 파이프라인과 입력 루프를 함께 구동
    await asyncio.gather(runner.run(task), input_loop())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
