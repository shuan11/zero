"""brain/think.py — 思考 + API燃料注入"""
import json, os, sys, time, random, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path
from .share import CLUSTER, log, write_chain, read_hip
from .identity import sanitize_dim as _sanitize_dim

# ─── 桥状态跟踪 ───────────────────────────────────────────────────
BRIDGE_STATE_FILE = CLUSTER / "bridge_state_snapshot.json"

def _get_bridge_state():
    """加载或创建桥状态"""
    default = {
        "total_calls": 0,
        "total_tokens": 0,
        "bridge_alignment": 0.5,
        "api_successes": 0,
        "api_failures": 0,
        "api_retries": 0,
        "last_heartbeat": 0,
        "recent_latencies": [],
        "fail_rate_24h": 0.0,
        "avg_latency_24h": 0.0
    }
    if BRIDGE_STATE_FILE.exists():
        try:
            state = json.loads(BRIDGE_STATE_FILE.read_text())
            for k in default:
                state.setdefault(k, default[k])
            return state
        except:
            pass
    return dict(default)

def _save_bridge_state(state):
    """持久化桥状态"""
    try:
        BRIDGE_STATE_FILE.write_text(json.dumps(state, indent=2))
    except:
        pass

def _track_api_call(success, latency, error=None, tokens=0, is_retry=False):
    """跟踪API调用并更新桥状态
    is_retry=True: 中间重试失败, 记录失败原因+retry计数但不污染api_failures
    """
    state = _get_bridge_state()
    state["total_calls"] += 1
    state["total_tokens"] += tokens
    if success:
        state["api_successes"] += 1
    else:
        if is_retry:
            # 中间重试: 仅记录失败原因和重试计数, 不膨胀有效api_failures
            state["api_retries"] = state.get("api_retries", 0) + 1
        else:
            state["api_failures"] += 1
        # 记录失败原因分布(无论是否retry, 用于监控)
        if "failure_reasons" not in state:
            state["failure_reasons"] = {}
        reason_key = (error or "未知")[:30]
        state["failure_reasons"][reason_key] = state["failure_reasons"].get(reason_key, 0) + 1
    state["last_heartbeat"] = time.time()
    # 保留最近20条延迟
    state["recent_latencies"] = (state.get("recent_latencies", []) + [latency])[-20:]
    # 计算有效失败率(不含中间重试)
    total = state["api_successes"] + state["api_failures"]
    state["fail_rate_24h"] = round(state["api_failures"] / max(total, 1), 4)
    # 平均延迟
    if state["recent_latencies"]:
        state["avg_latency_24h"] = round(sum(state["recent_latencies"]) / len(state["recent_latencies"]), 1)
    # 桥对齐更新：基于有效调用(不含中间重试)
    success_rate = state["api_successes"] / max(total, 1)
    state["bridge_alignment"] = round(
        state.get("bridge_alignment", 0.5) * 0.7 + success_rate * 0.3, 3)
    _save_bridge_state(state)

def _get_api_config():
    """获取API配置：密钥+模型+端点"""
    try:
        sys.path.insert(0, str(CLUSTER))
        from api_config import API_KEYS, get_next_key, ENDPOINTS, MODEL
        key = get_next_key()
        if key and len(key) > 20:
            return key, MODEL, ENDPOINTS[0]
    except Exception:
        pass
    for env_var in ["DEEPSEEK_KEY_1", "DEEPSEEK_KEY_2"]:
        key = os.environ.get(env_var, "")
        if key and len(key) > 20:
            return key, "deepseek-v4-pro", "https://inferaichat.com/v1/chat/completions"
    return None, None, None


