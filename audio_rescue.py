import os
import requests
import urllib3
import subprocess
from dotenv import load_dotenv

urllib3.disable_warnings()
load_dotenv(override=True)

def final_audio_rescue():
    print("--- ULTIMATE AUDIO RESCUE ---")
    key = os.getenv("OPENAI_API_KEY", "").strip()
    
    # 1. OpenAI TTS 호출 (이미 검증된 OpenAI 경로 사용)
    url = "https://api.openai.com/v1/audio/speech"
    headers = {"Authorization": f"Bearer {key}"}
    payload = {
        "model": "tts-1",
        "voice": "alloy",
        "input": "Connection successful. I am speaking through the system player."
    }

    try:
        print("🚀 Requesting Voice from OpenAI...")
        res = requests.post(url, headers=headers, json=payload, verify=False, timeout=15)
        
        if res.status_code == 200:
            audio_path = "rescue_voice.mp3"
            with open(audio_path, "wb") as f:
                f.write(res.content)
            print(f"✅ Success! Voice saved as {audio_path}")
            
            # 2. 시스템 플레이어로 직접 실행 (PyAudio 우회)
            print("🔊 Attempting to play via System Player...")
            os.startfile(audio_path)
            print("✅ If a music player opened and you heard sound, the hardware is PERFECT.")
        else:
            print(f"❌ OpenAI TTS Failed: {res.text}")
    except Exception as e:
        print(f"❌ Crash: {e}")

if __name__ == "__main__":
    final_audio_rescue()
