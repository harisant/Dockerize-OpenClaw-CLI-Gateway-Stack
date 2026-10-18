#!/usr/bin/env python3
"""
Host Antigravity Daemon Bridge
Allows Docker containers to run `agy` natively on the macOS host.
Listens on 0.0.0.0:45690.
"""

import sys
import os
import json
import subprocess
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("AGY_HOST_DAEMON_PORT", 45690))
AGY_BIN = os.environ.get("AGY_CLI_BIN") or shutil.which("agy") or os.path.expanduser("~/.local/bin/agy")

class AgyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Concise logging
        sys.stderr.write(f"[HostBridge] {self.address_string()} - {format % args}\n")

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "agy_bin": AGY_BIN, "exists": os.path.exists(AGY_BIN)}).encode())
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/exec":
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"Invalid JSON: {e}".encode())
                return

            args = payload.get("args", [])
            stdin_data = payload.get("stdin", "")
            extra_env = payload.get("env", {})

            cmd = [AGY_BIN] + args
            env = os.environ.copy()
            env.update(extra_env)

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )
                stdout_data, stderr_data = proc.communicate(
                    input=stdin_data.encode("utf-8") if stdin_data else None
                )

                response = {
                    "exit_code": proc.returncode,
                    "stdout": stdout_data.decode("utf-8", errors="replace"),
                    "stderr": stderr_data.decode("utf-8", errors="replace")
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))

            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"agy binary not found at '{AGY_BIN}'"}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        self.send_response(404)
        self.end_headers()

def main():
    print(f"===========================================================")
    print(f" Antigravity CLI Host Daemon Bridge")
    print(f" Listening on 0.0.0.0:{PORT}")
    print(f" Target agy binary: {AGY_BIN}")
    print(f"===========================================================")
    server = HTTPServer(("0.0.0.0", PORT), AgyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Host Daemon Bridge...")
        server.server_close()

if __name__ == "__main__":
    main()
