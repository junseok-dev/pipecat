import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger

from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.deepgram.stt import DeepgramSTTService, Language
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# --- 전사 로그를 터미널에 출력하는 프로세서 ---
class TranscriptionLogger(FrameProcessor):
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            # 사용자가 말한 내용을 터미널에 화려하게(?) 출력
            print(f"\n[USER] {frame.text}\n")

        await self.push_frame(frame, direction)


async def main():
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
        )
    )

    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        settings=DeepgramSTTService.Settings(
            language=Language.EN,
        ),
    )

    tl = TranscriptionLogger()

    # 파이프라인: 입력 -> STT -> 로그 출력
    pipeline = Pipeline([transport.input(), stt, tl])

    task = PipelineTask(pipeline)

    runner = PipelineRunner(handle_sigint=False if sys.platform == "win32" else True)

    logger.info("Transcription Bot started. Speak into your microphone...")
    await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
