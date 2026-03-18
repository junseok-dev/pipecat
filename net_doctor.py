import socket
import os
import requests
import urllib3
import time

# 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def network_doctor():
    print("--- Network Connectivity Doctor ---")
    
    # 1. DNS 체크
    print("\n1. DNS Resolution Check...")
    try:
        ip = socket.gethostbyname("api.openai.com")
        print(f"✅ Resolved api.openai.com to {ip}")
    except Exception as e:
        print(f"❌ DNS FAILED: {e}")

    # 2. Port 443 TCP Check
    print("\n2. Port 443 (HTTPS) Connection Check...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        start = time.time()
        s.connect(("api.openai.com", 443))
        end = time.time()
        print(f"✅ Socket connected to api.openai.com:443 in {end-start:.2f}s")
        s.close()
    except Exception as e:
        print(f"❌ Port 443 Connection FAILED: {e}")

    # 3. Simple HTTP GET (No SSL Verify)
    print("\n3. Simple API Probe (verify=False)...")
    try:
        res = requests.get("https://api.openai.com/v1/models", 
                           headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                           verify=False, timeout=5)
        print(f"✅ API Probe SUCCESS! Status: {res.status_code}")
    except Exception as e:
        print(f"❌ API Probe FAILED (Timeout or Blocked): {e}")

    # 4. Environment Check
    print("\n4. Proxy/Env Check...")
    print(f"HTTP_PROXY: {os.environ.get('HTTP_PROXY')}")
    print(f"HTTPS_PROXY: {os.environ.get('HTTPS_PROXY')}")

if __name__ == "__main__":
    network_doctor()
