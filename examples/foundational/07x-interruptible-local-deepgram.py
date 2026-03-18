import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
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
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


async def main():
    # 1. 마이크 입력 및 스피커 출력을 위한 로컬 트랜스포트 설정
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )
    )

    # 2. STT (음성 인식) 설정 - Deepgram 사용
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    # 3. LLM (대화 지능) 설정 - OpenAI 사용
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        settings=OpenAILLMService.Settings(
            system_instruction="You are a helpful assistant in a voice conversation. Your responses will be spoken aloud, so avoid emojis, bullet points, or other formatting that can't be spoken. Respond to what the user said in a creative, helpful, and brief way.",
        ),
    )

    # 4. TTS (음성 합성) 설정 - Deepgram 사용
    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice="aura-asteria-en",
    )

    # 5. 대화 문맥 및 VAD (음성 감지) 설정
    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    # 6. 파이프라인 구성
    pipeline = Pipeline(
        [
            transport.input(),      # 마이크 입력
            stt,                    # STT (음성 -> 텍스트)
            user_aggregator,        # 사용자 발화 수집
            llm,                    # LLM (텍스트 답변 생성)
            tts,                    # TTS (텍스트 -> 음성)
            transport.output(),     # 스피커 출력
            assistant_aggregator,   # 어시스턴트 발화 수집 (문맥 유지용)
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    # 7. 시작 메시지 자동 실행 (봇이 먼저 인사하게 함)
    context.add_message({"role": "user", "content": "Please introduce yourself to the user briefly."})
    await task.queue_frames([LLMRunFrame()])

    runner = PipelineRunner(handle_sigint=False if sys.platform == "win32" else True)

    logger.info("Starting real-time conversation bot...")
    await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
