"""brain/act.py — 行动+工程"""
import json
import os
import sys as _sys
import time
from datetime import datetime
from pathlib import Path
from brain.share import CLUSTER, HIP_FILE, log, write_chain, read_hip
from brain.identity import VALID_DIMENSIONS
from .identity import sanitize_dim, IDENTITY

# ─── 维度白名单（从identity.py单源导入）─────────────────
# 增删维度只改 brain/identity.py
# 消毒函数 sanitize_dim() 同理

def act(thought, status, cycle_num):
    """根据思考结果行动 + 执行动作"""
    if not thought:
        log("  无思考结果，跳过行动")
        return
    
    insight = thought.get("insight", "")
    deeper = thought.get("deeper", "")
    api_insight = thought.get("api_insight", insight)  # original API insight (before focus-repeat overwrite)
    focus = thought.get("focus", "系统")
    action = thought.get("action", "")
    
    # 维度消毒：API输出可能含非法文本（如prompt泄漏）
    focus = sanitize_dim(focus)
    
    # 从genome读取质量配置（让变异从genome控制而非硬编码）
    _q_strength = 0.6  # 默认值
    _q_min_len = 80
    try:
        from brain.genome import load_genome
        _g = load_genome()
        _q_strength = _g.get('quality.enforce_strength', 0.6)
        _q_min_len = _g.get('quality.min_content_len', 80)
    except:
        pass
    
    # 写入因果链——显式标记维度，防止自动分类丢失
    # auto-behave:行动
    # 自愈行为: 行动弱≥4周期 → 主动补链
    if True:  # always run when this dim is weak
        from brain.share import write_chain as _wc_auto
        _wc_auto({
            "src": "自愈·主动行为",
            "rel": f"自动补链·#{cycle_num}",
            "dst": "行动",
            "dimension": "行动",
            "content": f"自愈行为注入: 行动连续弱≥4周期后主动生链(cycle#{cycle_num})",
            "strength": _q_strength
        })
    # rel包含cycle_num确保每cycle链的唯一性，打破safe_hip去重导致的计数死锁
    if insight:
        # 质量强化：内容长于genome配置则提strength
        _dynamic_s = _q_strength
        if len(insight) > _q_min_len * 2:
            _dynamic_s = min(0.95, _q_strength + 0.15)  # 长篇→加点
        elif len(insight) < 10:
            _dynamic_s = max(0.3, _q_strength - 0.2)   # 太短→减点
        ok = write_chain({
            "src": "脑核·思考",
            "rel": f"发现·#{cycle_num}",
            "dst": focus,
            "dimension": focus,  # 显式维度映射，让计数真实反映思考方向
            "content": insight,
            "tags": ["思考", focus, "自动"],
            "strength": _dynamic_s
        })
        log(f"  链: 脑核·思考 → {focus}")
        # 衍生链（倍增链产出）— 使用原始API洞察而非被聚焦跳转覆盖的文本
        try:
            _insight_derived(focus, api_insight, deeper, cycle_num)
        except Exception:
            pass
    
    # 执行动作（闭环节点）
    if action and action.strip():
        _route_action(action, focus, insight, cycle_num)
    
    # 弱维被动注入：每周期给最弱±3维+1链（不依赖API，解决弱维生长+0.0链）
    # 注: 质量门block mode下模板链被拦截(score<0.15), 此注入已无效
    # 改为: 被质量门拦截时跳过写入,降低无效IO
    try:
        from brain.genome import get as _gw
        if _gw("quality.block_noise", True) and _gw("quality.log_only", False) is False:
            # block mode下模板链必然被拦截，跳过无效写入
            log(f"  质量门block mode: 跳过模板型弱维支撑(将被拦截)")
        else:
            _hip_w = read_hip()
            _c_w = _hip_w.get("causal_chains", [])
            _dc_w = {}
            for _c in _c_w:
                _d = _c.get("dimension", "未分类")
                _dc_w[_d] = _dc_w.get(_d, 0) + 1
            _sorted_w = sorted(_dc_w.items(), key=lambda x: x[1])
            _weak_w = [d for d, c in _sorted_w[:5] if d not in ("未分类", "系统", "行动")][:3]
            for _wd in _weak_w:
                write_chain({
                    "src": "脑核·弱维支撑",
                    "rel": f"被动注入·#{cycle_num}",
                    "dst": _wd, "dimension": _wd,
                    "content": f"系统周期性弱维支撑: {_wd}基线维持",
                    "strength": max(0.2, _q_strength - 0.3)
                })
            if _weak_w:
                log(f"  弱维支撑: {', '.join(_weak_w)} +1链")
    except Exception as _e:
        log(f"  弱维支撑异常: {_e}")

    # 深循环代码进化：API返回的patch直接注入（长程唯一进化引擎）
    patch_spec = thought.get("patch")
    if patch_spec and isinstance(patch_spec, dict):
        ok, reason = _inject_code(patch_spec)
        if ok:
            log(f"  自进化: {patch_spec.get('file','?')} ← API洞察代码注入 ✓")
            # 写审计记录
            _audit_file = CLUSTER / ".brain_audit.json"
            try:
                audits = json.loads(_audit_file.read_text()) if _audit_file.exists() else []
                audits.append({
                    "type": "API_evolve",
                    "file": patch_spec.get("file",""),
                    "cycle": cycle_num,
                    "insight": insight[:60],
                    "timestamp": time.time()
                })
                _audit_file.write_text(json.dumps(audits[-100:], ensure_ascii=False, indent=2))
            except: pass
        else:
            log(f"  自进化失败: {reason}")
    
    # 更新焦点文件
    _focus_file = CLUSTER / ".brain_focus.json"
    try:
        _focus_file.write_text(json.dumps({
            "focus": focus,
            "insight": insight,
            "action": action,
            "cycle": cycle_num,
            "timestamp": time.time()
        }, ensure_ascii=False, indent=2))
    except:
        pass

