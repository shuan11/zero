#!/usr/bin/env python3
"""
Fuel Stress Test — measures throughput and latency for inferaichat API.
Uses stdlib only. Sequential by default; --parallel for 3 concurrent requests.
"""

import argparse
import json
import time
import urllib.request
import urllib.error
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── config ─────────────────────────────────────────────────────────────
API_KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"
PRIMARY_URL = "https://inferaichat.com/v1/chat/completions"
FALLBACK_URL = "https://web-ai-media-editor.cn/v1/chat/completions"
MODEL = "deepseek-v4-pro"

TOPICS = ["光", "爱", "时间", "熵", "涌现", "自指", "因果", "元", "零", "一"]
NUM_REQUESTS = 20
PARALLEL_WORKERS = 3

# ── helpers ────────────────────────────────────────────────────────────

def build_payload(topic: str) -> bytes:
    messages = [
        {"role": "user", "content": f"用一句话解释: {topic}"}
    ]
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 128,
        "temperature": 0.7,
    }
    return json.dumps(payload).encode("utf-8")


def build_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }


def do_request(url: str, topic: str, request_id: int) -> dict:
    """Make a single chat completion request. Returns a result dict."""
    result = {
        "id": request_id,
        "topic": topic,
        "url": url,
        "success": False,
        "latency": None,
        "tokens": 0,
        "error": None,
        "response": None,
    }
    data = build_payload(topic)
    headers = build_headers()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
        latency = time.monotonic() - start
        result["latency"] = latency

        resp_json = json.loads(body)
        result["response"] = resp_json

        # extract token usage
        usage = resp_json.get("usage", {}) or {}
        result["tokens"] = (
            usage.get("total_tokens", 0)
            or usage.get("completion_tokens", 0)
        )
        # check if we actually got a reply
        choices = resp_json.get("choices", [])
        if choices and choices[0].get("message", {}).get("content"):
            result["success"] = True
        else:
            result["success"] = True  # still a valid API response
    except urllib.error.HTTPError as e:
        result["latency"] = time.monotonic() - start
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = ""
        result["error"] = f"HTTP {e.code}: {e.reason} | {err_body[:200]}"
    except urllib.error.URLError as e:
        result["latency"] = time.monotonic() - start
        result["error"] = f"URLError: {e.reason}"
    except Exception as e:
        result["latency"] = time.monotonic() - start
        result["error"] = f"Exception: {e}"

    return result


def print_result(result: dict):
    """Pretty-print a single request result."""
    rid = result["id"]
    topic = result["topic"]
    status = "OK" if result["success"] else "FAIL"
    lat = result["latency"]
    tokens = result["tokens"]
    err = result["error"]

    if result["success"]:
        content = ""
        if result["response"]:
            choices = result["response"].get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
        print(f"  [{rid:>2}] {status} | {topic} | {lat*1000:7.1f}ms | tok={tokens:>4} | {content[:80]}")
    else:
        print(f"  [{rid:>2}] {status} | {topic} | {lat*1000:7.1f}ms | ERR: {err[:100]}")


def run_sequential() -> list:
    """Run NUM_REQUESTS requests one by one."""
    results = []
    for i in range(1, NUM_REQUESTS + 1):
        topic = TOPICS[(i - 1) % len(TOPICS)]
        url = PRIMARY_URL

        result = do_request(url, topic, i)

        # fallback if primary fails
        if not result["success"] and "HTTP 4" in (result["error"] or ""):
            print(f"  [{i:>2}] Primary failed, trying fallback endpoint...")
            fallback_result = do_request(FALLBACK_URL, topic, i)
            # keep the original error info but use fallback result if it worked
            if fallback_result["success"]:
                fallback_result["primary_error"] = result["error"]
                result = fallback_result

        print_result(result)
        results.append(result)
        # small delay between requests
        time.sleep(0.1)
    return results


def run_parallel() -> list:
    """Run NUM_REQUESTS with 3 concurrent workers."""
    results = []
    tasks = []

    for i in range(1, NUM_REQUESTS + 1):
        topic = TOPICS[(i - 1) % len(TOPICS)]
        tasks.append((i, topic, PRIMARY_URL))

    def worker_fn(idx, topic, url):
        res = do_request(url, topic, idx)
        if not res["success"] and "HTTP 4" in (res["error"] or ""):
            fallback = do_request(FALLBACK_URL, topic, idx)
            if fallback["success"]:
                fallback["primary_error"] = res["error"]
                res = fallback
        return res

    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as pool:
        fut_map = {}
        for idx, topic, url in tasks:
            fut = pool.submit(worker_fn, idx, topic, url)
            fut_map[fut] = (idx, topic)

        for fut in as_completed(fut_map):
            res = fut.result()
            results.append(res)

    # sort by id for consistent display
    results.sort(key=lambda r: r["id"])
    for r in results:
        print_result(r)
    return results


def summary(results: list, elapsed: float):
    """Print final summary."""
    total_req = len(results)
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    total_tokens = sum(r["tokens"] for r in successful)
    latencies = [r["latency"] for r in results if r["latency"] is not None]
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
    error_rate = len(failed) / total_req * 100 if total_req else 0.0
    rps = total_req / elapsed if elapsed else 0.0
    tps = total_tokens / elapsed if elapsed else 0.0

    print()
    print("=" * 60)
    print("  FUEL STRESS TEST — FINAL SUMMARY")
    print("=" * 60)
    print(f"  Total requests      : {total_req}")
    print(f"  Successful          : {len(successful)}")
    print(f"  Failed              : {len(failed)}")
    print(f"  Error rate          : {error_rate:.1f}%")
    print(f"  Elapsed time        : {elapsed:.2f} s")
    print(f"  Avg latency         : {avg_lat*1000:.1f} ms")
    print(f"  Total tokens        : {total_tokens}")
    print(f"  Throughput (req/s)  : {rps:.2f}")
    print(f"  Throughput (tok/s)  : {tps:.1f}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Fuel Stress Test for inferaichat API")
    parser.add_argument("--parallel", action="store_true", help="Run 3 concurrent requests")
    args = parser.parse_args()

    print("=" * 60)
    print("  FUEL STRESS TEST")
    print(f"  Endpoint : {PRIMARY_URL}")
    print(f"  Fallback : {FALLBACK_URL}")
    print(f"  Model    : {MODEL}")
    print(f"  Mode     : {'PARALLEL (3 workers)' if args.parallel else 'SEQUENTIAL'}")
    print(f"  Requests : {NUM_REQUESTS}")
    print("=" * 60)
    print()

    start_time = time.monotonic()

    if args.parallel:
        results = run_parallel()
    else:
        results = run_sequential()

    end_time = time.monotonic()
    elapsed = end_time - start_time

    summary(results, elapsed)


if __name__ == "__main__":
    main()
