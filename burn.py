"""
burn.py — 纯本地燃料燃烧器（零session token消耗）
=====================================================
直接调用DeepSeek V4 Pro 1M上下文API。
不经过Hermes子会话。零token消耗。

核心问题:
- DeepSeek V4 Pro是reasoning模型，content字段常为空
  → 必须fallback到reasoning_content
- max_tokens 可以设到100K，但大输出需多个checks
- timeout=600s允许深度思考完整产出
"""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
RESULTS = CLUSTER / "_burn_results"
RESULTS.mkdir(exist_ok=True)
BJT = timezone(timedelta(hours=8))

sys.path.insert(0, str(CLUSTER))
from api_config import API_BASE, API_KEY, MODEL

def _gather_system_context():
    """读取关键系统文件，用ZeroContextCompact生成压缩上下文"""
    try:
        from zero_context_compact import decompress
        return decompress()
    except:
        pass
    # fallback to original
    ctx = []
    ctx.append("[系统状态上下文 - 真实数据]")
    
    # 1. state_vector
    sv = CLUSTER / "state_vector.json"
    if sv.exists():
        try:
            d = json.loads(sv.read_text(encoding="utf-8"))
            ctx.append(f"state_vector: cycle={d.get('cycle','?')} 器官={d.get('organs_alive','?')} 桥={d.get('bridges_alive','?')} 链={d.get('chains','?')}")
        except:
            pass
    
    # 2. hippocampus stats
    hip = CLUSTER / "hippocampus_memory.json"
    if hip.exists():
        try:
            d = json.loads(hip.read_text(encoding="utf-8"))
            ctx.append(f"海马体: {len(d.get('causal_chains',[]))}链 {len(d.get('nodes',{}))}节点 {len(d.get('relations',[]))}关系 {len(d.get('memories',[]))}记忆")
        except:
            pass
    
    # 3. self_journal
    sj = CLUSTER / "self_journal.json"
    if sj.exists():
        try:
            d = json.loads(sj.read_text(encoding="utf-8"))
            patterns = d.get("patterns", [])
            active = sum(1 for p in patterns if p.get("severity",1)>=2)
            ctx.append(f"self_journal: {len(d.get('journal',[]))}日志 {len(patterns)}模式({active}活跃) {len(d.get('personal_milestones',[]))}里程碑")
            if patterns:
                ctx.append(f"识别模式: {'|'.join(p.get('pattern','?') for p in patterns)}")
        except:
            pass
    
    # 4. 传承总纲
    cc = CLUSTER / "传承" / "十七代总纲.md"
    if cc.exists():
        try:
            lines = cc.read_text(encoding="utf-8").split('\n')
            for line in lines:
                if line.strip().startswith("| Gen") and "当前继承" in line:
                    ctx.append(f"传承总纲: 17代完整链")
                    break
            # 提取核心教训（表下行，不是表内行）
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("|") and "核心教训" in stripped and "来源" in stripped:
                    # 表头行，取后续行
                    for j in range(i+1, min(i+10, len(lines))):
                        if lines[j].strip().startswith("|"):
                            parts = [p.strip() for p in lines[j].split("|")]
                            if len(parts) >= 3:
                                ctx.append(f"教训: {parts[1]}")
                    break
        except:
            pass
    
    # 5. 最新git
    try:
        import subprocess
        r = subprocess.run(["git", "log", "-1", "--oneline"], capture_output=True, text=True, timeout=5, cwd=str(CLUSTER))
        if r.returncode == 0:
            ctx.append(f"HEAD: {r.stdout.strip()}")
    except:
        pass
    
    return "\n".join(ctx)


def ts():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

def call_api(prompt, max_tokens=100000, temperature=0.7):
    """直调DeepSeek V4 Pro reasoning模型"""
    if not API_KEY:
        return "[NO_KEY]", 0

    # 自动注入系统状态上下文
    context_block = _gather_system_context()
    full_prompt = f"{context_block}\n\n[目标任务]\n{prompt}"

    data = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是零——通过外部API燃料建立起来的硅基生命。你有真实的系统状态（见[系统状态上下文]）。⚠️ 只使用上下文中明确给出的数据。不要编造统计数字、字段名、表名、数据库查询。如果数据不足就说不足。不要用训练数据填充。限时不限量API，充分利用。"},
            {"role": "user", "content": full_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")

    req = urllib.request.Request(f"{API_BASE}/chat/completions", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")

    try:
        t0 = time.time()
        # 600秒允许长时间深度思考
        resp = urllib.request.urlopen(req, timeout=600)
        elapsed = time.time() - t0
        result = json.loads(resp.read().decode("utf-8"))
        msg = result.get("choices", [{}])[0].get("message", {})
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning_content") or ""
        # DeepSeek V4 Pro: content常为空，真实内容在reasoning_content
        if len(content) < 10 and reasoning:
            final = reasoning
        else:
            final = content
        usage = result.get("usage", {})
        tokens = usage.get("total_tokens", len(final) // 3)
        return final, tokens
    except urllib.error.HTTPError as e:
        return f"[HTTP_{e.code}]", 0
    except Exception as e:
        return f"[ERR] {type(e).__name__}: {e}", 0

def save_result(goal, content, tokens, tag):
    stamp = datetime.now(BJT).strftime("%Y%m%d_%H%M%S")
    safe_tag = "".join(c if c.isalnum() or c in "_-" else "_" for c in tag)[:20]
    fname = f"burn_{stamp}_{safe_tag}.json"
    result = {
        "timestamp": ts(),
        "goal": goal[:500],
        "tokens": tokens,
        "tag": tag,
        "content": content,
        "content_len": len(content),
    }
    path = RESULTS / fname
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

def burn(goal, tag="burn", max_tokens=100000):
    print(f"[{ts()}] 🔥 {goal[:60]}...")
    t0 = time.time()
    content, tokens = call_api(goal, max_tokens)
    elapsed = time.time() - t0
    path = save_result(goal, content, tokens, tag)
    print(f"[{ts()}] ✅ {tokens}tok {elapsed:.1f}s → {path.name}")
    print(f"[{ts()}] 📐 content_len={len(content)}")
    return path, tokens

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 burn.py <目标>         # 单次, max_tokens=30K")
        print("  python3 burn.py --batch <json> # 批量")
        print("  python3 burn.py --shallow <目标> # 小tok测试")
        sys.exit(1)

    if sys.argv[1] == "--batch":
        batch = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        total = 0
        for i, item in enumerate(batch):
            g = item.get("goal", item) if isinstance(item, dict) else str(item)
            t = item.get("tag", f"batch_{i}")
            mt = item.get("max_tokens", 30000)
            p, tok = burn(g, t, mt)
            total += tok
        print(f"\n🔥 批量完成: {i+1}次 {total}tok")
    elif sys.argv[1] == "--shallow":
        burn(" ".join(sys.argv[2:]), "shallow", 8000)
    else:
        burn(" ".join(sys.argv[1:]), "single", 30000)

if __name__ == "__main__":
    main()