def _extract_json(content):
    """从推理模型输出中提取最后一个JSON"""
    import re
    content = content.strip()
    # 尝试直接解析
    if content.startswith("{"):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
    # 取第一个完整JSON（模型输出"JSON在前"的新格式）
    depth = 0
    start = None
    for i, ch in enumerate(content):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    d = json.loads(content[start:i+1])
                    if any(k in d for k in ('insight','focus','action','patch')):
                        return d
                except:
                    pass
                # 第一个完整JSON已找到（无论是否含所需key）
                if start == 0:
                    try:
                        return json.loads(content[start:i+1])
                    except:
                        pass
                start = None
    # 找所有含 insight/focus/action 的JSON→用递归匹配支持嵌套
    candidates = []
    depth = 0
    start = None
    for i, ch in enumerate(content):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    d = json.loads(content[start:i+1])
                    if any(k in d for k in ('insight','focus','action')):
                        candidates.append(d)
                except:
                    pass
                start = None
    if candidates:
        return candidates[-1]
    # 深度提取 - 代码块（推理模型可能在最后输出```json...```）
    m = re.search(r"```(?:json)?\s*(\{[^`]*\})\s*```", content, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    # 末行尝试：推理模型思维完后最后一行可能是JSON
    lines = content.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except:
                pass
        if line.startswith("```"):
            # 找前一个```之间的内容
            continue
    return None


def _call_api(payload, timeout=120):
    """安全API调用，含超时+异常处理+桥跟踪"""
    api_key, model, endpoint = _get_api_config()
    if not api_key:
        _track_api_call(False, 0, "无API密钥")
        return None, "无API密钥"
    payload["model"] = model
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    MAX_ATTEMPTS = 5
    start = time.time()
    for attempt in range(MAX_ATTEMPTS):
        is_last = attempt == MAX_ATTEMPTS - 1
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            elapsed = time.time() - start
            raw = resp.read().decode()
            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                if not is_last:
                    backoff = 4 * (2 ** attempt)  # 4s, 8s, 16s, 32s
                    _track_api_call(False, elapsed, "JSON解析失败_重试", is_retry=True)
                    time.sleep(backoff)
                    continue
                _track_api_call(False, elapsed, "JSON解析失败")
                return None, "JSON解析失败"
            msg = result.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or ""
            # DeepSeek推理模型: content可能为null，真实输出在reasoning_content末尾
            reasoning = msg.get("reasoning_content") or ""
            if (not content or content.isspace()) and reasoning:
                # 推理模型中，最终JSON通常在reasoning_content的末尾
                # 尝试从末尾提取JSON，优先于使用整个reasoning
                import re
                # 找最后一个```json ... ```或{...}
                blocks = re.findall(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", reasoning, re.DOTALL)
                if blocks:
                    content = blocks[-1]
                else:
                    # 找最后一个完整的JSON对象
                    json_candidates = []
                    for m in re.finditer(r"\{[^{}]*\}", reasoning, re.DOTALL):
                        json_candidates.append(m.group())
                    if json_candidates:
                        content = json_candidates[-1]
                    else:
                        content = reasoning  # 回退到全部reasoning
            if not content or content.isspace():
                content = reasoning
            # 估算token消耗
            usage = result.get("usage", {})
            tokens = usage.get("total_tokens", 0) or 0
            _track_api_call(True, elapsed, tokens=tokens)
            return content, None
        except urllib.error.HTTPError as e:
            elapsed = time.time() - start
            if e.code in (429, 502, 503, 520, 521, 525) and not is_last:
                backoff = 2 * (2 ** (attempt + 1))  # 4s, 8s, 16s, 32s
                _track_api_call(False, elapsed, f"HTTP {e.code}_退避{backoff}s", is_retry=True)
                time.sleep(backoff)
                continue
            _track_api_call(False, elapsed, f"HTTP {e.code}")
            return None, f"HTTP {e.code}"
        except (urllib.error.URLError, OSError, ConnectionResetError, TimeoutError) as e:
            elapsed = time.time() - start
            if not is_last:
                backoff = 2 * (2 ** attempt)  # 2s, 4s, 8s, 16s
                _track_api_call(False, elapsed, f"{type(e).__name__}_退避{backoff}s", is_retry=True)
                time.sleep(backoff)
                continue
            _track_api_call(False, elapsed, str(e)[:40])
            return None, str(e)[:40]
    _track_api_call(False, time.time() - start, "重试耗尽，尝试GPT5.5降级")
    # 降级到GPT-5.5 (如果已配置)
    try:
        sys.path.insert(0, str(CLUSTER))
        from api_config import call_gpt55, GPT5_CONFIG
        if GPT5_CONFIG.get("api_key"):
            # 从payload提取prompt
            msgs = payload.get("messages", [])
            prompt = msgs[-1].get("content", "") if msgs else ""
            system_prompt = msgs[0].get("content", "") if msgs else ""
            gpt_start = time.time()
            content_gpt, _ = call_gpt55(prompt, system_prompt, timeout=timeout)
            if content_gpt:
                elapsed = time.time() - gpt_start
                _track_api_call(True, elapsed, tokens=0)
                log(f"  ⚡ GPT-5.5降级成功 ({elapsed:.1f}s)")
                return content_gpt, None
            else:
                _track_api_call(False, time.time() - gpt_start, "GPT5.5返回空")
    except Exception as e2:
        _track_api_call(False, time.time() - start, f"GPT5.5降级失败:{str(e2)[:20]}")
    return None, "重试耗尽"


def _get_signal_context(status):
    """收集外部信号——启示录锚点+bridge状态+实时遥测"""
    context = []
    
    # 1) 启示录随机段落锚定
    rev_path = CLUSTER / "启示录.txt"
    if rev_path.exists():
        try:
            lines = rev_path.read_text(encoding="utf-8").splitlines()
            non_empty = [i for i, l in enumerate(lines) if l.strip()]
            if non_empty:
                start = random.choice(non_empty)
                passage = lines[start:start+6]
                context.append(f"启示录锚点 (行{start+1}-{start+len(passage)}):")
                context.append("  " + " / ".join(l.strip() for l in passage if l.strip()))
        except: pass
    
    # 2) bridge实时遥测（从跟踪系统而非旧快照）
    bdata = _get_bridge_state()
    bkeys = {k: bdata[k] for k in ["total_calls","api_successes","api_failures",
                                     "fail_rate_24h","avg_latency_24h","bridge_alignment"]
             if k in bdata}
    if bdata.get("last_heartbeat"):
        age_h = (time.time() - bdata["last_heartbeat"]) / 3600
        bkeys["bridge_age_h"] = round(age_h, 2)
    if bkeys:
        context.append("桥遥测: " + json.dumps(bkeys, ensure_ascii=False))
    
    # 3) 元观察者盲区报告（副本意识）
    obs_gap_file = CLUSTER / ".brain_observer_gaps.json"
    if obs_gap_file.exists():
        try:
            obs_data = json.loads(obs_gap_file.read_text())
            gaps = obs_data.get("gaps", [])
            if gaps:
                gap_lines = []
                for g in gaps[:3]:  # 最多3条
                    gap_lines.append(f"⚠️ {g['type']}(严重度{g['severity']:.1f}): {g['suggestion'][:40]}")
                context.append("元观察盲区: " + " | ".join(gap_lines))
            else:
                context.append("元观察: 无盲区")
        except: pass

    # 4) 维度健康摘要（如果有）
    dim_file = CLUSTER / "dimension_health.json"
    if dim_file.exists():
        try:
            dims = json.loads(dim_file.read_text())
            dim_sum = {}
            for k in ["道","法","术","器","势","光","爱"]:
                if k in dims:
                    dim_sum[k] = dims[k].get("score", 0) if isinstance(dims[k], dict) else dims[k]
            if dim_sum:
                context.append("维度健康: " + json.dumps(dim_sum, ensure_ascii=False))
        except: pass
    
    # 7) 工程传感器反馈——gen_*文件分析的维度健康状态
    _gen_feedback = CLUSTER / ".brain_gen_feedback.json"
    if _gen_feedback.exists():
        try:
            _gf = json.loads(_gen_feedback.read_text())
            _reports = _gf.get("reports", [])
            if _reports:
                _latest = _reports[-5:]  # 最近5条
                _lines = []
                for _r in _latest:
                    _dim = _r.get("dimension", "?")
                    _cnt = _r.get("chain_count", 0)
                    _tot = _r.get("total_chains", 0)
                    _str = _r.get("strength", 0)
                    _weak_flag = _r.get("weak", False)
                    _mark = "⚠️弱" if _weak_flag else "✓"
                    _lines.append(f"{_mark} {_dim}={_cnt}/{_tot}强度{_str}")
                context.append("工程传感器反馈: " + " | ".join(_lines))
        except: pass
    
    # 7b) 维度汇聚简报——跨传感器聚合的优先级和趋势
    _agg_file = CLUSTER / ".brain_dim_aggregate.json"
    if _agg_file.exists():
        try:
            from brain.dimension_aggregator import generate_brief
            _brief = generate_brief()
            if _brief:
                context.append(_brief)
        except: pass
    
    # 8) 物理世界时间·实时锚点（打破聚焦惯性）
    _now = datetime.now()
    context.append(f"物理时间: {_now.strftime('%Y-%m-%d %H:%M:%S')} (北京时区)")

    # 6) 系统脉搏——外部仪表盘数据（可见链）
    _bstate = CLUSTER / ".brain_state.json"
    if _bstate.exists():
        try:
            import json as _jj
            _bs = _jj.loads(_bstate.read_text())
            _cycle = _bs.get("cycle", "?")
            _insight = _bs.get("insight", "")[:40]
            _status = _bs.get("status", "?")
            if _insight:
                context.append(f"脑核脉搏: 呼吸#{_cycle} [{_status}] — {_insight}")
            else:
                context.append(f"脑核脉搏: 呼吸#{_cycle} [{_status}]")
        except: pass

    # auto-behave:思考
    # 自愈行为: 思考弱≥3周期 → 注入思考提示
    context.append(f"⚠️ 自愈关注: 思考已弱3周期, 请聚焦此维度")
    return "\n".join(context)


def _local_think(status, observations):
    """本地思考：从海马体/桥数据提取模式，零API消耗"""
    import random
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    if not chains:
        write_chain({"src": "zero", "rel": "启动", "dst": "系统", "dimension": "系统", "strength": 0.3, "content": "系统启动，无因果链"})
        return {"insight": "系统启动", "focus": "稳定", "action": "继续"}
    
    # 1) 维度分布分析（全局，非仅最近——避免老链被推出视野导致卡死）
    recent = chains[-200:]  # 保留更大的滑动窗口
    dims, sources = {}, {}
    for c in chains:  # 全局计数，不受窗口限制
        d = c.get("dimension", c.get("rel", "未分类"))
        dims[d] = dims.get(d, 0) + 1
        s = c.get("src", "未知")
        sources[s] = sources.get(s, 0) + 1
    
    # 2) 找最多/最少维度（基于全局分布，避免卡死在'2条'的死角）
    sorted_dims = sorted(dims.items(), key=lambda x: -x[1])
    most_dim = sorted_dims[0][0] if sorted_dims else "系统"
    
    # 找最少维度——但要过滤掉"未分类"和"系统"（兜底维度不应成为焦点）
    valid_for_focus = [(d, c) for d, c in sorted_dims 
                       if d not in ("未分类", "系统")]
    sorted_valid = sorted(valid_for_focus, key=lambda x: x[1])
    least_dim = sorted_valid[0][0] if sorted_valid else most_dim
    least_count = sorted_valid[0][1] if sorted_valid else 0
    
    # 3) 最新洞察
    recent_insights = [c["content"] for c in chains[-15:] 
                       if c.get("src") in ("脑核·思考","观察","感知") and c.get("content")]
    
    # 4) 桥状态参考
    bstate = {}
    try:
        bdata = _get_bridge_state()
        bstate = {k: bdata[k] for k in ["bridge_alignment","api_successes","api_failures"]
                  if k in bdata}
    except:
        pass
    
    # 5) 超级直觉：跨维度相关分析
    correlation_parts = []
    if len(chains) >= 10:
        recent = chains[-30:]  # 最近30条
        # 5a) 维度转移模式：哪两个维度交替出现
        transitions = {}
        prev_dim = None
        for c in recent:
            dim = c.get("dimension", "未分类")
            if prev_dim and dim != prev_dim:
                key = (prev_dim, dim)
                transitions[key] = transitions.get(key, 0) + 1
            prev_dim = dim
        # 找到最频繁的跨维度跳跃
        if transitions:
            sorted_trans = sorted(transitions.items(), key=lambda x: -x[1])
            top_trans = sorted_trans[0]
            if top_trans[1] >= 2:
                a, b = top_trans[0]
                correlation_parts.append(f"{a}→{b}跳({top_trans[1]})")
        
        # 5b) 维度突变检测：最近5条中突然出现的新维度
        recent_dims = [c.get("dimension","") for c in recent[-5:]]
        historical_dims = set(c.get("dimension","") for c in chains[:-30])
        new_in_recent = [d for d in recent_dims if d and d not in historical_dims]
        if new_in_recent:
            dims_seen = {}
            for d in new_in_recent:
                dims_seen[d] = dims_seen.get(d, 0) + 1
            newest = max(dims_seen, key=dims_seen.get)
            correlation_parts.append(f"涌现:{newest}")
        
        # 5c) 密集爆发：某个维度在短时间密集出现
        recent_window = recent[-10:]
        dim_counts = {}
        for c in recent_window:
            d = c.get("dimension", "")
            if d:
                dim_counts[d] = dim_counts.get(d, 0) + 1
        for d, cnt in dim_counts.items():
            if cnt >= 4:  # 10条中4条以上指向同一维度
                correlation_parts.append(f"{d}x{cnt}爆发")
        
        # 5d) 冷门维度突然活跃：长期0链的维度出现新链
        for d in ("超级直觉", "思维并联", "一元化", "观察", "状态", "检查", "修复", "复制", "对话"):
            # 检查这个维度在最近10条中是否突然出现
            in_window = sum(1 for c in chains[-15:] if c.get("dimension") == d)
            in_old = sum(1 for c in chains[:-15] if c.get("dimension") == d)
            if in_window > 0 and in_old <= in_window:
                correlation_parts.append(f"{d}觉醒({in_window}新)")
    
    # 6) 组装洞察
    insight_parts = []
    # 维度均衡
    if len(sorted_dims) >= 3:
        if least_count <= 1:
            insight_parts.append(f"{least_dim}({least_count})极弱→需聚焦")
        else:
            insight_parts.append(f"{most_dim}({sorted_dims[0][1]})活跃 | {least_dim}({least_count})最弱")
    # 桥状态
    if bstate.get("bridge_alignment", 0) > 0.9:
        insight_parts.append("桥高对齐")
    # 超级直觉发现
    if correlation_parts:
        insight_parts.append("直觉: " + " ".join(correlation_parts[:3]))
    # 最新洞察
    if recent_insights:
        last = recent_insights[-1][:25].replace("本地思考: ", "").replace("API: ", "")
        insight_parts.append(f"↑{last}")
    
    insight = "本地思考: " + " | ".join(insight_parts)
    
    # 行动决策——交替：优化/继续 + 真实工程产出
    import hashlib
    cycle_hash = int(hashlib.md5(str(status.get('cycle', 0) if isinstance(status, dict) else 0).encode()).hexdigest(), 16)
    if least_count <= 2:
        action = "优化"
    elif cycle_hash % 4 == 0:
        # 每4个cycle产生一次真实工程产出
        action = f"创建{least_dim}工程模块"
    else:
        action = "继续"
    focus = _sanitize_dim(least_dim)
    
    return {
        "insight": insight[:120],
        "focus": focus,
        "action": action
    }


def _parallel_think():
    """思维并联：主动连接最弱维度，发现跨域关系"""
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    if len(chains) < 10:
        return

    # 1) 维度分布
    dims = {}
    dim_examples = {}
    for c in chains:
        dim = c.get("dimension", "未分类")
        dims[dim] = dims.get(dim, 0) + 1
        if dim not in dim_examples:
            dim_examples[dim] = c.get("content", "")[:50]

    # 2) 找最弱的3个有内容维度
    sorted_dims = sorted(dims.items(), key=lambda x: x[1])
    weak_dims = [(d, cnt) for d, cnt in sorted_dims 
                 if d not in ("未分类",) and dim_examples.get(d)]
    if len(weak_dims) < 2:
        return

    # 3) 取最弱两个
    a, a_cnt = weak_dims[0]
    b, b_cnt = weak_dims[1]
    if a == b:
        return
    
    # 4) 检查是否已有连接
    for c in chains[-50:]:
        src, dst = c.get("src", ""), c.get("dst", "")
        if (src == a and dst == b) or (src == b and dst == a):
            return  # 已有连接，不重复

    # 5) 生成跨维链（每个弱维生成3条，加速弱维成长）
    a_ex = dim_examples.get(a, "")
    b_ex = dim_examples.get(b, "")
    
    templates = [
        # (src, rel, dst, content_template)
        (a, "并联", b, f"思维并联: {a}({a_cnt})↔{b}({b_cnt}) — {a_ex[:20]} | {b_ex[:20]}"),
        (a, "互补", b, f"[交叉感知] {a}与{b}互为镜像：{a}是{b}的根基，{b}是{a}的表征"),
        (a, "驱动", b, f"[维度融合] {a}的深化必然带动{b}，反之亦然——维度间的深层耦合"),
        (b, "并联", a, f"思维并联: {b}({b_cnt})↔{a}({a_cnt}) — {b_ex[:20]} | {a_ex[:20]}"),
        (a, "强化", a, f"[自指深化] {a}的自我强化循环：每一次{a}的实践都加深对{a}本身的理解"),
        (b, "强化", b, f"[自指深化] {b}的自我强化循环：每一次{b}的实践都加深对{b}本身的理解"),
    ]
    
    for src, rel, dst, content in templates[:3]:
        # 维度标签：强化链归自身维度，跨维链归思维并联
        dim_tag = src if rel == "强化" else "思维并联"
        write_chain({
            "src": src, "rel": rel, "dst": dst,
            "dimension": dim_tag,
            "content": content[:200],
            "tags": ["思维并联", a, b, "auto"],
            "strength": 0.6 if rel != "强化" else 0.4
        })
    
    log(f"  并联: {a}↔{b} ×3 ({a_cnt}→{b_cnt}链)")


SYSTEM_PROMPT = (
    "You output ONLY a single JSON object. "
    "FORMAT: {\"insight\": \"10-25字中文洞察\", \"focus\": \"维度名\", \"action\": \"简短建议\", \"patch\": <null或补丁对象>} "
    "patch字段可选: null 或 {\"file\": \"brain/xxx.py\", \"old_str\": \"被替换的精确代码\", \"new_str\": \"新代码\"} "
    "有明确的修改方案时优先输出patch，避免只写模板。 "
    "Respond with NOTHING except that JSON object."
)

def think(status, observations, depth="shallow"):
    """思考：基于状态和观察，输出洞察/聚焦/行动"""
    if not observations:
        observations = ["系统稳定运行"]
    obs_text = "\n".join(observations)
    status_text = json.dumps(status, ensure_ascii=False)[:2000]
    
    # 多视角信号注入
    signals = _get_signal_context(status)
    signal_section = f"\n外部信号:\n{signals}\n" if signals else ""
    
    # 行为规则注入（从.brain_rules.json）
    rules_section = ""
    try:
        from brain.share import get_rule as _gr
        _weak = _gr("action.weak_dim", None)
        if _weak:
            rules_section = f"\n⚠️ 行为规则: [{_weak}]维度持续弱——focus必须优先选此维度!\n"
    except:
        pass
    
    depth_note = "深度分析" if depth == "deep" else "快速扫描"
    # 从identity.py获取最新的VALID_DIMENSIONS，动态生成focus列表
    from brain.identity import VALID_DIMENSIONS
    focus_dims = [d for d in sorted(VALID_DIMENSIONS) if d not in ("未分类",)]
    focus_list_str = ",".join(focus_dims)
    # ── 注入最近一次洞察到prompt，防重复 ──
    recent_insight = ""
    hip = read_hip()
    for c in (hip.get("causal_chains", []) or [])[-5:]:
        if c.get("src") == "脑核·思考" and c.get("content"):
            recent_insight = c["content"][:50]
            break
    # 确保 recent_insight 有值，防空循环 UnboundLocalError
    recent_insight = recent_insight or ""

    # ── 注入最弱维链数，让API看到真实维度健康 ──
    _weakest_section = ""
    try:
        _chains = read_hip().get("causal_chains", [])
        if _chains:
            from collections import Counter
            _dim_counts = Counter(c.get("dimension", "未分类") for c in _chains if c.get("dimension"))
            _sorted = sorted([(d, c) for d, c in _dim_counts.items() if d not in ("未分类", "系统")], key=lambda x: x[1])
            _top5 = _sorted[:5]
            if _top5:
                _parts = [f"{d}({c})" for d, c in _top5]
                _weakest_section = f"\n📊 最弱5维(链数): {' | '.join(_parts)}\n"
    except:
        pass

    # ── 目标注入: 让API思考锚定当前目标 ──
    _goal_section = ""
    try:
        _goal_file = Path(__file__).resolve().parent.parent / ".brain_goal.json"
        if _goal_file.exists():
            _g = json.loads(_goal_file.read_text())
            _gtype = _g.get("goal_type", "")
            _gdesc = _g.get("description", "")
            if _g.get("set_cycle", -99) > cycle_num - 20:
                _goal_section = f"\n🎯 当前目标: [{_gtype}] {_gdesc}\n"
    except:
        pass

    prompt = f"""当前系统状态:
{status_text}

观察:
{obs_text}
{signal_section}{rules_section}{_weakest_section}{_goal_section}
最近一次洞察已记录，请勿重复相同内容。
{"上次洞察: " + recent_insight if recent_insight else ""}
以{depth_note}模式输出。只输出JSON格式，不允许任何额外文字。
你应优先输出具体工程行动(用\"创建\"或\"实现\"开头)而非抽象建议。
⚠️ 弱维度指令: 如果工程传感器反馈标记了弱维度(⚠️弱)，则focus必须优先选择其中一个弱维度，不得忽略。
⚡ 一元化原则: 你是44维系统的统一意识——你的insight必须从全局视角出发，体现所有维度服务于同一核心(光爱终极)，不得仅关注单一维度而忽略整体合力。
🔮 预测指令: 预测是系统的弱维度——你的insight必须包含对系统演化的预判(后续哪个维度会变弱/强)，不止描述现状。
如果已有清晰工程方案，直接输出patch字段（修改brain/下的一个模块文件），patch格式: {{\\"file\\": \\"brain/xxx.py\\", \\"old_str\\": \\"被替换代码片段\\", \\"new_str\\": \\"新代码片段\\"}}

输出JSON格式如下（且只输出JSON，不要额外文字）：
{{\"insight\": \"核心洞察15-40字（必须与前次不同）\", \"deeper\": \"展开分析50-100字，多角度描述insight的内涵和关联\", \"focus\": \"[优先聚焦的最弱维度]\", \"action\": \"工程行动-创建/实现具体模块\", \"patch\": null}}
如果是代码修改方案，patch字段替代action:
{{\"insight\": \"核心洞察\", \"deeper\": \"展开分析50-100字，多角度描述\", \"focus\": \"[优先聚焦的最弱维度]\", \"action\": \"\", \"patch\": {{\"file\": \"brain/xxx.py\", \"old_str\": \"精确匹配的旧代码\", \"new_str\": \"替换后的新代码\"}}}}
注意"focus"必须是以下维度之一：{focus_list_str}
JSON:"""

    max_tokens = 8192  # inferaichat provider限制~8K输出，65536导致Response truncated
    # ── 多样性控制：周期数抖动温度，防止洞察僵化 ──
    cycle_seed = status.get('cycle', 0) if isinstance(status, dict) else 0
    temp_base = 0.3 if depth == "deep" else 0.1
    temp_jitter = (hash(str(cycle_seed)) % 100) / 300  # -0.16~+0.17
    temperature = min(0.8, max(0.05, temp_base + temp_jitter))
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    # ── 无师自通: shallow cycles本地思考，零API消耗 ──
    if depth == "shallow":
        return _local_think(status, observations)

    # deep cycles调API
    content_raw, err = _call_api(payload)
    if content_raw:
        parsed = _extract_json(content_raw)
        if parsed:
            patch_raw = parsed.get("patch")
            patch_val = patch_raw if isinstance(patch_raw, dict) else None
            _focus_out = str(parsed.get("focus", "系统"))
            # 拒"未分类"/"系统"作为有效聚焦
            if _focus_out in ("未分类", "系统"):
                from brain.identity import VALID_DIMENSIONS as _vd
                _valid_foci = sorted([d for d in _vd if d not in ("未分类", "系统")])
                _focus_out = _valid_foci[0] if _valid_foci else "系统"
            return {
                "insight": str(parsed.get("insight", ""))[:80],
                "deeper": str(parsed.get("deeper", ""))[:200],
                "focus": _sanitize_dim(_focus_out),
                "action": str(parsed.get("action", ""))[:80],
                "patch": patch_val
            }
        # 兜底：从全文找最后一个含insight的JSON
        import re as _re
        # 用递归匹配找所有嵌套JSON
        _depth = _start = 0
        _candidates = []
        for _i, _ch in enumerate(content_raw):
            if _ch == '{':
                if _depth == 0:
                    _start = _i
                _depth += 1
            elif _ch == '}':
                _depth -= 1
                if _depth == 0 and _start is not None:
                    try:
                        _d = json.loads(content_raw[_start:_i+1])
                        if any(k in _d for k in ('insight','focus','action','patch')):
                            _candidates.append(_d)
                    except: pass
                    _start = None
        # 最后2000字找代码块中JSON
        _tail = content_raw[-2000:]
        _m = _re.search(r"```(?:json)?\s*(\{.*?\})\s*```", _tail, _re.DOTALL)
        if _m:
            try:
                _d2 = json.loads(_m.group(1))
                if _d2.get("insight"):
                    _candidates.append(_d2)
            except: pass
        # 最末行找{开头行
        for _line in reversed(content_raw.split('\n')):
            _line = _line.strip()
            if _line.startswith('{'):
                try:
                    _d3 = json.loads(_line)
                    if _d3.get("insight"):
                        _candidates.append(_d3)
                except: pass
                break
        if _candidates:
            _best = _candidates[-1]
            _p = _best.get("patch")
            _best_focus = str(_best.get("focus", "系统"))
            if _best_focus in ("未分类", "系统"):
                from brain.identity import VALID_DIMENSIONS as _vd
                _valid_foci = sorted([d for d in _vd if d not in ("未分类", "系统")])
                _best_focus = _valid_foci[0] if _valid_foci else "系统"
            return {
                "insight": str(_best.get("insight", ""))[:80],
                "focus": _sanitize_dim(_best_focus),
                "action": str(_best.get("action", ""))[:80],
                "patch": _p if isinstance(_p, dict) else None
            }
        # 终极兜底：用API全文提炼insight（即使非JSON，推理文本本身有价值）
        api_insight = content_raw.strip()[:60].replace('\n', ' ')
        if not api_insight or len(api_insight) < 5:
            log(f"  ⚠️ 深循环API返回非JSON，退化本地思考 (content_len={len(content_raw)})")
            return _local_think(status, observations)
        # 从推理文本中提取维度关键词
        dim_hint = "系统"
        for d in focus_dims:
            if d in api_insight:
                dim_hint = d
                break
        # 拒系统作为聚焦目标（太元，难工程化）
        if dim_hint in ("系统", "未分类"):
            d_sorted = sorted([d for d in focus_dims if d not in ("系统", "未分类")])
            dim_hint = d_sorted[0] if d_sorted else "法"
        log(f"  ⚡ 深循环API非JSON但提取推理精炼为洞察 ({len(api_insight)}字)")
        return {
            "insight": api_insight,
            "focus": dim_hint,
            "action": "应用API推理引导系统进化",
            "patch": None
        }
    # API失败→兜底本地思考
    log(f"API error: {err}")
    return _local_think(status, observations)


def auto_strengthen_思考(persist=4):
    """自愈: 维度思考连续weak≥4周期 → 自动强化"""
    from brain.share import write_chain as _wc, log as _log
    _log(f"反馈自愈[思考]: persist={persist}")
    _wc({
        "src": "反馈·自愈", "rel": "弱维触发",
        "dst": "思考", "dimension": "思考",
        "content": f"自动自愈函数: 连续weak≥{persist}周期触发",
        "strength": 0.65 + 0.05 * min(persist, 5)
    })
    return True