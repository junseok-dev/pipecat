import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
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
from pipecat.turns.user_start import TranscriptionUserTurnStartStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


async def main():
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )
    )

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    # 번역 봇을 위한 TTS 설정 (일본어 목소리 사용 예시)
    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice="aura-kazuya-jp", # 일본어 목소리 (또는 원하는 언어)
    )

    # LLM 설정: 영어를 일본어로 번역하는 역할 부여
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        settings=OpenAILLMService.Settings(
            system_instruction="You are a live translation assistant. Translate English text into Japanese. Provide only the translation, no explanations.",
        ),
    )

    context = LLMContext()
    
    # 실시간 번역을 위해 사용자가 말을 마칠 때마다 즉시 번역하도록 설정
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=UserTurnStrategies(
                start=[TranscriptionUserTurnStartStrategy(enable_interruptions=False)],
            ),
            vad_analyzer=SileroVADAnalyzer(),
        ),
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

    async def start_bot():
        await asyncio.sleep(1.0)
        # 시작 메시지
        await task.queue_frames([TTSSpeakFrame("Ready for English to Japanese translation. Please speak.")])

    runner = PipelineRunner(handle_sigint=False if sys.platform == "win32" else True)

    logger.info("Live Translation Bot started...")
    await asyncio.gather(runner.run(task), start_bot())


if __name__ == "__main__":
    asyncio.run(main())
