import socket
import ssl
import time

def check(host, port=443):
    print(f"--- Checking {host}:{port} ---")
    try:
        # 1. TCP Connect
        s = socket.create_connection((host, port), timeout=3)
        print(f"✅ TCP Connected")
        
        # 2. SSL Wrap (Check if certificate is accepted)
        try:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(s, server_hostname=host) as ss:
                print(f"✅ SSL Handshake Success (Cert Valid)")
        except Exception as ssl_e:
            print(f"❌ SSL Handshake FAILED: {ssl_e}")
            
    except Exception as e:
        print(f"❌ TCP Connection FAILED: {e}")
    print("-" * 20)

if __name__ == "__main__":
    print(f"System Time: {time.ctime()}")
    check("google.com")
    check("api.openai.com")
    check("api.deepgram.com")
