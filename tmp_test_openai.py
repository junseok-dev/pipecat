import asyncio
import os
import aiohttp
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(override=True)

async def test_openai():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env")
        return

    print(f"Testing OpenAI with key: {api_key[:10]}...")
    client = AsyncOpenAI(api_key=api_key)
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say hello!"}],
            max_tokens=10
        )
        print(f"Response: {response.choices[0].message.content}")
        print("OpenAI API test SUCCESS!")
    except Exception as e:
        print(f"OpenAI API test FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai())
