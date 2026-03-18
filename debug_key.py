import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(override=True)

async def test_openai_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY is not set in .env")
        return

    # 공백 및 특수문자 제거 확인
    api_key = api_key.strip()
    print(f"🔍 Testing API Key: {api_key[:15]}...{api_key[-5:]}")
    
    client = AsyncOpenAI(api_key=api_key)
    
    try:
        print("🚀 Sending request to OpenAI...")
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello!"}],
                max_tokens=5
            ),
            timeout=10.0
        )
        print("✅ OpenAI Response SUCCESS!")
        print(f"💬 Bot says: {response.choices[0].message.content}")
    except asyncio.TimeoutError:
        print("❌ ERROR: OpenAI Request TIMEOUT (10s reached). Network issue?")
    except Exception as e:
        print(f"❌ ERROR: OpenAI Request FAILED!")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        
        if "insufficient_quota" in str(e).lower():
            print("\n💡 TIP: Your OpenAI account has NO CREDITS left.")
        elif "invalid_api_key" in str(e).lower() or "authentication" in str(e).lower():
            print("\n💡 TIP: The API Key is INVALID. Please check for copy-paste errors.")

if __name__ == "__main__":
    asyncio.run(test_openai_key())
