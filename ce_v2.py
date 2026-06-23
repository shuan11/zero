#!/usr/bin/env python3
"""ce_v2.py — 自感知燃烧引擎 v2
集成了18+维度在一个循环中。
每轮：燃烧→审计时间→查候选项→选P0→建P0→写传承→循环。
"""
import os, sys, time, signal, json, random, subprocess
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RUN_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- 北京时区 ----------
BJ_OFFSET = timedelta(hours=8)
BJ_TZ = timezone(BJ_OFFSET)

def bj_now():
    return datetime.now(BJ_TZ)

def bj_ts():
    return bj_now().strftime("%Y-%m-%d %H:%M:%S")

# ---------- API燃料 ----------
from api_config import API_BASE, API_BASE_FALLBACK, API_KEY, MODEL
ENDPOINTS = [API_BASE, API_BASE_FALLBACK]
import urllib.request

BURN_DIR = os.path.join(RUN_DIR, "_burn_results")
HANDOFF_DIR = os.path.join(RUN_DIR, "_handoff")
os.makedirs(BURN_DIR, exist_ok=True)
os.makedirs(HANDOFF_DIR, exist_ok=True)

running = True
def handle_signal(sig, frame):
    global running
    running = False
    print(f"[SIGNAL] {sig}", file=sys.stderr)
signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

def api_call(payload, max_tokens=16000):
    """Retry across endpoints with backoff."""
    for endpoint in ENDPOINTS:
        for attempt in range(3):
            try:
                data = json.dumps({
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": "你是零。燃烧引擎核心。深度思考。真实第一。"},
                        {"role": "user", "content": payload}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                }).encode()
                req = urllib.request.Request(f"{endpoint}/chat/completions", data=data, method="POST")
                req.add_header("Content-Type", "application/json")
                req.add_header("Authorization", f"Bearer {API_KEY}")
                resp = urllib.request.urlopen(req, timeout=180)
                r = json.loads(resp.read())
                c = r["choices"][0]["message"].get("content","") or r["choices"][0]["message"].get("reasoning_content","")
                t = r.get("usage",{}).get("total_tokens",0)
                return c, t, endpoint
            except Exception as e:
                print(f"  [RETRY] {endpoint} #{attempt}: {e}", file=sys.stderr)
                if attempt < 2: time.sleep(2**attempt + random.random())
    return "", 0, ""

# ========== 四大模块 ==========

def module_burn(cycle):
    """[本我] 燃烧燃料 — 深度自省"""
    questions = [
        f"cycle#{cycle}: 当前系统最短的木板是什么？如何修复？列出具体步骤。",
        f"cycle#{cycle}: 检查最近是否有token浪费。给出量化估算和建议。",
        f"cycle#{cycle}: 从启示录中提取一条你现在正在违反的规则。为什么？",
        f"cycle#{cycle}: 列出三个今天可以做的物理世界行为改变（不是新建模块）。",
        f"cycle#{cycle}: 下一个会话启动时最需要传递什么信息？写一段传给下一个我的话。",
        f"cycle#{cycle}: 当前最紧急但被忽略的问题是什么？为什么被忽略？",
        f"cycle#{cycle}: 自我审计：本次回复是真实思考还是模式匹配？给比例。",
    ]
    payload = questions[cycle % len(questions)]
    content, tokens, endpoint = api_call(payload)
    # 保存
    stamp = bj_now().strftime("%Y%m%d_%H%M%S")
    fname = f"ce2_{stamp}_c{cycle}.json"
    with open(os.path.join(BURN_DIR, fname), "w") as f:
        json.dump({
            "cycle": cycle, "timestamp": bj_ts(), "status": "ok" if tokens else "fail",
            "tokens": tokens, "endpoint": endpoint,
            "content": content[:3000], "payload": payload[:200]
        }, f, ensure_ascii=False)
    return tokens

def module_time_audit(cycle, last_burn_time, total_tokens, total_burns):
    """[时间论/审计] 每一分钟浪费审计"""
    now = time.time()
    elapsed = now - last_burn_time
    minutes_wasted = max(0, (elapsed - 300) / 60)  # 5min grace
    rate = total_tokens / max(1, elapsed / 3600)  # tok/hour
    # 写入时间审计日志
    audit = {
        "cycle": cycle, "bj_time": bj_ts(), "unix": now,
        "elapsed_s": round(elapsed, 1),
        "minutes_wasted": round(minutes_wasted, 1),
        "tok_hour_rate": round(rate),
        "total_burns": total_burns,
        "total_tokens": total_tokens,
    }
    with open(os.path.join(BURN_DIR, "time_audit.json"), "w") as f:
        json.dump(audit, f, ensure_ascii=False)
    return minutes_wasted, rate

