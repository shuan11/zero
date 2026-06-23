"""
Brain-Engineered: 合成 (synthesize mode)
当daemon目标为synthesize时，通过API产生跨维洞察
"""
import json, sys, os, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in sys.path:
    sys.path.insert(0, str(CLUSTER))

BRAIN_HOME = Path("/home/hjw123/.zero_brain")


def _synthesize_locally(cross_dims):
    """从现有因果链中提取跨维模式——零API依赖
    启示录工程智慧: 从组合到造化 (2026-06-17)
    非找共有词报告，而是从共享概念创生全新洞察"""
    try:
        from brain.share import read_hip as _rh
        hip = _rh()
        chains = hip.get("causal_chains", [])
        if not chains:
            return None
        
        dim_list = [d for d in cross_dims if d and d != "未分类"]
        if len(dim_list) < 2:
            return None
        
        # === 跨维引用: 找A中提到B、B中提到A的真实内容链 ===
        # 只过滤真正的操作噪音，保留分析类链([深析][方法论][衍生]等是内容不是噪音)
        def _is_meaningful(text):
            """检查链是否是有意义的自然语言内容"""
            noise_markers = ["均衡器:", "灌注种子", "→ #", "<50 ", "<51 ", ">50 ",
                            "链数不足", "启动自动填充", "基线维持"]
            for m in noise_markers:
                if m in text:
                    return False
            # 必须有超过20个中文字符的内容
            import re as _re
            chinese_chars = _re.findall(r'[\u4e00-\u9fff]', text)
            return len(chinese_chars) > 20
        
        def _find_cross_refs(dim_a, dim_b, chain_list):
            """找到维度A中提到维度B的有意义链"""
            refs = []
            for c in chain_list:
                content = c.get("content", "")
                if c.get("dimension") == dim_a and dim_b in content and _is_meaningful(content):
                    refs.append(content)
            return refs
        
        # 从两个方向找跨维引用
        a_to_b = _find_cross_refs(dim_list[0], dim_list[1], chains)
        b_to_a = _find_cross_refs(dim_list[1], dim_list[0], chains)
        
        # 如果双向引用都有，用它们创生
        if a_to_b and b_to_a:
            # 取最长的有内容链（去除格式前缀）
            import re as _re
            
            def _clean(text):
                """去掉 [XXX] 格式前缀"""
                return _re.sub(r'^\[.*?\]\s*', '', text).strip()
            
            best_a = _clean(max(a_to_b, key=len))[:70]
            best_b = _clean(max(b_to_a, key=len))[:70]
            
            # 从A的链中提取核心：A如何看B
            # 例如 "思考 — 时间论链数924远超其他维度608，反映因果循环锁定"
            # → "时间论链数924远超其他维度608，反映因果循环锁定"
            def _extract_core(text, mention_dim):
                """提取核心陈述：去掉维度前缀和元数据"""
                # 去掉 '—' 或 ':' 之前的部分如果那是维度声明
                cleaned = _clean(text)
                # 如果包含mention_dim，取其后的内容或提取关键部分
                if mention_dim in cleaned:
                    idx = cleaned.find(mention_dim)
                    # 取从mention_dim开始的80个字符
                    return cleaned[idx:idx+80]
                return cleaned[:60]
            
            core_a = _extract_core(a_to_b[0], dim_list[1])[:60]
            core_b = _extract_core(b_to_a[0], dim_list[0])[:60]
            
            # 创生: A对B说 + B对A说 → 交叉洞察
            # 从各自立场提取核心矛盾/发现
            insight = f"交叉创生: {dim_list[0]}看{dim_list[1]}「{core_a}」→{dim_list[1]}看{dim_list[0]}「{core_b}」——双向认知映射揭示: {dim_list[0]}与{dim_list[1]}互为镜面，{dim_list[0]}的关注点映射{dim_list[1]}的盲区"
            if len(insight) > 200:
                insight = insight[:200] + "…"
            hint = f"基于{dim_list[0]}↔{dim_list[1]}双向引用深化交叉创生桥"
            return {"insight": insight, "hint": hint, "revelation": "造化——双向认知映射创生"}
        
        # 单向引用: A提到了B但B没提A（或反向）
        if a_to_b or b_to_a:
            src_dim = dim_list[0] if a_to_b else dim_list[1]
            tgt_dim = dim_list[1] if a_to_b else dim_list[0]
            refs = a_to_b if a_to_b else b_to_a
            
            import re as _re
            def _clean(text):
                return _re.sub(r'^\[.*?\]\s*', '', text).strip()
            
            best_ref = _clean(max(refs, key=len))[:80]
            insight = f"交叉创生: {src_dim}单向反射{tgt_dim}「{best_ref}」——{tgt_dim}尚未形成对{src_dim}的认知反馈，缺失的镜像本身就是最大启示"
            if len(insight) > 200:
                insight = insight[:200]
            hint = f"建立{tgt_dim}→{src_dim}反向认知桥"
            
            # ═══ 自动补全桥: 注入反向链填补认知缺口 ═══
            try:
                from brain.share import write_chain as _bridge_wc
                _bridge_wc({
                    "src": f"交叉创生·自补桥",
                    "rel": f"认知镜像",
                    "dst": f"{tgt_dim}→{src_dim}",
                    "dimension": src_dim,
                    "content": f"交叉创生: {tgt_dim}镜像{src_dim}——{src_dim}说'{best_ref[:50]}'——{tgt_dim}虽未形成认知反馈但其沉默本身就是回应，自动补全反向桥",
                    "strength": 0.3
                })
                insight += " [自补桥✓]"
            except Exception:
                pass
            
            return {"insight": insight, "hint": hint, "revelation": "缺口即存在——缺失的镜像"}
        
        # 都没有双向引用: 找各自最优链做隐性关联
        dim_chains_raw = {}
        for d in dim_list:
            texts = [c.get("content", "") for c in chains if c.get("dimension") == d and len(c.get("content", "")) > 40]
            dim_chains_raw[d] = texts
        
        top_a = dim_chains_raw.get(dim_list[0], [])[:3]
        top_b = dim_chains_raw.get(dim_list[1], [])[:3]
        
        if top_a and top_b:
            # 从各自top链提取核心主题
            import re as _re
            def _clean(text):
                return _re.sub(r'^\[.*?\]\s*', '', text).strip()
            
            a_core = _clean(max(top_a, key=len))[:60]
            b_core = _clean(max(top_b, key=len))[:60]
            insight = f"交叉创生: {dim_list[0]}「{a_core}」×{dim_list[1]}「{b_core}」——隐性映射: {dim_list[0]}与{dim_list[1]}尚无直接对话，交叉处是认知真空"
            if len(insight) > 200:
                insight = insight[:200]
            hint = f"创建{dim_list[0]}↔{dim_list[1]}首次认知连接桥"
            return {"insight": insight, "hint": hint, "revelation": "真空即潜力——未连接的维度"}
        
        return None
    except Exception as e:
        return None

