import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

def test_ignore_ssl():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Key is missing")
        return
    
    api_key = api_key.strip()
    print(f"Testing with key (SSL Ignore): {api_key[:10]}...")
    
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
        # SSL 검증을 명시적으로 무시하고 시도 (원인 파악용)
        print("🚀 Sending request (verify=False)...")
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=10)
        print(f"✅ Response Status: {response.status_code}")
        print(f"💬 Body: {response.text}")
        if response.status_code == 200:
            print("\n💡 SUCCESS! It's an SSL Certificate issue on your machine.")
        elif response.status_code == 401:
            print("\n💡 FAILED! Your API Key is still invalid (Auth error).")
        elif response.status_code == 403:
            print("\n💡 FAILED! Your account/project permission is restricted.")
    except Exception as e:
        print(f"❌ Connection FAILED even without SSL verify: {e}")

if __name__ == "__main__":
    test_ignore_ssl()
