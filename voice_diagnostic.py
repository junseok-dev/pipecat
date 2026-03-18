import asyncio
import os
import sys
import ssl
from dotenv import load_dotenv
from loguru import logger

# 🚨 최후의 전역 SSL 무력화 (2026년 날짜 대응용)
try:
    ssl._create_default_https_context = ssl._create_unverified_context
    os.environ["CURL_CA_BUNDLE"] = ""
    os.environ["SSL_CERT_FILE"] = ""
except:
    pass

from pipecat.frames.frames import EndFrame, TTSSpeakFrame, StartFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

load_dotenv(override=True)

# 디버그 로그 활성화
logger.remove()
logger.add(sys.stderr, level="DEBUG")

async def main():
    print("--- VOICE DIAGNOSTIC (Deepgram + Local Audio) ---")
    
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("❌ ERROR: DEEPGRAM_API_KEY is missing in .env")
        return

    print(f"Using Key: {api_key[:10]}...")

    # 1. 오디오 장치 테스트
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        print(f"✅ PyAudio initialized. Devices: {p.get_device_count()}")
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            print(f"   [{i}] {dev['name']} (Out: {dev['maxOutputChannels']})")
        p.terminate()
    except Exception as e:
        print(f"❌ PyAudio Error: {e}")

    # 2. Pipecat 파이프라인 테스트
    transport = LocalAudioTransport(LocalAudioTransportParams(audio_out_enabled=True))
    
    tts = DeepgramTTSService(
        api_key=api_key,
        voice="aura-asteria-en",
    )

    pipeline = Pipeline([tts, transport.output()])
    task = PipelineTask(pipeline)
    runner = PipelineRunner(handle_sigint=True)

    async def say_test():
        # StartFrame이 파이프라인을 통과할 때까지 기다림
        await asyncio.sleep(2)
        print(">>> Requesting Speech: 'Hello! If you hear this, voice is working!'")
        # 🚨 TextFrame 대신 TTSSpeakFrame 사용
        await task.queue_frames([TTSSpeakFrame("Hello! If you hear this, voice is working!"), EndFrame()])

    print("🚀 Starting Pipeline... (Wait for sound)")
    await asyncio.gather(runner.run(task), say_test())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"System Error: {e}")
