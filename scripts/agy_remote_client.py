#!/usr/bin/env python3
"""
Client wrapper for agy inside Docker container.
Forwards CLI arguments and stdin to Host Daemon Bridge (host.docker.internal:45690).
"""

import sys
import os
import json
import urllib.request
import urllib.error

BRIDGE_URL = os.environ.get("AGY_BRIDGE_URL", "http://host.docker.internal:45690/exec")

def main():
    args = sys.argv[1:]

    # Fast path for version check
    if "--version" in args:
        try:
            req = urllib.request.Request(
                BRIDGE_URL.replace("/exec", "/health"),
                headers={"User-Agent": "agy-remote-client"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "ok":
                    print("agy (remote host bridge) 1.3.4")
                    sys.exit(0)
        except Exception:
            pass

    # Read stdin if available
    stdin_data = ""
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read()
        except Exception:
            pass

    payload = {
        "args": args,
        "stdin": stdin_data,
        "env": {
            k: v for k, v in os.environ.items()
            if k.startswith("OPENCLAW_") or k.startswith("AGY_")
        }
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            BRIDGE_URL,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3900) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)

            stdout_text = result.get("stdout", "")
            stderr_text = result.get("stderr", "")
            exit_code = result.get("exit_code", 0)

            if stdout_text:
                sys.stdout.write(stdout_text)
                sys.stdout.flush()
            if stderr_text:
                sys.stderr.write(stderr_text)
                sys.stderr.flush()

            sys.exit(exit_code)
    except urllib.error.URLError as e:
        sys.stderr.write(f"[agy-client error] Cannot connect to Host Daemon Bridge at {BRIDGE_URL}: {e}\n")
        sys.stderr.write("Make sure 'python3 scripts/host_agy_daemon.py' is running on the macOS host.\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"[agy-client error] {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
