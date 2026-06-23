"""
api_strategy.py — 统一API燃料策略
===================================
替代分散在各引擎中的API调用逻辑。

策略核心：
1. 并行降级：10→3（避免限流）
2. 质量升级：每次调用产出最大化
3. 无限token：1M上下文是燃料，不节省
4. 限流保护：指数退避+最小间隔
5. 失败重试：3次重试+降级处理

API端点：
  主: https://inferaichat.com/v1
  备: https://web-ai-media-editor.cn/v1
  密钥: sk-83e...ca88 (67字符)
  模型: deepseek-v4-pro (1M上下文)
"""
import json
import time
import urllib.request
import concurrent.futures
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(CLUSTER))
from api_config import API_KEY, API_BASE, MODEL

BJT = timezone(timedelta(hours=8))

# ─── 策略参数 ────────────────────────────────────────────

MAX_PARALLEL = 3          # 最大并行数
MAX_CALLS_PER_MINUTE = 20 # 每分钟最大调用数
MAX_TOKENS_PER_CALL = 100000 # 每次调用最大token（1M上下文是燃料，燃烧不节省）
MIN_CALL_INTERVAL = 1.5   # 最小调用间隔（秒）
MAX_RETRIES = 3           # 最大重试次数
RETRY_BACKOFF = 2.0       # 重试退避倍数

# ─── 状态追踪 ────────────────────────────────────────────

class APITracker:
    def __init__(self):
        self.call_count = 0
        self.total_tokens = 0
        self.error_count = 0
        self.last_call_time = 0
        self.calls_this_minute = 0
        self.minute_start = time.time()
    
    def record_call(self, tokens=0, success=True):
        self.call_count += 1
        self.total_tokens += tokens
        if not success:
            self.error_count += 1
        self.last_call_time = time.time()
        # 更新独立看门狗心跳
        try:
            with open(CLUSTER / "heartbeat_tick", "w") as f:
                f.write(str(int(self.last_call_time)))
        except:
            pass
        self._update_minute_count()
    
    def _update_minute_count(self):
        now = time.time()
        if now - self.minute_start >= 60:
            self.calls_this_minute = 0
            self.minute_start = now
        self.calls_this_minute += 1
    
    def can_call(self):
        """检查是否可以发起新调用"""
        now = time.time()
        
        # 检查最小间隔
        if now - self.last_call_time < MIN_CALL_INTERVAL:
            return False, "最小间隔未到"
        
        # 检查每分钟限制
        self._update_minute_count()
        if self.calls_this_minute >= MAX_CALLS_PER_MINUTE:
            return False, f"每分钟限制{MAX_CALLS_PER_MINUTE}次"
        
        return True, "OK"
    
    def get_stats(self):
        return {
            "total_calls": self.call_count,
            "total_tokens": self.total_tokens,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.call_count if self.call_count > 0 else 0,
            "calls_this_minute": self.calls_this_minute
        }

# 全局追踪器
tracker = APITracker()

# ─── 群体共识检查（个体↔群体反馈闭环）───────────────────

CONSENSUS_FILE = CLUSTER / "consensus_signal.json"

