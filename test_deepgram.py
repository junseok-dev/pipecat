import os
import httpx
import asyncio
import ssl
from dotenv import load_dotenv

# 전역 SSL 무력화
ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv(override=True)

async def test_deepgram_direct():
    print("\n--- DEEPGRAM DIRECT API TEST ---")
    api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
    if not api_key:
        print("❌ ERROR: DEEPGRAM_API_KEY missing")
        return

    # 1. Deepgram API 직접 호출 (HTTPS & SSL Bypass)
    url = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    payload = {"text": "Hello, this is a test from Deepgram. If you see this, the API is working."}

    async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
        try:
            print("🚀 Sending request to Deepgram...")
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                print("✅ SUCCESS! Deepgram responded with audio data.")
                print(f"   Audio size: {len(response.content)} bytes")
                # 파일로 저장해서 확인
                with open("test_audio.mp3", "wb") as f:
                    f.write(response.content)
                print(f"   Saved to '{os.path.abspath('test_audio.mp3')}'")
            else:
                print(f"❌ FAILED! Status: {response.status_code}")
                print(f"   Details: {response.text}")
        except Exception as e:
            print(f"❌ CONNECTION ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_deepgram_direct())
