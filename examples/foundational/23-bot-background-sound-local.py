import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.mixers.soundfile_mixer import SoundfileMixer
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame, MixerEnableFrame, MixerUpdateSettingsFrame
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

# 봇이 사용할 배경음 파일 경로 (사무실 소음)
OFFICE_SOUND_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assets", "office-ambience-24000-mono.mp3"
)

async def main():
    # 1. 배경음 믹서 설정
    # 'office'라는 이름으로 소리 파일을 등록하고 기본 재생되도록 설정합니다.
    mixer = SoundfileMixer(
        sound_files={"office": OFFICE_SOUND_FILE},
        default_sound="office",
        volume=1.0, # 배경음 볼륨 (0.0 ~ 1.0)
    )

    # 2. 로컬 트랜스포트에 믹서 연결
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_out_mixer=mixer
        )
    )

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        settings=OpenAILLMService.Settings(
            system_instruction="You are a helpful assistant. You are talking to a user in a busy office environment. Keep your responses brief.",
        ),
    )

    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice="aura-asteria-en",
    )

    context = LLMContext()
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

    async def start_bot():
        # 배경음 제어 시연
        logger.info("Background sound started at full volume.")
        await asyncio.sleep(1.0)

        logger.info("Reducing background volume to 20%...")
        await task.queue_frame(MixerUpdateSettingsFrame({"volume": 0.2}))
        await asyncio.sleep(1.0)

        logger.info("Starting conversation...")
        context.add_message({"role": "user", "content": "Please introduce yourself briefly."})
        await task.queue_frames([LLMRunFrame()])

    runner = PipelineRunner(handle_sigint=False if sys.platform == "win32" else True)

    logger.info("Background Sound Bot started...")
    await asyncio.gather(runner.run(task), start_bot())

if __name__ == "__main__":
    asyncio.run(main())
