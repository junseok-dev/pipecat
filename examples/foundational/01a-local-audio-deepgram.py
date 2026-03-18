import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger

from pipecat.frames.frames import EndFrame, TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


async def main():
    # 로컬 스피커 출력을 위한 트랜스포트 설정
    transport = LocalAudioTransport(LocalAudioTransportParams(audio_out_enabled=True))

    # 사용자가 보유한 Deepgram API 키를 사용하는 TTS 서비스
    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice="aura-asteria-en",
    )

    pipeline = Pipeline([tts, transport.output()])

    task = PipelineTask(pipeline)

    async def say_something():
        await asyncio.sleep(1)
        # 봇이 할 말을 큐에 추가
        await task.queue_frames([TTSSpeakFrame("Hello there, how is it going!"), EndFrame()])

    runner = PipelineRunner(handle_sigint=False if sys.platform == "win32" else True)

    await asyncio.gather(runner.run(task), say_something())


if __name__ == "__main__":
    asyncio.run(main())
