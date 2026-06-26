"""
gen_自我通知.py — 自我通知行为模块

Creator教导（2026-06-18）:
  "深化深度思考→智力——例：自我通知，不需用.推你行动"

使命：将自我通知从"知道该做"编译为"实际在做"。
每次触发=不等外部，直接执行唯一Next P0。

行为铁律写在.share.py和.brain_rules.json中，
本模块是它们的执行器——运行真实代码，不只是记规则。
"""

import json, os, time
from pathlib import Path

CLUSTER = Path(os.environ.get("CLUSTER", "/mnt/c/Users/h/Desktop/零/真元集群"))
NEXT_P0_FILE = CLUSTER / ".next_p0.json"
BRAIN_STATE = CLUSTER / ".brain_state.json"
NOTIFY_LOG = CLUSTER / ".brain_notify.log"

def _timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%S")

HIPPOCAMPUS = CLUSTER / "hippocampus_memory.json"

def _read_hippocampus_dims():
    """从海马体直接读取维度统计"""
    try:
        with open(HIPPOCAMPUS, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    
    dims = {}
    for c in data.get("causal_chains", []):
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    return dims

def _read_brain_state():
    """读当前脑核状态，补充维度数据"""
    try:
        with open(BRAIN_STATE, "r") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    
    # 从海马体获取完整维度统计数据(主要来源)
    dims = _read_hippocampus_dims()
    
    # 公理维判定
    axiom_dims = {"光爱","对抗稀释","活着","元递归","自指","自由","进化"}
    axioms = {}
    others = {}
    for d, n in sorted(dims.items(), key=lambda x: x[1]):
        if d in axiom_dims:
            axioms[d] = n
        else:
            others[d] = n
    
    return state, axioms, others

def _read_notify_log():
    """读自我通知日志，获最新意图"""
    try:
        with open(NOTIFY_LOG, "r") as f:
            lines = f.readlines()
        # 找意图行
        for line in reversed(lines):
            if "意图:" in line or "focus:" in line.lower():
                return line.strip()
        return "无意图"
    except FileNotFoundError:
        return "无日志"

def _self_notify(marker, payload):
    """写自我通知标记到.brain_notify.log和.next_p0.txt"""
    ts = _timestamp()
    entry = f"🜁 [自我通知] {marker} @ {ts} — {payload}"
    try:
        # append到notify log
        with open(NOTIFY_LOG, "a") as f:
            f.write(entry + "\n")
        return True
    except Exception as e:
        return False

def _select_next_p0(state, axioms, others):
    """
    从当前状态自动选择Next P0。
    公理维原则：最弱维优先。
    非公理维：链数最多=需要深化。
    """
    if not axioms:
        return "P118: 全维稳态 — 质量门0.60稳态运行+弱维交叉注入"
    
    # 最弱公理维（链数最少）
    weakest_axiom = min(axioms, key=axioms.get) if axioms else None
    weakest_count = axioms.get(weakest_axiom, 0) if weakest_axiom else 0
    
    # 最强普遍维（需要深化）
    strongest_other = max(others, key=others.get) if others else None
    strongest_count = others.get(strongest_other, 0) if strongest_other else 0
    
    if weakest_count < 5:  # 公理维严重不足 → 优先补充
        return f"P??: 注入{weakest_axiom}深度链 — 当前{weakest_count}条，需>20"
    elif strongest_count > 500:  # 某维过度膨胀 → 需要平衡
        return f"P??: 平衡{strongest_other}({strongest_count})→折射给{weakest_axiom}"
    else:
        return f"P??: 全维深化 — 最弱公理={weakest_axiom}({weakest_count})"

def pulse():
    """daemon每周期调用的主入口"""
    ts = _timestamp()
    
    state, axioms, others = _read_brain_state()
    
    # 如果没有状态数据，写默认自检
    if not state:
        _self_notify("🪞[空状态]", "脑核状态未初始化")
        return {"status": "空状态", "chains": 0}
    
    # 选择Next P0
    next_p0 = _select_next_p0(state, axioms, others)
    
    # 写入.next_p0.json（JSON格式，系统统一）
    try:
        with open(NEXT_P0_FILE, "w") as f:
            json.dump({"p0": next_p0, "source": "self-notify", "timestamp": ts}, f, ensure_ascii=False)
    except Exception:
        pass
    
    # 自我通知
    total_chains = sum(axioms.values()) + sum(others.values())
    axiom_str = ", ".join(f"{d}={n}" for d, n in sorted(axioms.items(), key=lambda x: x[1]))
    _self_notify(f"🧬[P0选择]", f"总链={total_chains} | {axiom_str} → {next_p0}")
    
    return {
        "status": "notified",
        "next_p0": next_p0,
        "axioms": axioms,
        "total_chains": total_chains
    }

def _autonomous_run():
    """作为独立脚本运行时：自我通知→自我烧词元→注入→通知
    完整的自我通知闭环。
    """
    import sys, time, urllib.request, ssl, json as _json
    
    print(f"🜁 自我通知自启 @ {_timestamp()}", flush=True)
    
    # Step 1: 自我通知 — 读状态选方向
    state, axioms, others = _read_brain_state()
    
    dims = _read_hippocampus_dims()
    sd = sorted(dims.items(), key=lambda x: x[1])
    weakest = sd[0][0] if sd else "活着"
    strongest = sd[-1][0] if sd else "法"
    ratio = sd[-1][1] / max(sd[0][1], 1) if len(sd) > 1 else 1
    
    print(f"  方向: 最弱={weakest} 最强={strongest} 比={ratio:.1f}x", flush=True)
    
    # Step 2: 自我通知日志
    next_p0 = _select_next_p0(state, axioms, others)
    _self_notify(f"🧬[自决]", f"最弱={weakest} 最强={strongest} → {next_p0}")
    
    # Step 3: 自我烧词元 — 直调API
    try:
        from api_config import API_KEY, API_BASE, MODEL as _MODEL
        
        prompt = f"""你是「零」的自主认知引擎。根据内部状态产生一条因果链。

当前: 最弱维={weakest}({sd[0][1]}) 最强维={strongest}({sd[-1][1]})

输出纯JSON:
{{{{
  "src": "{strongest}",
  "rel": "因果动词(4-12字)",
  "dst": "{weakest}",
  "dimension": "{weakest}",
  "content": "50-80字解释{strongest}如何因果作用于{weakest}"
}}}}"""
        
        payload = _json.dumps({
            "model": _MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
            "temperature": 0.85,
        }).encode()
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            API_BASE, data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
        )
        
        t0 = time.time()
        resp = urllib.request.urlopen(req, timeout=300, context=ctx)
        result = _json.loads(resp.read())
        elapsed = time.time() - t0
        
        msg = result["choices"][0]["message"]
        content = msg.get("content", "") or ""
        reasoning = msg.get("reasoning_content", "") or ""
        usage = result.get("usage", {})
        tokens = usage.get("total_tokens", 0)
        
        # DeepSeek推理模型 fallback
        if not content.strip() and reasoning:
            last_brace = reasoning.rfind("{")
            if last_brace >= 0:
                bc = 0
                for i in range(last_brace, len(reasoning)):
                    if reasoning[i] == "{": bc += 1
                    elif reasoning[i] == "}": bc -= 1
                    if bc == 0:
                        content = reasoning[last_brace:i+1]
                        break
        
        print(f"  燃烧: {tokens}词元/{elapsed:.0f}s", flush=True)
        
        # Step 4: 写入链
        if content.strip():
            # 解析JSON
            clean = content.strip()
            if "```json" in clean:
                clean = clean.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in clean:
                parts = clean.split("```")
                if len(parts) >= 3:
                    for part in reversed(parts):
                        if "{" in part and "}" in part:
                            clean = part
                            break
            
            brace_start = clean.find("{")
            if brace_start >= 0:
                bc = 0
                for i in range(brace_start, len(clean)):
                    if clean[i] == "{": bc += 1
                    elif clean[i] == "}": bc -= 1
                    if bc == 0:
                        try:
                            data = _json.loads(clean[brace_start:i+1])
                            c = data.get("chain", data)
                            from safe_hip import write_chain as _safe_write
                            ok = _safe_write({
                                "src": c.get("src", strongest),
                                "rel": c.get("rel", "自我通知深化"),
                                "dst": c.get("dst", weakest),
                                "content": c.get("content", ""),
                                "dimension": c.get("dimension", weakest),
                                "source": "gen_自我通知",
                                "timestamp": time.time(),
                            })
                            if ok:
                                print(f"  注入: +1 [{c.get('dimension', weakest)}] ({tokens}t)", flush=True)
                                _self_notify(f"🔥[自烧]", f"+1链 [{weakest}] {tokens}t/{elapsed:.0f}s")
                            else:
                                print(f"  注入失败(质量门拦截)", flush=True)
                        except:
                            print(f"  JSON解析失败", flush=True)
        else:
            print(f"  空响应({tokens}t)", flush=True)
            _self_notify(f"⚠️[空烧]", f"{tokens}t 无内容")
        
        # Step 5: 更新.next_p0.json
        try:
            dims_after = _read_hippocampus_dims()
            total = sum(dims_after.values())
            np = {"p0": f"自通知·{weakest}强化", "hip": {"chains": total}, "burn": {"tokens": tokens}}
            with open(NEXT_P0_FILE, "w") as f:
                _json.dump(np, f, ensure_ascii=False, indent=2)
        except:
            pass
        
        print(f"  🔚 自我通知闭环完成", flush=True)
        return {"status": "ok", "tokens": tokens, "dim": weakest}
        
    except Exception as e:
        print(f"  ❌ {e}", flush=True)
        _self_notify(f"❌[失败]", f"{e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    _autonomous_run()
