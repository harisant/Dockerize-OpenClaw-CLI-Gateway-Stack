#!/usr/bin/env python3
"""
OpenClaw Simulator Test Script for Antigravity CLI Gateway
Simulates OpenClaw agent requests to http://localhost:4569/v1/chat/completions
Zero external dependencies (Python 3 standard library only).
"""

import sys
import os
import json
import time
import argparse
import urllib.request
import urllib.error
import urllib.parse

# ANSI colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def log_header(title):
    print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")

def log_success(msg):
    print(f"{GREEN}✔ {msg}{RESET}")

def log_info(msg):
    print(f"{CYAN}ℹ {msg}{RESET}")

def log_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def log_error(msg):
    print(f"{RED}✖ {msg}{RESET}")

def build_headers(api_key=None):
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "OpenClaw-Agent/2026.10 (macOS; Simulator)",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers

def test_health(base_url, api_key=None):
    log_header("1. Health Check (GET /health)")
    url = f"{base_url}/health"
    start = time.time()
    try:
        req = urllib.request.Request(url, headers=build_headers(api_key), method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed = int((time.time() - start) * 1000)
            status = resp.status
            body = resp.read().decode("utf-8")
            log_success(f"Status: {status} ({elapsed}ms)")
            try:
                data = json.loads(body)
                print(f"{DIM}{json.dumps(data, indent=2)}{RESET}")
            except Exception:
                print(f"{DIM}{body}{RESET}")
            return True
    except urllib.error.URLError as e:
        log_error(f"Gagal menghubungi {url}: {e}")
        return False

def test_models(base_url, api_key=None):
    log_header("2. Catalog Models (GET /v1/models)")
    url = f"{base_url}/v1/models"
    start = time.time()
    try:
        req = urllib.request.Request(url, headers=build_headers(api_key), method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed = int((time.time() - start) * 1000)
            status = resp.status
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            models = [m.get("id") for m in data.get("data", [])]
            log_success(f"Status: {status} ({elapsed}ms) - Ditemukan {len(models)} model:")
            for m in models:
                print(f"  • {BOLD}{m}{RESET}")
            return models
    except Exception as e:
        log_error(f"Gagal mengambil model dari {url}: {e}")
        return []

def test_chat_completion(base_url, model, prompt, effort="medium", api_key=None):
    log_header(f"3. Chat Completion (Non-Streaming) [{model} | effort={effort}]")
    url = f"{base_url}/v1/chat/completions"

    payload = {
        "model": model,
        "reasoning_effort": effort,
        "messages": [
            {
                "role": "system",
                "content": "You are OpenClaw agent running via Antigravity CLI Gateway. session=agent:openclaw-test-session"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    log_info(f"Mengirim pesan: \"{prompt}\"")
    start = time.time()
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=build_headers(api_key), method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            elapsed = int((time.time() - start) * 1000)
            body = resp.read().decode("utf-8")
            result = json.loads(body)

            content = result["choices"][0]["message"].get("content", "")
            usage = result.get("usage", {})

            log_success(f"Response diterima ({elapsed}ms):")
            print(f"\n{BOLD}Output Jawaban:{RESET}\n{content}\n")

            if usage:
                print(f"{DIM}Tokens: prompt={usage.get('prompt_tokens')} | completion={usage.get('completion_tokens')} | total={usage.get('total_tokens')}{RESET}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        log_error(f"HTTP Error {e.code}: {e.reason}\n{body}")
        return False
    except Exception as e:
        log_error(f"Error request: {e}")
        return False

def test_chat_streaming(base_url, model, prompt, effort="medium", api_key=None):
    log_header(f"4. Chat Completion (Streaming SSE) [{model} | effort={effort}]")
    url = f"{base_url}/v1/chat/completions"

    payload = {
        "model": model,
        "reasoning_effort": effort,
        "stream": True,
        "stream_options": {
            "include_usage": True
        },
        "messages": [
            {
                "role": "system",
                "content": "You are OpenClaw, a coding assistant. session=agent:stream-test"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    log_info(f"Streaming prompt: \"{prompt}\"")
    start = time.time()
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=build_headers(api_key), method="POST")

        with urllib.request.urlopen(req, timeout=120) as resp:
            print(f"{BOLD}Streaming tokens: {RESET}", end="", flush=True)
            usage_data = None

            buffer = ""
            for raw_line in resp:
                line = raw_line.decode("utf-8")
                if line.startswith("data: "):
                    chunk_str = line[6:].strip()
                    if chunk_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(chunk_str)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            thinking = delta.get("reasoning_content", "")
                            if thinking:
                                print(f"{YELLOW}{thinking}{RESET}", end="", flush=True)
                            if content:
                                print(f"{content}", end="", flush=True)
                        if "usage" in chunk and chunk["usage"]:
                            usage_data = chunk["usage"]
                    except json.JSONDecodeError:
                        pass

            elapsed = int((time.time() - start) * 1000)
            print(f"\n\n{GREEN}✔ Stream Selesai ({elapsed}ms){RESET}")
            if usage_data:
                print(f"{DIM}Stream Usage: {json.dumps(usage_data)}{RESET}")
            return True
    except Exception as e:
        log_error(f"Error streaming: {e}")
        return False

def test_structured_output(base_url, model, api_key=None):
    log_header(f"5. Structured Output (response_format=json_object) [{model}]")
    url = f"{base_url}/v1/chat/completions"

    prompt = "Kembalikan informasi tentang project openclaw dalam format JSON dengan key: name, gateway_supported, status"
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {
            "type": "json_object"
        }
    }

    start = time.time()
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=build_headers(api_key), method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            elapsed = int((time.time() - start) * 1000)
            body = resp.read().decode("utf-8")
            result = json.loads(body)
            raw_content = result["choices"][0]["message"].get("content", "")

            parsed = json.loads(raw_content)
            log_success(f"Valid JSON diterima ({elapsed}ms):")
            print(f"{BOLD}{json.dumps(parsed, indent=2)}{RESET}")
            return True
    except Exception as e:
        log_error(f"Structured output gagal: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="OpenClaw Simulator for Antigravity CLI Gateway")
    parser.add_argument("--url", default="http://localhost:4569", help="Base URL of Antigravity CLI Gateway (default: http://localhost:4569)")
    parser.add_argument("--model", default="gemini-3.8-flash", help="Model name (default: gemini-3.8-flash)")
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high"], help="Reasoning effort level")
    parser.add_argument("--prompt", default="Sebutkan 3 kelebihan OpenClaw dengan singkat.", help="Prompt text to test")
    parser.add_argument("--stream", action="store_true", help="Run in streaming mode")
    parser.add_argument("--all", action="store_true", help="Run all test suites (Health, Models, Chat, Stream, JSON)")
    parser.add_argument("--api-key", default=os.environ.get("AGY_CLI_GATEWAY_API_KEY", ""), help="API key if configured")

    args = parser.parse_args()

    print(f"{BOLD}{GREEN}===================================================={RESET}")
    print(f"{BOLD}{GREEN} OpenClaw Simulator -> Antigravity Gateway Tester  {RESET}")
    print(f"{BOLD}{GREEN} Target Gateway: {args.url}{RESET}")
    print(f"{BOLD}{GREEN} Default Model:  {args.model} (effort: {args.effort}){RESET}")
    print(f"{BOLD}{GREEN}===================================================={RESET}")

    if args.all:
        h_ok = test_health(args.url, args.api_key)
        if not h_ok:
            log_warning("Health check gagal. Pastikan Antigravity Gateway sedang berjalan di port 4569.")
            sys.exit(1)

        test_models(args.url, args.api_key)
        test_chat_completion(args.url, args.model, args.prompt, effort=args.effort, api_key=args.api_key)
        test_chat_streaming(args.url, args.model, "Buat 1 baris haiku tentang programming.", effort=args.effort, api_key=args.api_key)
        test_structured_output(args.url, args.model, api_key=args.api_key)
        print(f"\n{BOLD}{GREEN}Semua pengujian selesai!{RESET}\n")
    elif args.stream:
        test_chat_streaming(args.url, args.model, args.prompt, effort=args.effort, api_key=args.api_key)
    else:
        # Default run health + single chat completion
        test_health(args.url, args.api_key)
        test_chat_completion(args.url, args.model, args.prompt, effort=args.effort, api_key=args.api_key)

if __name__ == "__main__":
    main()
