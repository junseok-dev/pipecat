import socket
import os
import requests
import urllib3
import time

# 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def network_doctor_to_file():
    with open("net_doctor_log.txt", "w", encoding="utf-8") as f:
        f.write("--- Network Connectivity Doctor ---\n")
        
        # 1. DNS 체크
        f.write("\n1. DNS Resolution Check...\n")
        try:
            ip = socket.gethostbyname("api.openai.com")
            f.write(f"✅ Resolved api.openai.com to {ip}\n")
        except Exception as e:
            f.write(f"❌ DNS FAILED: {e}\n")

        # 2. Port 443 TCP Check
        f.write("\n2. Port 443 (HTTPS) Connection Check...\n")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            start = time.time()
            s.connect(("api.openai.com", 443))
            end = time.time()
            f.write(f"✅ Socket connected to api.openai.com:443 in {end-start:.2f}s\n")
            s.close()
        except Exception as e:
            f.write(f"❌ Port 443 Connection FAILED: {e}\n")

        # 3. Simple HTTP GET (No SSL Verify)
        f.write("\n3. Simple API Probe (verify=False)...\n")
        try:
            res = requests.get("https://api.openai.com/v1/models", 
                               headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                               verify=False, timeout=5)
            f.write(f"✅ API Probe SUCCESS! Status: {res.status_code}\n")
        except Exception as e:
            f.write(f"❌ API Probe FAILED (Timeout or Blocked): {e}\n")

        f.write("\n4. Proxy/Env Check...\n")
        f.write(f"HTTP_PROXY: {os.environ.get('HTTP_PROXY')}\n")
        f.write(f"HTTPS_PROXY: {os.environ.get('HTTPS_PROXY')}\n")

if __name__ == "__main__":
    network_doctor_to_file()
