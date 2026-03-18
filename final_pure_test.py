import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

def quick_test():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY is empty in .env")
        return

    print(f"Checking API Key: {api_key[:10]}...")
    client = OpenAI(api_key=api_key.strip())
    
    try:
        print("🚀 Requesting to OpenAI (Direct)...")
        # 스트리밍이 아닌 일반 요청으로 테스트
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'API confirms connection'"}],
            max_tokens=10
        )
        print("✅ OpenAI Response SUCCESS!")
        print(f"💬 Bot says: {completion.choices[0].message.content}")
    except Exception as e:
        print("❌ OpenAI Request FAILED!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")

if __name__ == "__main__":
    quick_test()
