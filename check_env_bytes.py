import os

def check_env():
    env_path = ".env"
    if not os.path.exists(env_path):
        print("❌ .env file not found!")
        return

    with open(env_path, "rb") as f:
        content = f.read()
        print(f"📄 Full hex representation:\n{content.hex()}")
        print(f"\n📄 Text representation (repr):\n{repr(content)}")
        
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        key = os.getenv("OPENAI_API_KEY")
        print(f"\n🔑 OPENAI_API_KEY from os.getenv: {repr(key)}")
        if key:
            print(f"📏 Length: {len(key)}")
            if key.startswith("sk-proj-"):
                print("✅ Pattern: Starts with sk-proj-")
    except Exception as e:
        print(f"❌ Error loading .env: {e}")

if __name__ == "__main__":
    check_env()