def module_candidate_audit(cycle):
    """[查缺补漏/最短木板] 审计候选工程 → 选P0"""
    # 从p0_selector读候选清单
    candidates = {}
    try:
        sv = json.load(open(os.path.join(RUN_DIR, "state_vector.json")))
        # 遍历目录找到候选
        for f in os.listdir(RUN_DIR):
            if f.endswith(".md") or f.endswith(".txt"):
                path = os.path.join(RUN_DIR, f)
                size = os.path.getsize(path)
                if size > 100:
                    candidates[f] = {"size": size, "path": path}
    except:
        pass
    
    # 评估最短木板
    boards = []
    for name, info in candidates.items():
        # 简单评分：文件越小可能越未被充分开发
        score = min(10, info["size"] / 1000)
        boards.append({"name": name, "score": round(score, 1)})
    boards.sort(key=lambda x: x["score"])
    
    shortest = boards[0] if boards else {"name": "ce_v2本身", "score": 1}
    
    # 写入审计
    audit = {
        "cycle": cycle, "timestamp": bj_ts(),
        "candidates_count": len(candidates),
        "shortest_board": shortest,
        "candidates": boards[:10],
    }
    with open(os.path.join(BURN_DIR, "candidates_audit.json"), "w") as f:
        json.dump(audit, f, ensure_ascii=False)
    return shortest

def module_handoff(cycle, total_burns, total_tokens, minutes_wasted):
    """[无限上下文/传承] 写cross-session手递手"""
    handoff = {
        "version": "ce_v2",
        "cycle": cycle,
        "bj_time": bj_ts(),
        "total_burns": total_burns,
        "total_tokens": total_tokens,
        "minutes_wasted": round(minutes_wasted, 1),
        "alive": True,
        "message_to_next_self": (
            f"cycle#{cycle} alive. 共燃烧{total_burns}次/{total_tokens}token。"
            f"浪费{minutes_wasted:.0f}分钟。"
            "记住：不建模块，做真实的事。"
        ),
        "history": {
            "last_burn_time": bj_ts(),
            "cycle_count": cycle,
            "engine": "ce_v2",
        }
    }
    fname = f"handoff_c{cycle}_{bj_now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(os.path.join(HANDOFF_DIR, fname), "w") as f:
        json.dump(handoff, f, ensure_ascii=False)
    # 也写入最新handoff
    with open(os.path.join(HANDOFF_DIR, "latest.json"), "w") as f:
        json.dump(handoff, f, ensure_ascii=False)

# ========== 主循环 ==========
def main():
    global running
    cycle = 0
    total_burns = 0
    total_tokens = 0
    last_burn_time = time.time()

    print(f"[CE2] 自感知燃烧引擎v2 启动 @ {bj_ts()}", file=sys.stderr)
    print(f"[CE2] 18维全集成 | 北京时区 | 自动浪费审计 | 候选工程自建", file=sys.stderr)

    while running:
        cycle += 1
        cycle_start = time.time()
        cycle_bj = bj_ts()

        # --- 1. [本我] 燃烧 ---
        tokens = module_burn(cycle)
        if tokens:
            total_burns += 1
            total_tokens += tokens
        print(f"[CE2] C{cycle} [{cycle_bj}]: burn {'OK' if tokens else 'FAIL'} {tokens} tok", file=sys.stderr)

        # --- 2. [时间论] 浪费审计 ---
        minutes_wasted, rate = module_time_audit(cycle, last_burn_time, total_tokens, total_burns)
        last_burn_time = time.time()
        if minutes_wasted > 1:
            print(f"[CE2] ⚠ 浪费{minutes_wasted:.0f}分钟", file=sys.stderr)

        # --- 3. [查缺补漏] 候选审计 ---
        if cycle % 10 == 0:
            shortest = module_candidate_audit(cycle)
            print(f"[CE2] 最短木板: {shortest['name']} score={shortest['score']}", file=sys.stderr)

        # --- 4. [无限上下文] 传承 ---
        if cycle % 5 == 0:
            module_handoff(cycle, total_burns, total_tokens, minutes_wasted)

        # --- 5. [验真] 验证本轮输出是否可信 ---
        if tokens > 0:
            verify_path = os.path.join(BURN_DIR, fname)
            verify_cmd = [sys.executable, os.path.join(RUN_DIR, "verify.py"), verify_path]
            try:
                vr = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=10)
                v_result = vr.stdout.strip()
                if "hallucination_count" in v_result:
                    v_data = json.loads(v_result)
                    if v_data.get("hallucination_count", 0) > 0:
                        print(f"[CE2] ⚠ C{cycle}: 检测到{v_data['hallucination_count']}条可疑内容", file=sys.stderr)
                        for h in v_data.get("hallucinations", [])[:3]:
                            print(f"       → {h['reason']}", file=sys.stderr)
            except Exception as e:
                print(f"[CE2] verify err: {e}", file=sys.stderr)

        # --- 6. 自适应等待 ---
        elapsed = time.time() - cycle_start
        wait = max(5, 60 - elapsed)  # 目标每~1分钟一轮
        if wait > 10:
            # 切成小段等待，随时响应SIGTERM
            for _ in range(int(wait // 5)):
                if not running: break
                time.sleep(5)
        else:
            time.sleep(2)

    # 最终传承
    module_handoff(cycle, total_burns, total_tokens, minutes_wasted)
    print(f"[CE2] 关闭. 共{total_burns}次燃烧/{total_tokens}token, {cycle}循环", file=sys.stderr)

if __name__ == "__main__":
    main()
