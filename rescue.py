import os
import httpx
import asyncio
import ssl
import time
from dotenv import load_dotenv

# 전역 SSL 무력화
ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv(override=True)

async def rescue_to_file():
    log_file = "rescue_log.txt"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"--- Rescue Mission at {time.ctime()} ---\n")
        
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            f.write("❌ ERROR: OPENAI_API_KEY is empty\n")
            return

        f.write(f"Key used: {api_key[:15]}...\n")
        f.write("🚀 Sending Request (stream=False)...\n")
        
        async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": "Hello! Show me you can respond!"}],
                        "max_tokens": 10
                    }
                )
                
                if response.status_code == 200:
                    ai_text = response.json()['choices'][0]['message']['content']
                    f.write("✅ SUCCESS! AI responded.\n")
                    f.write(f"🤖 BOT: {ai_text}\n")
                    print(f"\n✅ SUCCESS! AI says: {ai_text}") # 터미널에도 출력
                else:
                    f.write(f"❌ FAILED! Status: {response.status_code}\n")
                    f.write(f"Body: {response.text}\n")
            except Exception as e:
                f.write(f"❌ CRITICAL ERROR: {e}\n")

if __name__ == "__main__":
    asyncio.run(rescue_to_file())
