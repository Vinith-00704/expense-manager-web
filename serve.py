"""
LAN / Local Production Server (Windows-friendly)
Run this instead of run.py for stable local hosting:
    python serve.py
Others on your WiFi can access at: http://YOUR_PC_IP:5000
Find your IP with: ipconfig -> IPv4 Address
"""
from waitress import serve
from run import app

if __name__ == "__main__":
    print("=" * 50)
    print(" FinanceOS - Production Server (Waitress)")
    print(" Running at: http://0.0.0.0:5000")
    print(" Find your IP: run `ipconfig` -> IPv4 Address")
    print("=" * 50)
    serve(app, host="0.0.0.0", port=5000, threads=4)
