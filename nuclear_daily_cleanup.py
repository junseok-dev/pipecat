import os
import sys
import shutil

def nuclear_cleanup():
    print("--- [NUCLEAR CLEANUP] Finding conflicting daily.py ---")
    
    # 1. 사이트 패키지 경로 찾기
    for path in sys.path:
        if 'site-packages' in path:
            target = os.path.join(path, "daily.py")
            if os.path.exists(target):
                print(f"🚩 FOUND: {target}")
                try:
                    os.remove(target)
                    print(f"✅ DELETED: {target}")
                except Exception as e:
                    print(f"❌ FAILED TO DELETE: {e}")
            
            # __pycache__ 도 제거
            cache = os.path.join(path, "__pycache__", "daily.cpython-313.pyc")
            if os.path.exists(cache):
                try:
                    os.remove(cache)
                    print(f"✅ DELETED CACHE: {cache}")
                except:
                    pass

    print("--- Cleanup finished. ---")

if __name__ == "__main__":
    nuclear_cleanup()
