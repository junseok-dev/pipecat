import asyncio
import os
import sys
import httpx
import ssl
import traceback
import subprocess
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from loguru import logger

# 🚨 최후의 전역 SSL 무력화 (OpenAI 인증서 이슈 대응)
try:
    ssl._create_default_https_context = ssl._create_unverified_context
    os.environ["CURL_CA_BUNDLE"] = ""
    os.environ["SSL_CERT_FILE"] = ""
except:
    pass

from pipecat.frames.frames import (
    Frame, 
    StartFrame,
    TTSSpeakFrame,
    ImageRawFrame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.openai.tts import OpenAITTSService

# 🚨 Daily SDK Import 검증 (V44)
try:
    import daily
    # AudioData가 실제로 있는지 확인
    from pipecat.transports.services.daily import DailyTransport, DailyTransportParams
    DAILY_AVAILABLE = True
    print("✅ Daily SDK successfully imported.")
except ImportError as e:
    print(f"🚩 Daily SDK not found or shadowing persists: {e}")
    DAILY_AVAILABLE = False
except Exception as e:
    print(f"🚩 General Daily Import error: {e}")
    DAILY_AVAILABLE = False

load_dotenv(override=True)
logger.remove()

# 상태 제어
bot_ready_event = asyncio.Event()

class RecoveryEngineV44(FrameProcessor):
    def __init__(self, openai_key):
        super().__init__()
        self._openai_key = openai_key.strip()
        self._http_client = httpx.AsyncClient(verify=False, timeout=60.0)

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        if isinstance(frame, StartFrame):
            await super().process_frame(frame, direction)
            bot_ready_event.set()
        else:
            await super().process_frame(frame, direction)

    async def dual_voice_v44(self, text, filename, task):
        print(f"[VOICE] 🎙️ Processing Voice for: {text[:20]}...")
        try:
            res = await self._http_client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {self._openai_key}"},
                json={"model": "tts-1", "input": text, "voice": "alloy"}
            )
            if res.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(res.content)
                os.startfile(os.path.abspath(filename))
                if DAILY_AVAILABLE:
                    await task.queue_frame(TTSSpeakFrame(text))
            else:
                print(f"⚠️ TTS HTTP Error: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"⚠️ Voice step failed: {e}")

    async def run_v44(self, theme, task):
        print(f"\n[PHASE 1] 📖 Generating Story...")
        try:
            # 1. 시나리오 생성
            res = await self._http_client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._openai_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "system", "content": "2-sentence storyteller. End with 'IMG: ' and 3 words."},
                                 {"role": "user", "content": theme}]
                }
            )
            
            if res.status_code != 200:
                print(f"❌ OpenAI LLM Error: {res.status_code} - {res.text}")
                return

            content = res.json()["choices"][0]["message"]["content"]
            parts = content.split("IMG:")
            story_text = parts[0].strip()
            img_key = parts[1].strip() if len(parts) > 1 else theme
            
            print(f"🤖 BOT STORY: {story_text}")
            await self.dual_voice_v44(story_text, "story_voice.mp3", task)

            # 2. 이미지 생성
            print(f"\n[PHASE 2] 🎨 Generating DALL-E Image...")
            img_res = await self._http_client.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {self._openai_key}"},
                json={"model": "dall-e-3", "prompt": img_key, "n": 1, "size": "1024x1024"}
            )
            
            if img_res.status_code != 200:
                print(f"⚠️ Image generation error: {img_res.status_code} - {img_res.text}")
            else:
                img_url = img_res.json()["data"][0]["url"]
                print(f"✅ Image URL received. Downloading...")
                img_data_res = await self._http_client.get(img_url)
                if img_data_res.status_code == 200:
                    with open("story_image.png", "wb") as f:
                        f.write(img_data_res.content)
                    print(f"🖼️ Saved: {os.path.abspath('story_image.png')}")
                    
                    if DAILY_AVAILABLE:
                        print("🖼️ Pushing Image to Daily...")
                        img = Image.open(BytesIO(img_data_res.content)).convert("RGB")
                        await task.queue_frame(ImageRawFrame(image=img.tobytes(), size=img.size, format="RGB"))
                else:
                    print(f"⚠️ Image download error: {img_data_res.status_code}")

            # 3. 해설
            print(f"\n[PHASE 3] 🔍 Creating Narration...")
            n_res = await self._http_client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._openai_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "system", "content": "1 cool sentence image description."},
                                 {"role": "user", "content": f"Describe: {img_key}"}]
                }
            )
            if n_res.status_code == 200:
                narration = n_res.json()["choices"][0]["message"]["content"]
                print(f"🤖 NARRATION: {narration}")
                await self.dual_voice_v44(narration, "narration_voice.mp3", task)
                
        except Exception as e:
            print(f"❌ V44 CRITICAL ENGINE ERROR:")
            traceback.print_exc()

async def main():
    openai_key = os.getenv("OPENAI_API_KEY")
    daily_url = os.getenv("DAILY_ROOM_URL", "https://practice2.daily.co/practice2")

    pipeline_components = []
    engine = RecoveryEngineV44(openai_key)
    pipeline_components.append(engine)

    # 🎙️ TTS 서비스
    tts = OpenAITTSService(api_key=openai_key, voice="alloy")
    pipeline_components.append(tts)

    # 🌐 Daily 연동
    if DAILY_AVAILABLE:
        try:
            transport = DailyTransport(
                room_url=daily_url,
                token=None,
                bot_name="StoryBotV44",
                params=DailyTransportParams(
                    audio_out_enabled=True,
                    video_out_enabled=True,
                    camera_out_enabled=True,
                    camera_out_width=1024,
                    camera_out_height=1024
                )
            )
            pipeline_components.append(transport.output())
        except Exception as daily_err:
            print(f"⚠️ Daily hand-shake error: {daily_err}. Running local mode.")
    else:
        pipeline_components.append(FrameProcessor())

    pipeline = Pipeline(pipeline_components)
    task = PipelineTask(pipeline)
    runner = PipelineRunner(handle_sigint=True)

    async def input_loop():
        try:
            await asyncio.wait_for(bot_ready_event.wait(), timeout=5.0)
        except:
            pass

        print("\n" + "*"*50)
        print("🎭 STORYTELLER V44: STABLE MULTIMODAL ENGINE")
        print("*"*50)
        while True:
            theme = await asyncio.to_thread(input, "\n[THEME] : ")
            if theme.lower() in ["exit", "q"]: break
            if not theme.strip(): continue
            await engine.run_v44(theme, task)
            await asyncio.sleep(2)

    await asyncio.gather(runner.run(task), input_loop())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n[SYSTEM CRITICAL] {e}")
        traceback.print_exc()
