import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

def final_poke():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Key missing")
        return
    
    api_key = api_key.strip()
    print(f"Poking OpenAI with: {api_key[:10]}...")
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5
    }
    
    try:
        # verify=False로 SSL 검증을 완전히 끄고 시도
        print("🚀 Sending request (SSL VERIFY = FALSE)...")
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=10)
        print(f"✅ Status: {response.status_code}")
        print(f"💬 Response: {response.text}")
    except Exception as e:
        print(f"❌ Even with SSL ignore, it FAILED: {e}")

if __name__ == "__main__":
    final_poke()
