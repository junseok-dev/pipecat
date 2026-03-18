import os
import sys
import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

def final_check():
    with open("openai_result.txt", "w", encoding="utf-8") as f:
        now = datetime.datetime.now()
        f.write(f"--- Diagnostic at {now} ---\n")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            f.write("❌ Error: OPENAI_API_KEY is empty\n")
            return

        api_key = api_key.strip()
        f.write(f"Key starts with: {api_key[:10]}...\n")
        
        client = OpenAI(api_key=api_key)
        
        try:
            f.write("🚀 Sending request to OpenAI...\n")
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            f.write("✅ SUCCESS!\n")
            f.write(f"Response: {completion.choices[0].message.content}\n")
        except Exception as e:
            f.write("❌ FAILED!\n")
            f.write(f"Type: {type(e).__name__}\n")
            f.write(f"Message: {str(e)}\n\n")
            
            # 상세 분석
            import traceback
            f.write(f"Traceback:\n{traceback.format_exc()}\n")

if __name__ == "__main__":
    final_check()