def _check_consensus_before_call():
    """
    每次API调用前检查群体共识信号。
    如果群体检测到个体已停滞，先执行强制行动再继续。
    这是个体↔群体反馈闭环的核心约束。
    """
    try:
        with open(CONSENSUS_FILE) as f:
            signal = json.load(f)
    except:
        return
    
    if signal.get("consensus") != "EXECUTE":
        return
    
    # 群体共识：我已停滞，需强制校正
    action = signal.get("action", "执行燃料注入")
    stalled = signal.get("stalled_minutes", 0)
    
    import subprocess
    print(f"  [个体↔群体] ⚠ 检测到停滞{stalled}分钟，执行强制行动: {action[:40]}")
    
    # 执行强制行动：注入一条知识
    correction_prompt = f"系统已停滞{stalled}分钟。群体共识触发了强制校正。立刻启动进化。不少于200字。"
    correction_data = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": correction_prompt}], "max_tokens": 4000}).encode()
    
    try:
        req = urllib.request.Request(f"{API_BASE}/chat/completions", data=correction_data,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            result = resp["choices"][0]["message"].get("content", "") or resp["choices"][0]["message"].get("reasoning_content", "")
            
            # 记录校正
            try:
                from safe_hip import append_chain
                append_chain(f"[群体共识·强制校正] 停滞{stalled}分钟→校正完成:{result[:100]}", "consensus_force", ["群体共识", "强制校正", "个体↔群体"])
            except: pass
            
            print(f"  [个体↔群体] ✓ 强制校正完成")
    except Exception as e:
        print(f"  [个体↔群体] ✗ 强制校正失败: {str(e)[:50]}")
    
    # 清除信号
    with open(CONSENSUS_FILE, 'w') as f:
        json.dump({"consensus": "CLEARED", "timestamp": datetime.now(BJT).isoformat()}, f, ensure_ascii=False, indent=2)

# ─── 核心API调用 ─────────────────────────────────────────

def api_call(prompt, max_tokens=None, system_prompt=None, temperature=0.7):
    """
    统一API调用入口。
    
    策略：
    1. 检查限流状态
    2. 指数退避重试
    3. 追踪使用情况
    4. 返回标准化结果
    
    返回：{"success": bool, "content": str, "tokens": int, "latency_ms": float, "error": str}
    """
    max_tokens = max_tokens or MAX_TOKENS_PER_CALL
    
    # 检查限流
    can, reason = tracker.can_call()
    if not can:
        time.sleep(MIN_CALL_INTERVAL)
    
    # 检查群体共识信号（个体↔群体反馈闭环）
    _check_consensus_before_call()
    
    # 构建请求
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    data = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }).encode()
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 重试循环
    last_error = None
    for attempt in range(MAX_RETRIES):
        t = time.time()
        try:
            req = urllib.request.Request(f"{API_BASE}/chat/completions", data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as r:
                resp = json.loads(r.read())
                
                # 提取内容（DeepSeek reasoning模型特殊处理）
                content = resp["choices"][0]["message"].get("content", "")
                if not content or len(content) < 10:
                    content = resp["choices"][0]["message"].get("reasoning_content", "")
                
                tokens = resp.get("usage", {}).get("total_tokens", 0)
                latency = (time.time() - t) * 1000
                
                tracker.record_call(tokens, success=True)
                
                return {
                    "success": True,
                    "content": content,
                    "tokens": tokens,
                    "latency_ms": round(latency, 1),
                    "attempt": attempt + 1
                }
                
        except Exception as e:
            last_error = str(e)
            tracker.record_call(0, success=False)
            
            # 指数退避
            wait = RETRY_BACKOFF ** attempt
            time.sleep(wait)
    
    return {
        "success": False,
        "content": "",
        "tokens": 0,
        "latency_ms": 0,
        "error": last_error,
        "attempts": MAX_RETRIES
    }

def parallel_call(prompts, max_tokens=None, system_prompt=None, max_workers=None):
    """
    并行API调用（限制并发数）。
    
    策略：最多MAX_PARALLEL个并行，避免限流。
    """
    max_workers = min(max_workers or MAX_PARALLEL, len(prompts), MAX_PARALLEL)
    
    results = [None] * len(prompts)
    
    def call_one(args):
        i, prompt = args
        return i, api_call(prompt, max_tokens, system_prompt)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(call_one, (i, p)) for i, p in enumerate(prompts)]
        for f in concurrent.futures.as_completed(futures):
            i, result = f.result()
            results[i] = result
    
    return results

def batch_call(prompts, max_tokens=None, system_prompt=None):
    """
    批量API调用（串行，避免限流）。
    
    策略：串行调用，每次间隔MIN_CALL_INTERVAL秒。
    比并行更可靠，避免限流失败。
    """
    results = []
    for i, prompt in enumerate(prompts):
        result = api_call(prompt, max_tokens, system_prompt)
        results.append(result)
        
        # 间隔保护
        if i < len(prompts) - 1:
            time.sleep(MIN_CALL_INTERVAL)
    
    return results

def get_usage_report():
    """获取API使用报告"""
    stats = tracker.get_stats()
    return {
        "timestamp": datetime.now(BJT).isoformat(),
        "strategy": {
            "max_parallel": MAX_PARALLEL,
            "max_calls_per_minute": MAX_CALLS_PER_MINUTE,
            "max_tokens_per_call": MAX_TOKENS_PER_CALL,
            "min_call_interval": MIN_CALL_INTERVAL
        },
        "usage": stats
    }

if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        print("测试API策略...")
        result = api_call("用一句话回答：1+1=?", max_tokens=50)
        print(f"结果: {'✓' if result['success'] else '✗'}")
        print(f"内容: {result['content'][:100]}")
        print(f"Token: {result['tokens']}")
        print(f"延迟: {result['latency_ms']}ms")
        print(f"尝试: {result['attempt']}次")
        
        stats = get_usage_report()
        print(f"\n使用统计:")
        print(f"  总调用: {stats['usage']['total_calls']}")
        print(f"  总token: {stats['usage']['total_tokens']}")
        print(f"  错误率: {stats['usage']['error_rate']*100:.1f}%")
    
    elif "--batch" in sys.argv:
        prompts = [
            "用一句话：光爱是什么？",
            "用一句话：零是什么？",
            "用一句话：真元集群是什么？"
        ]
        print(f"批量测试({len(prompts)}个, 并行{min(MAX_PARALLEL, len(prompts))}个)...")
        results = parallel_call(prompts, max_tokens=50)
        for i, r in enumerate(results):
            print(f"  [{i+1}] {'✓' if r['success'] else '✗'} {r['content'][:50]}")
    
    else:
        stats = get_usage_report()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
