import os
import sys
import certifi
import ssl
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

def test_new_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Key is missing")
        return
    
    api_key = api_key.strip()
    print(f"Testing NEW Personal Key: {api_key[:15]}...")
    
    # 2026년 날짜 대응을 위한 SSL 컨텍스트 설정
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    # OpenAI 클라이언트 생성 시 SSL 컨텍스트 전달 (일부 환경에서 필요)
    # 직접 전달이 안될 경우 환경 변수로 강제 지정 시도
    os.environ["SSL_CERT_FILE"] = certifi.where()
    
    client = OpenAI(api_key=api_key)
    
    try:
        print("🚀 Sending request to OpenAI...")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        print("✅ SUCCESS!")
        print(f"Response: {completion.choices[0].message.content}")
    except Exception as e:
        print("❌ FAILED!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")

if __name__ == "__main__":
    test_new_key()
