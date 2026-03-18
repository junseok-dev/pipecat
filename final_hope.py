import os
import socket
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)

async def final_hope():
    print("--- Final Hope Diagnostic (IPv4 + No SSL) ---")
    
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("❌ Error: OPENAI_API_KEY is missing")
        return

    # 1. IP 주소 강제 추출 (IPv4)
    print("\n1. Resolving api.openai.com (IPv4)...")
    try:
        # IPv4 주소만 가져오기
        ais = socket.getaddrinfo("api.openai.com", 443, socket.AF_INET)
        target_ip = ais[0][4][0]
        print(f"✅ Target IP: {target_ip}")
    except Exception as e:
        print(f"❌ DNS Resolution Failed: {e}")
        return

    # 2. 직접 통신 테스트 (SSL 무시 + 타임아웃 15초)
    print(f"\n2. Poking {target_ip} directly with Header...")
    
    # 🚨 극약처방: 모든 라이브러리 우회, 순수 httpx + verify=False
    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        try:
            print("🚀 Sending request...")
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5
                }
            )
            print(f"✅ Response Received! Status: {response.status_code}")
            print(f"💬 Body: {response.text}")
        except Exception as e:
            print(f"❌ Connection FAILED: {type(e).__name__} - {e}")
            print("\n💡 결론: 회사 랜선에서 api.openai.com으로의 통신 자체가 '물리적'으로 막혀있습니다.")
            print("💡 해결책: 노트북이시라면 [스마트폰 핫스팟]을 켜서 랜선을 뽑고 연결해 보세요.")

if __name__ == "__main__":
    try:
        asyncio.run(final_hope())
    except KeyboardInterrupt:
        pass
