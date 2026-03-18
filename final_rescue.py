import os
import httpx
import asyncio
import ssl
from dotenv import load_dotenv

# 전역 SSL 무력화 (2026년 날짜 대응 최후 수단)
ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv(override=True)

async def final_answer():
    print("\n" + "="*50)
    print("🌟 FINAL RECOVERY: EMERGENCY AI SYSTEM ONLINE")
    print("="*50)
    
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY missing in .env")
        return

    print("🚀 Connecting... (Ignoring SSL & Threading issues)")
    
    # 🚨 input() 없이 즉시 요청하는 다이렉트 호출
    async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a very helpful assistant."},
                        {"role": "user", "content": "Tell me a very short 1-sentence story about a miracle!"}
                    ],
                    "max_tokens": 50
                }
            )
            
            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content']
                print("\n✅ CONNECTION ESTABLISHED!")
                print(f"🤖 Bot Story: {answer}")
                print("\n" + "*"*50)
                print("💡 Success! AI is talking to you again.")
                print("💡 Once this works, we will restore the voice and images.")
                print("*"*50)
            else:
                print(f"❌ API Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ System Error: {e}")

if __name__ == "__main__":
    asyncio.run(final_answer())