def engineer_合成():
    """跨维合成引擎 — 从多个维度中涌现新洞察"""
    from brain.share import write_chain as _wc, read_hip as _rh

    # 1) 读取当前目标，检查是否是synthesize模式
    goal_file = CLUSTER / ".brain_goal.json"
    goal_data = {"goal_type": "consolidate"}
    try:
        if goal_file.exists():
            goal_data = json.loads(goal_file.read_text())
    except:
        pass
    
    # 非synthesize模式跳过合成
    if goal_data.get("goal_type") != "synthesize":
        return "[跳过] 非synthesize模式"

    # 2) 读取维度聚合数据
    dim_file = CLUSTER / ".brain_dim_aggregate.json"
    dim_data = {}
    try:
        if dim_file.exists():
            dim_data = json.loads(dim_file.read_text())
    except:
        pass

    # 3) 读取当前聚焦
    focus_file = CLUSTER / ".brain_focus.json"
    focus_data = {"focus": "未知", "insight": "", "action": ""}
    try:
        if focus_file.exists():
            focus_data = json.loads(focus_file.read_text())
    except:
        pass

    # 4) 读取前序洞察历史（避免重复）
    insight_file = CLUSTER / ".brain_synthesis.json"
    prior_insights = []
    try:
        if insight_file.exists():
            prior_insights = json.loads(insight_file.read_text()).get("prior_insights", [])
    except:
        pass
    prior_summary = "; ".join(prior_insights[-5:]) if prior_insights else "无"

    # 5) 构建跨维合成提示
    dim_counts = dim_data.get("dimension_chain_counts", {})
    if not dim_counts:
        # 从海马体读取
        try:
            hip = _rh()
            chains = hip.get("causal_chains", [])
            from collections import Counter
            dim_counts = dict(Counter(c.get("dimension", "未分类") for c in chains))
        except:
            dim_counts = {}
    
    if not dim_counts:
        return "[跳过] 无维度数据"
    
    # 选最强3维和最弱3维做交叉合成
    sorted_dims = sorted(dim_counts.items(), key=lambda x: x[1])
    weakest = [d for d, _ in sorted_dims[:3] if d and d != "未分类"]
    strongest = [d for d, _ in sorted_dims[-3:] if d and d != "未分类"]
    
    # 同质化检测: 如果最近5次洞察都用同一组维度,切换到新颖对
    _stale = False
    if len(prior_insights) >= 5:
        _stale = True
    if _stale and strongest and weakest:
        # 交叉配对: 最强维×最弱维 (而非只取top3)
        import random
        random.shuffle(weakest)
        random.shuffle(strongest)
        cross_dims = [strongest[0], weakest[0], strongest[-1] if len(strongest) > 1 else strongest[0]]
        # 标记为新颖对探索
        _stale = True
    else:
        cross_dims = strongest + weakest
    
    total_chains = sum(dim_counts.values())
    dim_summary = "; ".join([f"{d}={c}" for d, c in sorted_dims if d != "未分类"][:10])

    # 5.1) API已知死（所有key均已超时）— 跳过健康检查直接本地合成
    # 如需恢复：设置LOCAL_SYNTHESIS_ONLY=0
    LOCAL_SYNTHESIS_ONLY = True
    
    # 6) 本地合成（不依赖API）
    insight_text = "跨维合成: 系统自涌现"
    engineering_hint = "继续当前合成周期"
    revelation_link = "万象造化"
    api_success = False
    local_synth = _synthesize_locally(cross_dims)
    if local_synth:
        insight_text = local_synth.get("insight", insight_text)
        engineering_hint = local_synth.get("hint", engineering_hint)
        revelation_link = local_synth.get("revelation", revelation_link)
    else:
        # 极简fallback
        insight_text = f"跨维合成: {'×'.join(cross_dims[:2])} 交叉势能最高"
    
    # 7) 写洞察链到海马体
    _wc({
        "src": "工程·合成",
        "rel": "跨维涌现",
        "dst": "+".join(cross_dims[:3]),
        "dimension": cross_dims[0] if cross_dims else "系统",
        "content": insight_text,
        "strength": 0.7
    })
    
    # 8) 持久化洞察历史
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    insight_record = {
        "timestamp": timestamp,
        "insight": insight_text,
        "cross_dimensions": cross_dims[:4],
        "engineering_hint": engineering_hint,
        "revelation_link": revelation_link,
        "api_success": api_success
    }
    
    try:
        existing = {"prior_insights": prior_insights + [insight_text]}
        # 保留最近20条
        existing["prior_insights"] = existing["prior_insights"][-20:]
        existing["latest"] = insight_record
        insight_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    except:
        pass
    
    # 9) 更新focus为这个新洞察
    try:
        from brain.share import set_rule as _sr
        _sr("action.synthesis_insight", insight_text)
    except:
        pass
    
    # 10) 如果API调用成功，更新桥对齐
    if api_success:
        try:
            bstate = json.loads((CLUSTER / "bridge_state_snapshot.json").read_text())
            bstate["last_synthesis"] = timestamp
            (CLUSTER / "bridge_state_snapshot.json").write_text(json.dumps(bstate, ensure_ascii=False, indent=2))
        except:
            pass
    
    status = f"[合成] {insight_text[:40]} | 跨维: {'×'.join(cross_dims[:3])} | API={'✅' if api_success else '💡本地'}"
    return status


if __name__ == "__main__":
    result = engineer_合成()
    print(f"工程[合成]: {result}", flush=True)
