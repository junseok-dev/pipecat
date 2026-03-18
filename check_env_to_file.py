import os

def check_env():
    env_path = ".env"
    with open("env_check.txt", "w", encoding="utf-8") as out:
        if not os.path.exists(env_path):
            out.write("❌ .env file not found!\n")
            return

        with open(env_path, "rb") as f:
            content = f.read()
            out.write(f"📄 Full hex representation:\n{content.hex()}\n")
            out.write(f"\n📄 Text representation (repr):\n{repr(content)}\n")
            
        try:
            from dotenv import load_dotenv
            load_dotenv(override=True)
            key = os.getenv("OPENAI_API_KEY")
            out.write(f"\n🔑 OPENAI_API_KEY from os.getenv: {repr(key)}\n")
        except Exception as e:
            out.write(f"❌ Error loading .env: {e}\n")

if __name__ == "__main__":
    check_env()