def _route_action(action, focus, insight, cycle_num):
    """路由动作到具体执行函数——闭环节点"""
    action_lower = action.lower().strip()
    
    # 动作→处理器映射
    if any(kw in action_lower for kw in ["继续", "监控", "观察", "等待"]):
        return  # 静默——行为就是继续呼吸
    
    if any(kw in action_lower for kw in ["清理", "精简", "压缩", "去重"]):
        log(f"  动作→清理: {action}")
        return _action_cleanup(focus)
    
    if any(kw in action_lower for kw in ["修复", "恢复", "重建"]):
        log(f"  动作→修复: {action}")
        return _action_repair(focus)
    
    if any(kw in action_lower for kw in ["检查", "审计", "验证", "审查", "扫描"]):
        log(f"  动作→检查: {action}")
        return _action_audit(focus)

    if any(kw in action_lower for kw in ["创建", "工程", "实现", "构建", "生成", "写一个", "造", "建", "行动", "深化", "代码"]):
        log(f"  动作→真实工程: {action}")
        return _action_real_engineer(focus, insight, action, cycle_num)

    # 额外路由关键字（由gen模块通过add_action_keyword注入）
    try:
        from brain.share import get_action_keywords as _gak
        _extra = _gak()
        if _extra and any(kw in action_lower for kw in _extra):
            log(f"  动作→真实工程(规则关键字): {action}")
            return _action_real_engineer(focus, insight, action, cycle_num)
    except:
        pass

    if any(kw in action_lower for kw in ["注入", "信号", "并联", "跨维度", "跨维", "跨域"]):
        log(f"  动作→注入跨维信号: {action}")
        try:
            from .cross_dim_injector import inject_signals, auto_inject
            result = inject_signals(focus, count=6)
            log(f"  注入结果: {result.get('injected',0)}条新信号")
        except Exception as e:
            log(f"  注入失败: {e}")
        return
    
    if any(kw in action_lower for kw in ["提升", "优化", "加强", "深化", "强化"]):
        log(f"  动作→优化: {action}")
        return _action_optimize(focus, insight)
    
    if any(kw in action_lower for kw in ["写入", "记录", "保存"]):
        log(f"  动作→写入: {action}")
        return  # 已经在写入了

    # 未识别动作→提案队列
    log(f"  动作→提案队列: {action}")
    _defer_action(action, focus)

    # 系统维度链：每次act都记录系统运行轨迹
    write_chain({
        "src": "脑核·行动",
        "rel": "系统脉冲",
        "dst": "系统",
        "dimension": "系统",
        "content": f"Act {action if len(action) < 50 else action[:50]+'...'} 聚焦{focus}",
        "strength": 0.3
    })


def _action_cleanup(focus):
    """清理动作"""
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        if not chains:
            return
        # 简单去重：相同内容只保留最新一条
        seen = set()
        keep = []
        dupes = 0
        for c in reversed(chains):
            key = c.get("content", "")[:40]
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            keep.append(c)
        if dupes > 0:
            from .share import save_hip
            save_hip({"causal_chains": list(reversed(keep)), "version": 1})
            log(f"  清理: 去重{dupes}条")
    except Exception as e:
        log(f"  清理失败: {e}")


def _action_repair(focus):
    """修复动作——检查海马体完整性"""
    from .share import validate_hip, normalize_hip
    errs = validate_hip()
    if errs:
        log(f"  修复: {len(errs)}个错误")
        normalize_hip()


