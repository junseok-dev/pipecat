import os
import socket
import requests
import time
import urllib3

urllib3.disable_warnings()

def final_network_report():
    with open("network_block_report.txt", "w", encoding="utf-8") as f:
        f.write("=== FINAL NETWORK BLOCKAGE REPORT ===\n")
        f.write(f"Timestamp: {time.ctime()}\n\n")

        # 1. Proxy Check
        f.write("1. Environment Proxy Settings:\n")
        f.write(f"HTTP_PROXY: {os.environ.get('HTTP_PROXY')}\n")
        f.write(f"HTTPS_PROXY: {os.environ.get('HTTPS_PROXY')}\n")
        f.write(f"NO_PROXY: {os.environ.get('NO_PROXY')}\n\n")

        # 2. General Internet Check (Google)
        f.write("2. General Internet Check (google.com): ")
        try:
            r = requests.get("https://google.com", timeout=5, verify=False)
            f.write(f"SUCCESS (Status: {r.status_code})\n")
        except Exception as e:
            f.write(f"FAILED ({e})\n")

        # 3. OpenAI Connectivity Check
        f.write("3. OpenAI API Check (api.openai.com): ")
        try:
            # DNS만이라도 되는지 확인
            ip = socket.gethostbyname("api.openai.com")
            f.write(f"DNS Resolved to {ip}. ")
            
            # TCP 연결 시도
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((ip, 443))
            f.write("TCP Connection SUCCESS.\n")
            s.close()
        except Exception as e:
            f.write(f"TCP Connection FAILED ({e})\n")

        f.write("\n=== CONCLUSION ===\n")
        f.write("If Google is SUCCESS but OpenAI is FAILED, your LAN is blocking AI domains.\n")
        f.write("If BOTH FAILED, your overall network/proxy setup is broken.\n")

if __name__ == "__main__":
    final_network_report()
