import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger
from PIL import Image

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
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )
    )

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        settings=OpenAILLMService.Settings(
            system_instruction="You are a helpful assistant. You can describe images in a brief and conversational way.",
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

    # --- 이미지 처리 로직 ---

    # 1. 자산 경로 설정 (기존에 존재하는 고양이 이미지 사용)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, "assets", "cat.jpg")

    if not os.path.exists(image_path):
        logger.error(f"Image not found at {image_path}")
        return

    # 2. 이미지 열기 및 문맥(Context)에 추가
    logger.info(f"Opening image: {image_path}")
    image = Image.open(image_path)
    message = await LLMContext.create_image_message(
        image=image.tobytes(),
        format="RGB",
        size=image.size,
        text="Please describe this image briefly.",
    )
    context.add_message(message)
    logger.info("Image message added to context.")

    # 3. 봇이 이미지를 보고 설명을 시작하게 함
    logger.info("Queuing LLMRunFrame...")
    await task.queue_frames([LLMRunFrame()])
    logger.info("LLMRunFrame queued.")

    runner = PipelineRunner(handle_sigint=False if sys.platform == "win32" else True)

    logger.info("Vision Bot started...")
    await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