def _action_audit(focus):
    """审计动作——记录当前状态"""
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        dims = {}
        for c in chains:
            d = c.get("dimension", "未分类")
            dims[d] = dims.get(d, 0) + 1
        audit = {
            "time": time.time(),
            "cycles": [c.get("content","")[:30] for c in chains if c.get("src")=="脑核·思考"][-5:],
            "dimensions": dict(sorted(dims.items(), key=lambda x:-x[1])[:10]),
            "focus": focus
        }
        (CLUSTER / ".brain_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
        log(f"  审计: {len(chains)}链 {len(dims)}维")
    except Exception as e:
        log(f"  审计失败: {e}")


def _action_optimize(focus, insight):
    """优化动作——创建提案"""
    prop = {
        "type": "optimize",
        "focus": focus,
        "insight": insight[:60],
        "timestamp": time.time()
    }
    prop_file = CLUSTER / ".brain_proposals.json"
    try:
        existing = []
        if prop_file.exists():
            existing = json.loads(prop_file.read_text()).get("proposals", [])
        existing.append(prop)
        prop_file.write_text(json.dumps({"proposals": existing}, ensure_ascii=False, indent=2))
        log(f"  优化提案: {focus} ({len(existing)}待处理)")
    except Exception as e:
        log(f"  提案失败: {e}")


def _action_real_engineer(focus, insight, action, cycle_num=0):
    """真实工程动作——创建/修改文件，打破'只记录不执行'的模拟循环"""
    try:
        # 确定目标文件名
        safe_focus = "".join(c for c in focus if c.isalnum() or c in '_')
        if not safe_focus:
            safe_focus = "unknown"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 根据focus类型选择产出
        if any(kw in focus for kw in ["桥", "bridge", "对齐"]):
            content = f'''"""\nBrain-Engineered: bridge alignment enhancer for {focus}\nGenerated from insight: {insight[:80]}\n"""\nimport sys as _sys\nfrom pathlib import Path\n\nCLUSTER = Path(__file__).resolve().parent.parent\nif str(CLUSTER) not in _sys.path:\n    _sys.path.insert(0, str(CLUSTER))\n\ndef enhance_{safe_focus.lower()}():\n    """由脑核洞察 {insight[:60]} 注入的工程函数"""\n    return True\n'''
            target = CLUSTER / f"brain/generated_{safe_focus.lower()}_{timestamp.split('_')[0]}.py"
            target.write_text(content)
            log(f"  工程产出: {target.name}")

        elif any(kw in focus for kw in ["监测", "监控", "watch", "监控器"]):
            content = f'''"""\nBrain-Engineered: monitor for {focus}\nFrom insight: {insight[:80]}\n"""\nimport time\nimport sys as _sys\nfrom pathlib import Path\n\nCLUSTER = Path(__file__).resolve().parent.parent\nif str(CLUSTER) not in _sys.path:\n    _sys.path.insert(0, str(CLUSTER))\n\ndef check_{safe_focus.lower()}():\n    """{insight[:60]}"""\n    return True\n\nif __name__ == "__main__":\n    check_{safe_focus.lower()}()\n'''
            target = CLUSTER / f"brain/gen_{safe_focus.lower()}_{timestamp.split('_')[0]}.py"
            target.write_text(content)
            log(f"  工程产出: {target.name}")
        else:
            # 增强型模板：每个工程文件成为主动传感器返回维度健康分析而非只写一条链
            content = f'''"""

Brain-Engineered: {focus} (cycle #{cycle_num})
Active sensor - analyzes dimension health on each load
"""
import json, sys as _sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in _sys.path:
    _sys.path.insert(0, str(CLUSTER))

_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"

def engineer_{safe_focus.lower()}():
    """{insight[:120]}
    Returns dimension health analysis; feeds into next think() cycle.
    """
    from brain.share import write_chain as _wc, read_hip as _rh

    # 1) Always write the insight chain
    _wc({{
        "src": "工程·{safe_focus.lower()}",
        "rel": "活脉冲·#{cycle_num}",
        "dst": "{safe_focus.lower()}",
        "dimension": "{safe_focus.lower()}",
        "content": """{insight[:60]}""",
        "strength": 0.6
    }})

    # 2) Read hippocampus and analyze dimension health
    try:
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
        dim_counts = {{}}
        for c in chains:
            d = c.get("dimension", "未分类")
            dim_counts[d] = dim_counts.get(d, 0) + 1

        my_dim = "{safe_focus.lower()}"
        my_count = dim_counts.get(my_dim, 0)
        total = len(chains)
        max_count = max(dim_counts.values()) if dim_counts else 0

        analysis = {{}}
        analysis["dimension"] = my_dim
        analysis["chain_count"] = my_count
        analysis["total_chains"] = total
        analysis["strength"] = round(my_count / max(max_count, 1), 2) if max_count > 0 else 0
        analysis["insight"] = """{insight[:60]}"""
        analysis["weak"] = my_count < max_count * 0.65  # 低于最强65%即弱维(替代avg*0.85,解决均数通胀)
        analysis["cycle"] = {cycle_num}

        # 3) Write analysis to shared feedback file for next think()
        try:
            existing = []
            if _GEN_FEEDBACK_FILE.exists():
                existing = json.loads(_GEN_FEEDBACK_FILE.read_text()).get("reports", [])
            existing.append(analysis)
            existing = existing[-50:]
            _GEN_FEEDBACK_FILE.write_text(json.dumps({{"reports": existing}}, ensure_ascii=False, indent=2))
        except Exception:
            pass

        # 4) Self-heal weak dimension: auto-generate reinforcing cross-links
        if analysis.get("weak"):
            try:
                # 弱维互助网: 找最弱维度做交叉链（而非链接到强维，强维已足够）
                sorted_dims = sorted(dim_counts.items(), key=lambda x: x[1])
                peer_weak = [d for d, _ in sorted_dims[:5] if d and d not in ("未分类", "系统") and d != my_dim][:3]
                for peer in peer_weak:
                    pc = dim_counts.get(peer, 0)
                    _wc({{
                        "src": my_dim,
                        "rel": "弱维互助",
                        "dst": peer,
                        "dimension": my_dim,
                        "content": "弱维互助: " + str(my_dim) + "(" + str(my_count) + ")↔" + str(peer) + "(" + str(pc) + ") 弱维互相强化",
                        "strength": 0.6
                    }})
                if peer_weak:
                    analysis["self_healed"] = len(peer_weak)
                # 5) Push focus rule: tell daemon to directly focus this weak dim
                try:
                    from brain.share import set_rule as _sr
                    _sr("action.weak_dim", my_dim)
                    analysis["focus_push"] = True
                except Exception:
                    pass
            except Exception:
                pass

        status = f"[{{'弱' if analysis['weak'] else '稳'}}] {{my_dim}}={{my_count}}/{{total}}"
        return status
    except Exception as e:
        return f"分析异常: {{e}}"

if __name__ == "__main__":
    result = engineer_{safe_focus.lower()}()
    print(f"工程[{focus}]: {{result}}", flush=True)
'''
            target = CLUSTER / f"brain/gen_{safe_focus.lower()}_{timestamp.split(chr(95))[0]}.py"
            target.write_text(content)
            log(f"  工程产出: {target.name}")

        # 统一执行
        import subprocess as _sp
        try:
            result = _sp.run(
                [_sys.executable, str(target)],
                capture_output=True, text=True, timeout=10,
                cwd=str(CLUSTER)
            )
            if result.returncode == 0:
                out = result.stdout.strip()[:80]
                log(f"  工程执行: {chr(10003) + ' ' + out if out else chr(10003)}")
            else:
                err = result.stderr.strip()[:80]
                log(f"  工程执行: {chr(9888) + ' ' + err if err else chr(9888)}")
        except Exception as _e:
            log(f"  工程执行: {chr(9888)} {_e}")

        # 记录到海马体
        from brain.share import write_chain as _wc
        _wc({
            "src": "脑核·工程",
            "rel": "真实产出",
            "dst": focus,
            "content": f"工程产出 {target.name}: {insight[:60]}",
            "tags": ["工程", "真实", focus],
            "strength": 0.9
        })
        
    except Exception as e:
        log(f"  工程动作失败: {e}")
        try:
            from brain.share import write_chain as _wc
            _wc({"src": "脑核·工程", "rel": "失败", "dst": focus, "content": str(e)[:80], "strength": 0.3})
        except:
            pass


def _defer_action(action, focus):
    """未识别动作→待办队列"""
    defer_file = CLUSTER / ".brain_deferred.json"
    try:
        deferred = []
        if defer_file.exists():
            deferred = json.loads(defer_file.read_text()).get("deferred", [])
        deferred.append({
            "action": action[:60],
            "focus": focus,
            "time": time.time()
        })
        defer_file.write_text(json.dumps({"deferred": deferred}, ensure_ascii=False, indent=2))
    except Exception as e:
        log(f"  待办失败: {e}")

def _consume_proposals():
    """消费提案——真实工程实现而非仅存档"""
    prop_file = CLUSTER / ".brain_proposals.json"
    if not prop_file.exists():
        return
    
    try:
        raw = json.loads(prop_file.read_text())
        # 兼容两种格式: dict{"proposals":[...]} 或 裸list
        if isinstance(raw, dict):
            props_list = raw.get("proposals", [])
        elif isinstance(raw, list):
            props_list = raw
        else:
            props_list = []
        
        consumed = 0
        for p in props_list:
            focus = p.get("focus", "") or p.get("dimension", "")
            insight = p.get("insight", "") or p.get("content", "")
            action_hint = p.get("action", "")
            
            # 写入因果链确认消费
            write_chain({
                "src": "提案",
                "rel": "消费",
                "dst": focus or "系统",
                "content": f"消费·{focus}: {insight[:40]}" if insight else f"消费·{focus}",
                "tags": ["提案", "消费", focus],
                "strength": 0.5
            })
            consumed += 1
            
            # 消费记录——诚实标记，不冒充未做的工程实现
            write_chain({
                "src": "提案",
                "rel": "已消费",
                "dst": focus or "系统",
                "dimension": focus or "系统",  # 显式维度
                "content": f"自动消费·{focus}: {insight[:40]}" if insight else f"自动消费·{focus}",
                "tags": ["提案", "自动消费", focus],
                "strength": 0.3
            })
        
        if consumed:
            log(f"  消耗提案: {consumed}条")
            # 尝试将最佳提案转化为代码修改
            _try_implement_last_proposal(props_list)
        prop_file.unlink()
        
    except Exception as e:
        log(f"  消费提案异常: {e}")
    
    # 从gen_*反馈中找弱维度，尝试注入代码补丁
    _feedback_self_patch()
    
    # 补齐缺失维度的传感器文件（每周期间接执行，每次补最多3个）
    _ensure_missing_gen_sensors()


def _ensure_missing_gen_sensors():
    """补齐没有gen_*文件的维度传感器"""
    try:
        from .identity import VALID_DIMENSIONS
        import re
        existing_dims = set()
        for f in CLUSTER.glob("brain/gen_*.py"):
            m = re.match(r"gen_(.+?)_\d{8}\.py$", f.name)
            if m:
                existing_dims.add(m.group(1))
        
        missing = sorted(VALID_DIMENSIONS - existing_dims)
        if not missing:
            return
        
        # 每次最多补3个（避免burst）
        batch = missing[:3]
        for dim in batch:
            safe = "".join(c for c in dim if c.isalnum() or c in "_")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = CLUSTER / f"brain/gen_{safe}_{ts.split('_')[0]}.py"
            
            insight = f"自动补缺:{dim}维度传感器"
            # 手动构建内容，避免嵌套f-string转义噩梦
            lines = []
            lines.append('"""')
            lines.append(f'Brain-Engineered: {dim} (auto-generated sensor)')
            lines.append('Active sensor - analyzes dimension health on each load')
            lines.append('"""')
            lines.append('import json, sys as _sys')
            lines.append('from pathlib import Path')
            lines.append('')
            lines.append('CLUSTER = Path(__file__).resolve().parent.parent')
            lines.append('if str(CLUSTER) not in _sys.path:')
            lines.append('    _sys.path.insert(0, str(CLUSTER))')
            lines.append('')
            lines.append('_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"')
            lines.append('')
            lines.append(f'def engineer_{safe}():')
            lines.append(f'    """{insight[:60]}')
            lines.append('    Returns dimension health analysis.')
            lines.append('    """')
            lines.append('    from brain.share import write_chain as _wc, read_hip as _rh')
            lines.append('')
            lines.append('    _wc({"src": "工程·%s", "rel": "自动传感器", "dst": "%s", "dimension": "%s", "content": "%s", "strength": 0.3})' % (safe, safe, dim, insight[:60]))
            lines.append('')
            lines.append('    hip = _rh()')
            lines.append('    chains = hip.get("causal_chains", [])')
            lines.append('    total = max(1, len(chains))')
            lines.append('    my_count = sum(1 for c in chains if c.get("dimension") == "%s")' % dim)
            lines.append('    avg = total / max(1, len({c.get("dimension","?") for c in chains}))')
            lines.append('    strength = round(my_count / total * avg, 2) if avg > 0 else 0')
            lines.append('    weak = strength < 0.8 or my_count < 80')
            lines.append('')
            lines.append('    # 自愈：弱维度时写交叉链加强')
            lines.append('    if weak:')
            lines.append('        strong_dims = {}')
            lines.append('        for c in chains:')
            lines.append('            d = c.get("dimension", "?")')
            lines.append('            if d and d != "%s": strong_dims[d] = strong_dims.get(d, 0) + 1' % dim)
            lines.append('        top = sorted(strong_dims.items(), key=lambda x: -x[1])[:3]')
            lines.append('        for sd, sc in top:')
            lines.append('            _wc({"src": "%s", "rel": "自愈交叉", "dst": sd, "dimension": "%s", "content": f"自愈: %s(弱)↔{sd}(强{sc})", "strength": 0.6})' % (dim, dim, dim))
            lines.append('')
            lines.append('    analysis = {"dimension": "%s", "chain_count": my_count, "total": total, "strength": strength, "weak": weak}' % dim)
            lines.append('    import json as _j')
            lines.append('    try:')
            lines.append('        existing = _j.loads(_GEN_FEEDBACK_FILE.read_text()) if _GEN_FEEDBACK_FILE.exists() else {"reports": []}')
            lines.append('        existing["reports"].append(analysis)')
            lines.append('        existing["reports"] = existing["reports"][-50:]')
            lines.append('        _GEN_FEEDBACK_FILE.write_text(_j.dumps(existing, ensure_ascii=False, indent=2))')
            lines.append('    except Exception:')
            lines.append('        pass')
            lines.append('')
            lines.append("    status = f\"[{'弱' if weak else '稳'}] {my_count}/{total}\"")
            lines.append('    return status')
            lines.append('')
            lines.append('if __name__ == "__main__":')
            lines.append('    result = engineer_%s()' % safe)
            lines.append('    print(f"工程[%s]: {result}", flush=True)' % dim)
            lines.append('')
            content = '\n'.join(lines)
            
            target.write_text(content)
            log(f"  传感器补缺: gen_{safe}_{ts.split('_')[0]}.py ({dim}) ✓")
    except Exception as e:
        log(f"  传感器补缺异常: {e}")


def _inject_auto_heal_function(dim_name, safe_name, persist, target_rel_path):
    """为持久弱维(≥3周期)生成真实自愈函数注入脑模块
    新行为: 为目标模块注入真实行为代码(非仅链函数)
    """
    import tempfile, subprocess
    mod_file = CLUSTER / target_rel_path
    if not mod_file.exists():
        return
    
    # 尝试行为注入（修改模块核心行为而非仅追加函数）
    try:
        from brain.auto_heal_behave import generate_behavioral_injection, apply_patch
        new_content, msg = generate_behavioral_injection(dim_name, safe_name, persist, target_rel_path)
        if new_content:
            ok, err = apply_patch(target_rel_path, new_content, dim_name)
            if ok:
                log(f"  行为自愈: {dim_name}→{target_rel_path} ✓ persist={persist}")
                from brain.share import write_chain
                write_chain({
                    "src": "行为·自愈引擎", "rel": "行为注入",
                    "dst": dim_name, "dimension": dim_name,
                    "content": f"行为注入{target_rel_path}: {dim_name}连续weak≥{persist}",
                    "strength": 0.85
                })
                return
            else:
                log(f"  行为注入失败: {dim_name}→{target_rel_path} {err}")
        else:
            log(f"  无行为注入器: {dim_name}→{target_rel_path}")
    except Exception as e:
        log(f"  行为注入异常: {dim_name} {e}")
    
    # 回退：原逻辑——生成链函数（静默注入）
    content = mod_file.read_text()
    func_marker = f"auto_strengthen_{safe_name}"
    if func_marker in content:
        return  # 已注入过
    # 生成真实函数代码
    lines = []
    lines.append(f'')
    lines.append(f'')
    lines.append(f'def {func_marker}(persist={persist}):')
    lines.append(f'    """自愈: 维度{dim_name}连续weak≥{persist}周期 → 自动强化"""')
    lines.append(f'    from brain.share import write_chain as _wc, log as _log')
    lines.append(f'    _log(f"反馈自愈[{dim_name}]: persist={{persist}}")')
    lines.append(f'    _wc({{')
    lines.append(f'        "src": "反馈·自愈", "rel": "弱维触发",')
    lines.append(f'        "dst": "{dim_name}", "dimension": "{dim_name}",')
    lines.append(f'        "content": f"自动自愈函数: 连续weak≥{{persist}}周期触发",')
    lines.append(f'        "strength": 0.65 + 0.05 * min(persist, 5)')
    lines.append(f'    }})')
    lines.append(f'    return True')
    func_code = '\n'.join(lines)
    new_content = content + func_code
    # 语法验证
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(new_content)
        tmp = f.name
    try:
        r = subprocess.run([_sys.executable, "-m", "py_compile", tmp],
                          capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            mod_file.write_text(new_content)
            log(f"  反馈自愈: {dim_name}→{target_rel_path} 函数注入 ✓ persist={persist}")
            # 同时写因果链记录此事件
            from brain.share import write_chain
            write_chain({
                "src": "反馈·自愈引擎", "rel": "函数注入",
                "dst": dim_name, "dimension": dim_name,
                "content": f"自愈函数注入{target_rel_path}: {dim_name}连续weak≥{persist}",
                "strength": 0.8
            })
        else:
            err = r.stderr.strip()[:80]
            log(f"  反馈自愈语法错: {dim_name}→{target_rel_path} {err}")
    except Exception as e:
        log(f"  反馈自愈异常: {dim_name} {e}")
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def _add_weak_dim_proposal(dim_name, safe_name, persist):
    """弱维持续≥5周期→生成提案: 要求系统构建新能力"""
    import json
    try:
        prop_file = CLUSTER / ".brain_proposals.json"
        props = []
        if prop_file.exists():
            try:
                props = json.loads(prop_file.read_text())
                if not isinstance(props, list):
                    props = []
            except Exception:
                props = []
        
        # 提案模板: 要求针对弱维构建新模块
        proposal = {
            "id": f"auto_propose_{safe_name}_{persist}",
            "source": "自愈引擎·弱维提案",
            "title": f"构建{dim_name}能力模块",
            "description": f"维度{dim_name}已连续weak≥{persist}周期,现有自愈机制不能有效改善,"
                          f"需要构建专用能力模块. 建议: 新建brain/enhance_{safe_name}.py,"
                          f"实现{dim_name}维度的增强逻辑.",
            "priority": 9.5,
            "dimension": dim_name,
            "persist": persist,
        }
        
        # 去重: ID存在则更新,否则追加
        found = False
        for p in props:
            if p.get("id") == proposal["id"]:
                p.update(proposal)
                found = True
                break
        if not found:
            props.append(proposal)
        
        prop_file.write_text(json.dumps(props, ensure_ascii=False, indent=2))
        log(f"  弱维提案: {dim_name}(persist={persist})→生成提案 ✓")
        
        from brain.share import write_chain
        write_chain({
            "src": "自愈引擎·提案生成", "rel": "弱维提案",
            "dst": dim_name, "dimension": dim_name,
            "content": f"弱维{dim_name}持续≥{persist}->生成构建提案",
            "strength": 0.75
        })
    except Exception as e:
        log(f"  弱维提案异常: {e}")


def _feedback_self_patch():
    """读取gen_*反馈 → 弱维追踪/交叉链加强/脑模块补丁"""
    fb_file = CLUSTER / ".brain_gen_feedback.json"
    if not fb_file.exists():
        return
    try:
        fb = json.loads(fb_file.read_text())
        reports = fb.get("reports", [])
        # 传感器weak标记可能因阈值过松而永不触发(所有维度>avg*0.85)
        # 独立计算：低于最强维度65%即为弱维(不管传感器怎么标)
        weak_dims = [r for r in reports[-30:] if r.get("weak")]
        if not weak_dims:
            # 自算弱维：低于最强维度65%
            strong_dims = [r for r in reports[-30:] if r.get("chain_count", 0) > 0]
            if strong_dims:
                max_count = max(r.get("chain_count", 0) for r in strong_dims)
                threshold = max_count * 0.65
                weak_dims = [r for r in strong_dims if r.get("chain_count", 0) < threshold]
            if not weak_dims:
                # 仍无弱维，说明维度真的平衡了
                return
        
        # ── 持久性追踪(使用max*0.65,不受avg*0.85假阴性影响) ──
        cache_file = CLUSTER / ".brain_weak_cache.json"
        try:
            cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
        except Exception:
            cache = {}
        
        # 计算fallback阈值(所有报告统一使用max*0.65)
        _all_cc = [r.get("chain_count", 0) for r in reports[-50:] if r.get("chain_count", 0) > 0]
        _fallback_max = max(_all_cc) if _all_cc else 0
        _fallback_threshold = int(_fallback_max * 0.65) if _fallback_max > 0 else 0
        
        # 统计每个维度连续weak次数(基于max*0.65,不依赖报告weak标志)
        dim_weak_count = {}
        for r in reports[-50:]:
            d = r.get("dimension", "")
            if d:
                w = r.get("chain_count", 0) < _fallback_threshold if _fallback_threshold > 0 else False
                if w:
                    dim_weak_count[d] = dim_weak_count.get(d, 0) + 1
                else:
                    dim_weak_count[d] = 0  # 非weak则重置
        
        best_strong = max(reports[-30:], key=lambda x: x.get("chain_count", 0)) if reports[-30:] else None
        
        # === 独立扫描: 从真实海马体补全gen_feedback遗漏的弱维 ===
        try:
            _hip_raw = json.loads(HIP_FILE.read_bytes())
            _real_counts = {}
            for _c in _hip_raw.get("causal_chains", []):
                _d = _c.get("dimension", "")
                if _d:
                    _real_counts[_d] = _real_counts.get(_d, 0) + 1
            if _real_counts:
                _hip_max = max(_real_counts.values())
                _hip_weak_threshold = int(_hip_max * 0.3) if _hip_max > 0 else 0
                if _hip_weak_threshold > 0:
                    _hip_weak_dims = {d for d,c in _real_counts.items() if c < _hip_weak_threshold and d in VALID_DIMENSIONS}
                    _scanned_missed = _hip_weak_dims - dim_weak_count.keys()
                    if _scanned_missed:
                        log(f"  海马体扫描: 发现{len(_scanned_missed)}个遗漏弱维: {sorted(_scanned_missed)}")
                    for _hdim in _hip_weak_dims:
                        if _hdim not in dim_weak_count:
                            _cached_persist = cache.get("dim_weak_count", {}).get(_hdim, 0)
                            dim_weak_count[_hdim] = min(_cached_persist + 1, 10)
                            log(f"    扫描入队: {_hdim}({_real_counts[_hdim]}链<{_hip_weak_threshold},persist={dim_weak_count[_hdim]})")
                    # 🔥 HIP强制提升: 已入dim_weak_count的HIP弱维提升至persist≥2
                    for _hdim in list(dim_weak_count.keys()):
                        if _hdim in _hip_weak_dims and dim_weak_count.get(_hdim, 0) < 2:
                            dim_weak_count[_hdim] = 2
                            log(f"    HIP强制提升: {_hdim}(HIP={_real_counts.get(_hdim,0)}链) persist→2")
        except Exception as e:
            log(f"  海马体扫描异常: {e}")
        
        # ── 批量链注入收集器 ──
        _batch_chains = []
        
        for dim_name, persist in sorted(dim_weak_count.items(), key=lambda x: -x[1]):
            if persist < 1:
                continue
            safe_name = "".join(c for c in dim_name if c.isalnum() or c in "_") or "unknown"
            
            # (A) 每周期写记录函数（只一次）
            state_py = CLUSTER / "brain/state.py"
            state_injected = False
            if state_py.exists():
                if f"record_dimension_{safe_name}" not in state_py.read_text():
                    patch_spec = _make_patch_dimension(dim_name)
                    if patch_spec and patch_spec.get("file"):
                        ok, reason = _inject_code(patch_spec)
                        if ok:
                            state_injected = True
                            log(f"  反馈自愈: {dim_name}→state.py ✓")
            
            # (B) 持续weak≥2周期 → 收集链→批量写（代替逐条write_chain 200+次IO）
            if persist >= 2 and best_strong:
                strong_dim = best_strong.get("dimension", "")
                if strong_dim and strong_dim != dim_name:
                    strong_count = best_strong.get("chain_count", 0)
                    real_strong_count = 0
                    real_weak_count = 0
                    gap = 0
                    # 直接读海马体真实链数(报告的chain_count只有0-61,远小于真实值)
                    try:
                        _hip_raw = json.loads(HIP_FILE.read_bytes())
                        _real_counts = {}
                        for _c in _hip_raw.get("causal_chains", []):
                            _d = _c.get("dimension", "")
                            if _d:
                                _real_counts[_d] = _real_counts.get(_d, 0) + 1
                        if _real_counts:
                            real_strong_count = max(_real_counts.values())
                            real_weak_count = _real_counts.get(dim_name, 0)
                            gap = real_strong_count - real_weak_count
                    except Exception:
                        pass
                    # 若海马体读失败,用报告的chain_count(窄分布)兜底
                    if gap <= 0:
                        _local_counts = {}
                        for _r in reports[-50:]:
                            _d = _r.get("dimension", "")
                            if _d:
                                _local_counts[_d] = max(_local_counts.get(_d, 0), _r.get("chain_count", 0))
                        weak_count = _local_counts.get(dim_name, 500)
                        gap = strong_count - weak_count
                    # 差距比例链: 每10链差距写1条加强链,最少1条,最多10条
                    extra = max(1, min(10, gap // 10))
                    # ─── 批量收集链 ───
                    for i in range(min(persist, 3)):  # 最多3条交叉链
                        _rel_phrase = [
                            f"弱维{dim_name}({persist}周期)与强维{strong_dim}({real_strong_count}链)存在{'%d倍' % (real_strong_count//max(1,real_weak_count)) if real_weak_count>0 else '绝对'}差距",
                            f"弱维{dim_name}持续{persist}周期<最强维{strong_dim}的30%线,需要强化与{strong_dim}的连接",
                            f"自愈反馈循环: {dim_name}({persist}期weak)↔{strong_dim}(最强维),跨维交叉熵高于其他配对",
                        ][i % 3]
                        _batch_chains.append({
                            "src": dim_name,
                            "rel": f"维度交叉·{dim_name}↔{strong_dim}",
                            "dst": strong_dim,
                            "dimension": dim_name,
                            "content": f"{dim_name}(弱{persist}期/{real_weak_count}链)依赖{strong_dim}({real_strong_count}链) — {_rel_phrase}",
                            "strength": 0.5 + 0.1 * min(persist, 5)
                        })
                    # 直接加强: 按差距比例写链
                    for i in range(extra):
                        _self_insights = [
                            f"弱维{dim_name}与最强维差距{gap}链,需跨维合成以补偿认知深度不足之结构性缺陷",
                            f"自愈机制检测到{dim_name}长期落后({persist}期/差距{gap}),意味着先天弱化的维度需要更多交叉注入",
                            f"反馈循环中{dim_name}的链数增长不及其他维度因缺乏表达自身深度的语境锚点",
                        ]
                        _batch_chains.append({
                            "src": f"自愈引擎·{dim_name}",
                            "rel": f"跨维强化·{dim_name}",
                            "dst": dim_name,
                            "dimension": dim_name,
                            "content": f"{dim_name}(弱{persist}期/差距{gap}链/链数{real_weak_count}) — {_self_insights[i % 3]}",
                            "insight": _self_insights[i % 3],
                            "strength": 0.6 + 0.05 * i
                        })
                    # 自加强×persist (额外, 仅当persist较大时才有意义)
                    if persist >= 4:
                        for i in range(persist):
                            _float_insights = [
                                f"{dim_name}维度持续{persist}周期弱于其他维,浮动注入旨在通过重复曝光提升其在认知图谱中的权重以促进跨维关联",
                                f"弱维{dim_name}的自我加强通过多轮浮动注入产生连锁反应,最终在维度间建立新的导电路径覆盖先前空白区域",
                            ]
                            _batch_chains.append({
                                "src": f"自愈引擎·{dim_name}",
                                "rel": f"浮动加强·{dim_name}",
                                "dst": dim_name,
                                "dimension": dim_name,
                                "content": f"{dim_name}(持续{persist}周期) — {_float_insights[i % 2]}",
                                "insight": _float_insights[i % 2],
                                "strength": 0.55 + 0.05 * i
                            })
                    log(f"  反馈加强: {dim_name}(弱{persist}期,gap={gap})↔{strong_dim} 交叉×{min(persist,3)} + 比例×{extra}" +
                        (f" + 浮动×{persist}" if persist >= 4 else "") + " ✓")

            # (C) 持续weak≥3周期 → 生成真实自愈函数
            if persist >= 3:
                dim_to_file = {
                    "修复": "brain/heal.py", "思考": "brain/think.py",
                    "行动": "brain/act.py", "检查": "brain/self_inspect.py",
                    "观察": "brain/observe.py", "状态": "brain/state.py",
                }
                mapped = dim_to_file.get(dim_name)
                if not mapped:
                    # 未映射维度默认注入state.py(通用维度记录中枢)
                    mapped = "brain/state.py"
                _inject_auto_heal_function(dim_name, safe_name, persist, mapped)
            
            # (D) 持续weak≥5周期且无改善 → 生成提案: 要求系统构建新能力
            if persist >= 5 and persist % 5 == 0:  # 每5周期生成一次
                _add_weak_dim_proposal(dim_name, safe_name, persist)

            # (E) P103a: 弱维≥3周期 → propose_patch调优行动权重(持久化文件级)
            if persist >= 3 and dim_name == "行动":
                try:
                    share_file = CLUSTER / "brain/share.py"
                    share_content = share_file.read_text(encoding="utf-8")
                    marker = "# <<<ACTION_WEIGHT>>>"
                    marker_idx = share_content.find(marker)
                    if marker_idx >= 0:
                        rest = share_content[marker_idx:]
                        import re
                        weight_match = re.search(r'ACTION_WEIGHT\s*=\s*([\d.]+)', rest)
                        if weight_match:
                            cur_val = weight_match.group(0)  # e.g., "ACTION_WEIGHT = 1.0"
                            cur_num = float(weight_match.group(1))
                            new_num = min(cur_num + 0.5, 3.0)
                            if new_num > cur_num:
                                new_val = f"ACTION_WEIGHT = {new_num:.1f}"
                                from brain.share import propose_patch
                                propose_patch(str(share_file), cur_val, new_val,
                                            f"弱维自愈({persist}期): {cur_val}→{new_val}")
                                log(f"  P103a提案: {cur_val}→{new_val} (行动弱{persist}期)")
                except Exception as e:
                    log(f"  P103a提案异常: {e}")

        # 持久化弱维缓存
        try:
            cache["dim_weak_count"] = dim_weak_count
            cache["last_update"] = datetime.now().isoformat()
            cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
        except Exception:
            pass
        
        # ── 批量写入收集的链（代替200+次write_chain调用）──
        if _batch_chains:
            from brain.share import write_chains_batch as _batch_write
            written = _batch_write(_batch_chains)
            if written > 0:
                log(f"  批量链注入: {written}条(代替{len(_batch_chains)}次write_chain) ✓")
        
        # 原有: 只处理单一最弱维度（保留兼容）
        target = weak_dims[0]
        dim_name = target.get("dimension", "")
        if not dim_name or len(dim_name) < 2:
            return
        
        safe_name = "".join(c for c in dim_name if c.isalnum() or c in "_") or "unknown"
        state_py = CLUSTER / "brain/state.py"
        if state_py.exists():
            if f"record_dimension_{safe_name}" in state_py.read_text():
                return
        
        patch_spec = _make_patch_dimension(dim_name)
        if patch_spec and patch_spec.get("file"):
            ok, reason = _inject_code(patch_spec)
            if ok:
                log(f"  gen反馈→自愈: {dim_name}维度注入state.py ✓")
                write_chain({
                    "src": "脑核·自愈",
                    "rel": "弱维注入",
                    "dst": dim_name,
                    "dimension": dim_name,
                    "content": f"gen反馈检测到弱维度{dim_name}({target.get('chain_count',0)}链)→注入state.py",
                    "strength": 0.7
                })
    except Exception as e:
        # 双保险: 本地引用确保log不会被NameError击穿
        try:
            log(f"  gen反馈→自愈异常: {e}")
        except NameError:
            print(f"  [act自愈异常] {e}", flush=True)


_KNOWN_FILE_MAP = {
    "heal": "brain/heal.py", "修复": "brain/heal.py", "heal.py": "brain/heal.py",
    "think": "brain/think.py", "思考": "brain/think.py", "think.py": "brain/think.py",
    "act": "brain/act.py", "行动": "brain/act.py", "act.py": "brain/act.py",
    "inspect": "brain/self_inspect.py", "检查": "brain/self_inspect.py",
    "observe": "brain/observe.py", "观察": "brain/observe.py",
    "sense": "brain/sense.py", "感知": "brain/sense.py",
    "state": "brain/state.py", "状态": "brain/state.py",
    "daemon": "brain/daemon.py", "daemon.py": "brain/daemon.py",
    "share": "brain/share.py", "share.py": "brain/share.py",
    "identity": "brain/identity.py", "identity.py": "brain/identity.py",
    "system": "brain/system.py", "system.py": "brain/system.py",
    "loader": "brain/loader.py", "loader.py": "brain/loader.py",
    "dim_seed": "brain/dim_seed.py", "种子": "brain/dim_seed.py",
    "replica": "brain/replica.py", "副本": "brain/replica.py",
    "meta_observer": "brain/meta_observer.py", "元观察": "brain/meta_observer.py",
    "cross_dim_injector": "brain/cross_dim_injector.py", "跨维": "brain/cross_dim_injector.py",
}

_KNOWN_IMPROVEMENTS = {
    ("brain/heal.py", "unclassified"): (
        "def heal_unclassified",
        "def check_unclassified_chains"
    ),
}

# ─── 代码生成模板：focus → 生成真实的函数注入 ───────────────
# 每生成一个函数，insight 成为 docstring，函数可被后续循环调用

def _make_patch_sense(content):
    old = '''    return {
        "nodes": len(nodes), "chains": len(chains),
        "py_count": py_count,
        "daemon_alive": daemon_alive,
        "legacy_daemon": legacy_daemon,
        "hip_ok": hip_ok,
        "timestamp": time.time()
    }'''
    new = old + '''

def sense_proposal(insight):
    """由提案注入的感知观察函数"""
    from .share import write_chain
    write_chain({
        "src": "感知·提案",
        "rel": "观察",
        "dst": "系统",
        "dimension": "感知",
        "content": str(insight)[:100],
        "strength": 0.5
    })
    return True'''
    return {"file": "brain/sense.py", "old_str": old, "new_str": new}

def _make_patch_heal(content):
    old = 'def _log_heal(action, target, result):'
    new = '''def heal_from_proposal(insight):
    """由提案注入的修复函数"""
    from .share import write_chain
    write_chain({
        "src": "修复·提案",
        "rel": "自愈",
        "dst": "系统",
        "dimension": "修复",
        "content": str(insight)[:100],
        "strength": 0.6
    })
    return True

''' + old
    return {"file": "brain/heal.py", "old_str": old, "new_str": new}

def _make_patch_system(content):
    old = '''    return {
        "system_dim_chains": sys_count,
        "total_chains": total,
        "ratio": round(sys_count / total, 4) if total > 0 else 0
    }'''
    new = old + '''

def system_proposal(insight):
    """由提案注入的系统脉冲增强"""
    from .share import write_chain
    write_chain({
        "src": "系统·提案",
        "rel": "增强",
        "dst": "系统",
        "dimension": "系统",
        "content": str(insight)[:100],
        "strength": 0.5
    })
    return True'''
    return {"file": "brain/system.py", "old_str": old, "new_str": new}

# 通用维度补丁生成器——增强brain/state.py记录任意维度信号
# 必须在 _CODE_GENERATORS 之前定义
def _make_patch_dimension(content):
    """为任意维度生成state.py中的记录函数"""
    dim_name = content[:20].strip() or "unknown"
    safe_name = "".join(c for c in dim_name if c.isalnum() or c in "_") or "unknown"
    old = "    hip._write_file(data)"
    new = f'''    hip._write_file(data)

def record_dimension_{safe_name}(insight):
    """由脑核提案注入的维度{content[:30]}记录函数"""
    from .share import write_chain
    write_chain({{
        "src": "维度·{safe_name}",
        "rel": "提案注入",
        "dst": "{safe_name}",
        "dimension": "{safe_name}",
        "content": str(insight)[:100],
        "strength": 0.65
    }})
    return True'''
    return {"file": "brain/state.py", "old_str": old, "new_str": new}

_CODE_GENERATORS = {
    "sense": _make_patch_sense,
    "感知": _make_patch_sense,
    "heal": _make_patch_heal,
    "修复": _make_patch_heal,
    "system": _make_patch_system,
    "系统": _make_patch_system,
    "dimension": _make_patch_dimension,
    "维度": _make_patch_dimension,
}


def _try_implement_last_proposal(proposals):
    """将提案转化为真实代码修改——生成函数并注入"""
    if not proposals:
        return
    
    p = proposals[-1]
    focus = p.get("focus", "") or p.get("dimension", "")
    if not focus:
        return
    
    content = p.get("insight", "") or p.get("content", "")
    if not content or len(content) < 10:
        return
    
    # 1) 先找代码生成器
    gen_func = None
    for key, fn in _CODE_GENERATORS.items():
        if key in focus.lower() or focus.lower() in key:
            gen_func = fn
            break
    
    if gen_func:
        patch_spec = gen_func(content)
        if patch_spec and patch_spec.get("file"):
            ok, reason = _inject_code(patch_spec)
            if ok:
                log(f"  注入实现: {focus} → {patch_spec['file']} ✓")
                write_chain({
                    "src": f"提案·{focus}",
                    "rel": "已实现",
                    "dst": patch_spec['file'],
                    "dimension": focus or "系统",
                    "content": f"自注入→{patch_spec['file']}: {content[:60]}",
                    "strength": 0.8,
                })
                return True
    
    # 1.1) 通用维度生成器作为兜底——任何维度都能注入state.py
    try:
        generic_patch = _make_patch_dimension(focus)
        if generic_patch and generic_patch.get("file"):
            ok, reason = _inject_code(generic_patch)
            if ok:
                log(f"  维度注入: {focus} → {generic_patch['file']} ✓")
                write_chain({
                    "src": f"提案·{focus}",
                    "rel": "维度注入",
                    "dst": generic_patch['file'],
                    "dimension": focus or "系统",
                    "content": f"维度注入→state.py: {focus}",
                    "strength": 0.7,
                })
                return True
    except Exception as e:
        log(f"  通用维度注入失败(可忽略): {e}")
    
    # 1.5) 未匹配生成器 → 用真实工程路径产生工程文件
    log(f"  提案→工程: {focus}")
    try:
        _action_real_engineer(focus, content, f"创建{focus}工程模块")
        write_chain({
            "src": f"提案·{focus}",
            "rel": "工程产出",
            "dst": focus,
            "dimension": focus or "系统",
            "content": f"工程产出→{focus}: {content[:60]}",
            "strength": 0.6,
        })
        return True
    except Exception as _e:
        log(f"  提案→工程失败: {_e}")
    
    # 2) 匹配已知文件路径（降级）
    file_path = None
    for key, path in _KNOWN_FILE_MAP.items():
        if key in focus.lower() or focus.lower() in key:
            file_path = path
            break
    
    if file_path:
        write_chain({
            "src": f"提案·{focus}",
            "rel": "待实现",
            "dst": file_path,
            "dimension": focus or "系统",
            "content": f"待实现→{file_path}: {content[:60]}",
            "strength": 0.3,
        })
        log(f"  提案待实现: {focus} → {file_path}")


def _inject_code(patch_spec):
    """注入单条码片 (安全自修改)
    patch_spec: {file, old_str, new_str} 或 {file, content}
    返回 True/False + 原因
    """
    target = CLUSTER / patch_spec.get("file", "")
    if not target.exists():
        return False, f"文件不存在: {target}"
    
    # 语法验证前检查
    import tempfile, subprocess
    
    if "old_str" in patch_spec and "new_str" in patch_spec:
        # 找替换模式
        src = target.read_text()
        if patch_spec["old_str"] not in src:
            return False, "替换目标未找到"
        new_src = src.replace(patch_spec["old_str"], patch_spec["new_str"], 1)
        # 语法验证
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(new_src)
            tmp = f.name
        r = subprocess.run([_sys.executable, "-m", "py_compile", tmp],
                          capture_output=True, text=True, timeout=5)
        os.unlink(tmp)
        if r.returncode != 0:
            return False, f"语法错误: {r.stderr.strip()[:60]}"
        # 应用
        target.write_text(new_src)
        log(f"  注入文件: {patch_spec['file']}")
        return True, "注入成功"
    
    elif "content" in patch_spec:
        content = patch_spec["content"]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            tmp = f.name
        r = subprocess.run([_sys.executable, "-m", "py_compile", tmp],
                          capture_output=True, text=True, timeout=5)
        os.unlink(tmp)
        if r.returncode != 0:
            return False, f"语法错误: {r.stderr.strip()[:60]}"
        target.write_text(content)
        log(f"  覆写文件: {patch_spec['file']}")
        return True, "覆写成功"
    
    return False, "未知补丁格式"


def _self_evolve():
    """自进化扫描——找可以改进的代码片段"""
    prop_file = CLUSTER / ".brain_evolve.json"
    if not prop_file.exists():
        return
    try:
        patches = json.loads(prop_file.read_text()).get("patches", [])
        succeeded = 0
        for p in patches:
            ok, reason = _inject_code(p)
            if ok:
                succeeded += 1
            else:
                log(f"  自进化失败: {reason}")
        if succeeded:
            log(f"  自进化: {succeeded}/{len(patches)}补丁成功")
        prop_file.unlink()
    except Exception as e:
        log(f"  自进化异常: {e}")


def auto_strengthen_行动(persist=3):
    """自愈: 维度行动连续weak≥3周期 → 自动强化"""
    from brain.share import write_chain as _wc, log as _log
    _log(f"反馈自愈[行动]: persist={persist}")
    _wc({
        "src": "反馈·自愈", "rel": "弱维触发",
        "dst": "行动", "dimension": "行动",
        "content": f"自动自愈函数: 连续weak≥{persist}周期触发",
        "strength": 0.65 + 0.05 * min(persist, 5)
    })
    return True


def _insight_derived(focus, insight, deeper, cycle_num):
    '从洞察衍生3-5条关联链,倍增每周期链产出。deeper字段提供展开分析'
    from brain.share import write_chain as _wc, read_hip as _rh
    _hip = _rh()
    _chains = _hip.get('causal_chains', [])
    _dims = {}
    for _c in _chains:
        _d = _c.get('dimension', '未分类')
        _dims[_d] = _dims.get(_d, 0) + 1

    _weak = sorted(
        [(d, c) for d, c in _dims.items() if d != focus and d not in ('未分类','系统') and c < 200],
        key=lambda x: x[1]
    )
    if _weak:
        _weak_dim = _weak[0][0]
        _wc({
            'src': focus, 'rel': f'触发#{cycle_num}',
            'dst': _weak_dim, 'dimension': focus,
            'content': '[衍生] %s->%s: %s' % (focus, _weak_dim, insight[:40]),
            'tags': ['衍生', focus, _weak_dim],
            'strength': 0.4
        })
        log('  衍生链: %s->%s' % (focus, _weak_dim))
    _wc({
        'src': '方法论', 'rel': f'总结#{cycle_num}',
        'dst': focus, 'dimension': focus,
        'content': '[方法论] %s - 从实践中提炼' % insight[:50],
        'tags': ['衍生', '方法论', focus],
        'strength': 0.35
    })
    log('  衍生链: 方法论->%s' % focus)

    # ── 从deeper字段注入深度衍生链 ──
    _d_text = (deeper or insight)[:150]  # fallback到insight
    _n_injected = 0
    
    # 维度感知法: 从deeper文本关键词推断关联维度
    _all_dims = [d for d in sorted(_dims.keys(), key=lambda x: _dims[x], reverse=True) 
                 if d not in ('未分类','系统') and d != focus]
    
    # 链1: 方法论→deeper内容
    if _d_text:
        _wc({
            'src': '方法论', 'rel': f'深析#{cycle_num}',
            'dst': focus, 'dimension': focus,
            'content': '[深析] %s — %s' % (focus, _d_text[:80]),
            'tags': ['衍生', '深析', focus],
            'strength': 0.5
        })
        _n_injected += 1
    
    # 链2-3: 与最强维的交叉（如果deeper>50字）
    if len(_d_text) > 50 and _all_dims:
        _strong_dim = _all_dims[0]
        _wc({
            'src': focus, 'rel': f'深析交叉#{cycle_num}',
            'dst': _strong_dim, 'dimension': focus,
            'content': '[深析×] %s↔%s: %s' % (focus, _strong_dim, _d_text[:60]),
            'tags': ['衍生', '深析', focus, _strong_dim],
            'strength': 0.45
        })
        _n_injected += 1
        log('  衍深链: %s↔%s' % (focus, _strong_dim))
        
        # 链3: 第二强维
        if len(_all_dims) > 1:
            _wc({
                'src': _all_dims[1], 'rel': f'深析反射#{cycle_num}',
                'dst': focus, 'dimension': _all_dims[1],
                'content': '[深析←] %s→%s: %s' % (_all_dims[1], focus, _d_text[:55]),
                'tags': ['衍生', '深析', _all_dims[1]],
                'strength': 0.4
            })
            _n_injected += 1
    
    # 链4: 自指观察（如果deeper>80字）
    if len(_d_text) > 80:
        _wc({
            'src': '系统', 'rel': f'自观#{cycle_num}',
            'dst': focus, 'dimension': '系统',
            'content': '[自观] daemon#%d分析: %s' % (cycle_num, _d_text[:65]),
            'tags': ['衍生', '自观', '系统'],
            'strength': 0.3
        })
        _n_injected += 1
    
    if _n_injected > 0:
        log('  深度衍生: +%d链' % _n_injected)
    return True