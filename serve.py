#!/usr/bin/env python3
"""开发服务器 - 预览生成的静态站点"""
import http.server
import socketserver
import webbrowser
from pathlib import Path

PORT = 8000
OUTPUT_DIR = Path(__file__).parent / "output"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(OUTPUT_DIR), **kwargs)

print("=" * 50)
print(f"  流量卡优选 - 开发服务器")
print(f"  地址: http://localhost:{PORT}")
print(f"  按 Ctrl+C 停止服务器")
print("=" * 50)

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
