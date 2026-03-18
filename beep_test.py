import winsound
import time

def test_speaker():
    print("--- WINDOWS SPEAKER TEST ---")
    try:
        print("Playing Beep (1000Hz, 500ms)...")
        winsound.Beep(1000, 500)
        time.sleep(0.5)
        print("Playing Beep (1500Hz, 500ms)...")
        winsound.Beep(1500, 500)
        print("✅ If you heard two beeps, your Windows speaker is WORKING.")
    except Exception as e:
        print(f"❌ Windows Speaker Error: {e}")

if __name__ == "__main__":
    test_speaker()
