"""零·智能限流API调用器 — 解决429限流"""
import time, json, urllib.request, threading

class SmartAPICaller:
    """带智能限流的API调用器"""
    def __init__(self):
        from api_config import API_KEY, API_BASE, MODEL
        self.key = API_KEY
        self.base = API_BASE
        self.model = MODEL
        self.call_count = 0
        self.success_count = 0
        self.error_429_count = 0
        self.total_tokens = 0
        self._last_call_time = 0
        self._min_interval = 2.0
        self._backoff_until = 0
    
    def call(self, prompt: str, max_tokens: int = 200, retries: int = 3) -> dict:
        for attempt in range(retries):
            now = time.time()
            if now < self._backoff_until:
                time.sleep(self._backoff_until - now)
            elapsed = time.time() - self._last_call_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call_time = time.time()
            self.call_count += 1
            try:
                data = json.dumps({
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens, "temperature": 0.7,
                }).encode()
                req = urllib.request.Request(
                    f"{self.base}/chat/completions", data=data,
                    headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
                )
                t0 = time.time()
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                # DeepSeek reasoning模型: content在reasoning_content字段
                if not content:
                    msg = result.get("choices", [{}])[0].get("message", {})
                    reasoning = msg.get("reasoning_content", "")
                    if reasoning:
                        # 提取最后一个完整句子
                        import re
                        sentences = re.split(r'(?<=[。！？\n])', reasoning)
                        content = sentences[-2] if len(sentences) >= 2 else reasoning[-200:]
                    else:
                        content = ""
                tokens = result.get("usage", {}).get("total_tokens", 0)
                self.success_count += 1
                self.total_tokens += tokens
                return {"success": True, "content": content[:500], "tokens": tokens,
                        "latency": round(time.time()-t0, 1), "attempt": attempt+1}
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    self.error_429_count += 1
                    self._backoff_until = time.time() + 5 * (3 ** attempt)
                    self._min_interval = min(10.0, self._min_interval * 1.5)
                    continue
                return {"success": False, "error": f"HTTP {e.code}", "attempt": attempt+1}
            except Exception as e:
                return {"success": False, "error": str(e)[:80], "attempt": attempt+1}
        return {"success": False, "error": "max retries", "attempt": retries}
