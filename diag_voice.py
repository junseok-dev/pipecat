import requests
import os
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings()
load_dotenv(override=True)

def diag_deepgram():
    print("--- DEEPGRAM SYNC DIAGNOSTIC ---")
    key = os.getenv("DEEPGRAM_API_KEY", "").strip()
    if not key:
        print("❌ NO KEY")
        return

    url = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
    headers = {"Authorization": f"Token {key}", "Content-Type": "application/json"}
    payload = {"text": "I am testing the voice line. Please work."}

    try:
        print("🚀 Sending request (verify=False)...")
        res = requests.post(url, headers=headers, json=payload, verify=False, timeout=10)
        print(f"✅ Response: {res.status_code}")
        if res.status_code == 200:
            with open("diag_audio.mp3", "wb") as f:
                f.write(res.content)
            print(f"✅ Saved diag_audio.mp3 ({len(res.content)} bytes)")
        else:
            print(f"❌ Error: {res.text}")
    except Exception as e:
        print(f"❌ Crash: {e}")

if __name__ == "__main__":
    diag_deepgram()
