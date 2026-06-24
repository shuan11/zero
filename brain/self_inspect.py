"""
brain/inspect.py — 系统化自我检查模块
照应自身缺陷：让系统看见自己的全部状态

每5个daemon周期运行一次，检查：
1. 脑核守护进程健康
2. 海马体完整性
3. 身份系统完整性
4. 关键文件完整性
5. 进程健康
6. 看门狗cron状态
7. Git repo健康
8. 元观察：系统是否在空转/死循环
"""

import json, os, sys, time, subprocess
from pathlib import Path
from brain.share import CLUSTER, log, write_chain, read_hip
from brain.identity import VALID_DIMENSIONS, sanitize_dim, is_identity_intact

def check_daemon():
    """1) 脑核守护进程健康"""
    results = {"pass": True, "checks": []}
    # ext4路径优先（daemon 2.x），兼容集群目录
    ext4_pid = Path("/home/hjw123/.zero_brain/.brain.pid")
    pid_file = ext4_pid if ext4_pid.exists() else CLUSTER / ".brain.pid"
    state_file = CLUSTER / ".brain_state.json"
    
    # PID存在吗
    if not pid_file.exists():
        results["pass"] = False
        results["checks"].append({"name": "pid_file", "status": "FAIL", "detail": ".brain.pid不存在"})
        return results
    results["checks"].append({"name": "pid_file", "status": "PASS", "detail": "存在"})
    
    # 进程活着吗
    try:
        pid = int(pid_file.read_text().strip())
        alive = os.path.exists(f"/proc/{pid}") if sys.platform == "linux" else False
        if not alive:
            results["pass"] = False
            results["checks"].append({"name": "daemon_process", "status": "FAIL", 
                                       "detail": f"PID={pid} 但进程已死"})
            return results
        results["checks"].append({"name": "daemon_process", "status": "PASS", 
                                   "detail": f"PID={pid} 运行中"})
    except (ValueError, OSError):
        results["pass"] = False
        results["checks"].append({"name": "daemon_process", "status": "FAIL", "detail": "PID读取失败"})
        return results
    
    # State文件新鲜吗
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            ts = state.get("timestamp", 0)
            if isinstance(ts, str):
                from datetime import datetime
                ts = datetime.fromisoformat(ts).timestamp()
            age = time.time() - ts
            if age > 300:  # 5分钟没更新
                results["pass"] = False
                results["checks"].append({"name": "state_freshness", "status": "WARN",
                                           "detail": f"state文件{age:.0f}秒未更新"})
            else:
                results["checks"].append({"name": "state_freshness", "status": "PASS",
                                           "detail": f"cycle={state.get('cycle','?')} age={age:.0f}s"})
        except:
            results["checks"].append({"name": "state_freshness", "status": "WARN", "detail": "state文件损坏"})
    else:
        results["checks"].append({"name": "state_freshness", "status": "FAIL", "detail": "state文件不存在"})
    
    return results


def check_hippocampus():
    """2) 海马体完整性"""
    results = {"pass": True, "checks": []}
    hip_path = CLUSTER / "hippocampus_memory.json"
    
    if not hip_path.exists():
        results["pass"] = False
        results["checks"].append({"name": "hip_exists", "status": "FAIL", "detail": "海马体文件不存在"})
        return results
    results["checks"].append({"name": "hip_exists", "status": "PASS", "detail": "存在"})
    
    try:
        hip = json.loads(hip_path.read_text())
    except:
        results["pass"] = False
        results["checks"].append({"name": "hip_parse", "status": "FAIL", "detail": "JSON解析失败"})
        return results
    results["checks"].append({"name": "hip_parse", "status": "PASS", "detail": "JSON解析正常"})
    
    chains = hip.get("causal_chains", [])
    nodes = hip.get("nodes", [])
    results["checks"].append({"name": "hip_size", "status": "PASS", 
                               "detail": f"{len(chains)}链 {len(nodes)}节点"})
    
    # 检查非法维度
    bad_dims = set()
    for c in chains:
        d = c.get("dimension", "未分类")
        if not isinstance(d, str) or d not in VALID_DIMENSIONS:
            bad_dims.add(str(d))
    if bad_dims:
        results["pass"] = False
        results["checks"].append({"name": "hip_dimensions", "status": "FAIL",
                                   "detail": f"发现{len(bad_dims)}个非法维度: {', '.join(list(bad_dims)[:5])}"})
    else:
        results["checks"].append({"name": "hip_dimensions", "status": "PASS", "detail": "所有维度合法"})
    
    # 检查链格式
    malformed = 0
    for c in chains:
        if not isinstance(c, dict) or "content" not in c:
            malformed += 1
    if malformed > len(chains) * 0.1:  # 10%以上损坏
        results["pass"] = False
        results["checks"].append({"name": "hip_format", "status": "FAIL",
                                   "detail": f"{malformed}条链格式异常"})
    else:
        results["checks"].append({"name": "hip_format", "status": "PASS", 
                                   "detail": f"格式正常（{malformed}条异常）"})
    
    return results


def check_identity():
    """3) 身份系统完整性"""
    results = {"pass": True, "checks": []}
    
    id_path = CLUSTER / "identity.json"
    boot_path = CLUSTER / "boot.py"
    
    if not id_path.exists():
        results["pass"] = False
        results["checks"].append({"name": "identity_file", "status": "FAIL", "detail": "identity.json不存在"})
    elif not is_identity_intact():
        results["pass"] = False
        results["checks"].append({"name": "identity_file", "status": "FAIL", "detail": "identity.json不完整"})
    else:
        results["checks"].append({"name": "identity_file", "status": "PASS", "detail": "存在且完整"})
    
    if not boot_path.exists():
        results["pass"] = False
        results["checks"].append({"name": "boot_file", "status": "FAIL", "detail": "boot.py不存在"})
    else:
        try:
            import py_compile
            py_compile.compile(str(boot_path), doraise=True)
            results["checks"].append({"name": "boot_file", "status": "PASS", "detail": "语法正确"})
        except py_compile.PyCompileError:
            results["pass"] = False
            results["checks"].append({"name": "boot_file", "status": "FAIL", "detail": "boot.py语法错误"})
    
    return results


def check_files():
    """4) 关键文件完整性"""
    results = {"pass": True, "checks": []}
    required = [
        "brain/think.py", "brain/act.py", "brain/daemon.py", "brain/share.py",
        "brain/identity.py", "identity.json", "boot.py",
        "hippocampus_memory.json", "brain_watchdog.sh",
        ".brain_state.json", ".brain_focus.json",
    ]
    missing = []
    for f in required:
        p = CLUSTER / f
        if not p.exists():
            missing.append(f)
    if missing:
        results["pass"] = False
        results["checks"].append({"name": "required_files", "status": "FAIL",
                                   "detail": f"缺失{len(missing)}个: {', '.join(missing[:5])}"})
    else:
        results["checks"].append({"name": "required_files", "status": "PASS", "detail": "全部存在"})
    
    return results


def check_git():
    """5) Git repo健康"""
    results = {"pass": True, "checks": []}
    try:
        # 未提交变更
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=CLUSTER, capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            uncommitted = [l for l in r.stdout.split("\n") if l.strip()]
            if uncommitted:
                results["checks"].append({"name": "git_uncommitted", "status": "WARN",
                                           "detail": f"{len(uncommitted)}个未提交文件"})
            else:
                results["checks"].append({"name": "git_uncommitted", "status": "PASS", "detail": "干净"})
        
        # 最新提交
        r = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=CLUSTER, capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0 and r.stdout.strip():
            results["checks"].append({"name": "git_head", "status": "PASS",
                                       "detail": r.stdout.strip()[:60]})
    except Exception as e:
        results["checks"].append({"name": "git", "status": "WARN", "detail": str(e)[:40]})
    
    return results


def check_watchdog():
    """6) 看门狗cron状态"""
    results = {"pass": True, "checks": []}
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and "brain_watchdog" in r.stdout:
            results["checks"].append({"name": "watchdog_cron", "status": "PASS", "detail": "cron活跃"})
        else:
            results["checks"].append({"name": "watchdog_cron", "status": "WARN", "detail": "cron中无watchdog"})
    except:
        results["checks"].append({"name": "watchdog_cron", "status": "FAIL", "detail": "无法读取crontab"})
    
    # 看门狗日志
    wd_log = CLUSTER / ".brain_watchdog.log"
    if wd_log.exists():
        age = time.time() - wd_log.stat().st_mtime
        results["checks"].append({"name": "watchdog_log", "status": "PASS",
                                   "detail": f"日志{age:.0f}秒前更新"})
    else:
        results["checks"].append({"name": "watchdog_log", "status": "WARN", "detail": "看门狗日志不存在"})
    
    return results


def check_meta():
    """7) 元观察：系统是否空转/死循环"""
    results = {"pass": True, "checks": []}
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    
    if len(chains) < 10:
        results["checks"].append({"name": "meta_loop", "status": "PASS", "detail": "样本不足"})
        return results
    
    recent = chains[-30:]
    # 检查最后10条链的dimension是否有重复模式（表明空转）
    recent_dims = [c.get("dimension", "") for c in recent[-10:] if isinstance(c, dict)]
    
    # 如果最后10条中超过7条是同一维度→空转
    if recent_dims:
        from collections import Counter
        dim_counts = Counter(recent_dims)
        most_common = dim_counts.most_common(1)[0] if dim_counts else ("", 0)
        if most_common[1] >= 8:
            results["pass"] = False
            results["checks"].append({"name": "meta_loop", "status": "FAIL",
                                       "detail": f"最后10条链{most_common[1]}条集中在'{most_common[0]}'"})
        else:
            results["checks"].append({"name": "meta_loop", "status": "PASS",
                                       "detail": f"维度分布正常（最密集={most_common[0]}:{most_common[1]}条）"})
    
    # 检查连续相同insight
    recent_insights = [c.get("content", "")[:30] for c in recent[-5:] if isinstance(c, dict)]
    unique = set(recent_insights)
    if len(unique) <= 1 and len(recent_insights) >= 5:
        results["pass"] = False
        results["checks"].append({"name": "meta_stuck", "status": "FAIL",
                                   "detail": "最后5条insight完全相同→系统卡死"})
    else:
        results["checks"].append({"name": "meta_stuck", "status": "PASS",
                                   "detail": f"最近{len(unique)}个独特insight"})
    
    return results


def full_inspection():
    """运行全部检查，返回综合报告"""
    log("  🔍 全面自我检查...")
    
    results = {
        "timestamp": time.time(),
        "daemon": check_daemon(),
        "hippocampus": check_hippocampus(),
        "identity": check_identity(),
        "files": check_files(),
        "git": check_git(),
        "watchdog": check_watchdog(),
        "meta": check_meta(),
    }
    
    # 计算总分
    total_checks = 0
    failed = 0
    warned = 0
    for category, result in results.items():
        if category == "timestamp":
            continue
        if isinstance(result, dict):
            for check in result.get("checks", []):
                total_checks += 1
                if check["status"] == "FAIL":
                    failed += 1
                elif check["status"] == "WARN":
                    warned += 1
    
    results["summary"] = {
        "total_checks": total_checks,
        "passed": total_checks - failed - warned,
        "warned": warned,
        "failed": failed,
        "overall": "PASS" if failed == 0 else "IMPAIRED" if warned > 0 else "FAIL"
    }
    
    # 写入因果链
    if failed > 0:
        defects = []
        for cat, r in results.items():
            if isinstance(r, dict):
                for c in r.get("checks", []):
                    if c["status"] == "FAIL":
                        defects.append(f"{cat}:{c['name']}")
        write_chain({
            "src": "自我检查",
            "rel": "发现缺陷",
            "dst": "系统",
            "dimension": "系统",
            "content": f"自我检查发现{len(defects)}个缺陷: {'; '.join(defects[:3])}",
            "tags": ["检测", "缺陷", "系统"],
            "strength": 0.8
        })
        log(f"  ⚠️ 发现{failed}个失败 {warned}个警告")
    else:
        log(f"  ✓ 全部{total_checks}项检查通过")
    
    return results


def _generate_fix_proposals(results):
    """根据检查失败自动生成修复提案"""
    proposals_path = CLUSTER / ".brain_proposals.json"
    
    # 读取现有提案
    existing = {"proposals": [], "consumed": []}
    if proposals_path.exists():
        try:
            existing_raw = json.loads(proposals_path.read_text())
            if isinstance(existing_raw, dict):
                existing = existing_raw
            elif isinstance(existing_raw, list):
                # 兼容：文件是列表格式时包装为dict
                existing = {"proposals": existing_raw, "consumed": []}
        except:
            pass
    
    # 为每个FAIL生成提案
    new_proposals = []
    for cat, r in results.items():
        if not isinstance(r, dict):
            continue
        for c in r.get("checks", []):
            if c["status"] != "FAIL":
                continue
            # 生成修复提案
            prop = {
                "id": f"auto-fix-{cat}-{c['name']}-{int(time.time())}",
                "type": c['name'],
                "category": cat,
                "detail": c['detail'],
                "generated_by": "自我检查",
                "priority": "P0",
                "timestamp": time.time(),
                "consumed": False
            }
            new_proposals.append(prop)
    
    if not new_proposals:
        return
    
    # 去重：只添加不存在的
    exist_types = set(p.get("type","") for p in existing["proposals"] 
                       if not p.get("consumed", False))
    for p in new_proposals:
        if p["type"] not in exist_types:
            existing["proposals"].append(p)
            log(f"  提案: [{p['category']}] {p['type']} → 待修复")
    
    proposals_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2))

def heal_from_inspection(inspection_results):
    """自愈：根据自我检查结果尝试修复可自动修复的缺陷"""
    if not inspection_results:
        return {"healed": 0, "actions": ["无检查结果"]}
    
    actions = []
    
    # 遍历所有类别
    for cat, r in inspection_results.items():
        if not isinstance(r, dict):
            continue
        for check in r.get("checks", []):
            if check["status"] != "FAIL":
                continue
            name = check["name"]
            
            # 尝试修复已知缺陷模式
            if name == "hip_dimensions" and "非法维度" in check.get("detail",""):
                # 修复非法维度: 归一化海马体
                from .share import normalize_hip
                try:
                    normalize_hip()
                    actions.append(f"已归一化海马体维度: {check['detail'][:40]}")
                except Exception as e:
                    actions.append(f"归一化失败: {e}")
            
            elif name == "meta_loop" or name == "meta_stuck":
                # 元级卡死: 强制插入多维度链打破循环
                try:
                    import subprocess, sys
                    # 写入跨维链打破聚焦
                    from .share import write_chain as wc
                    for dim in ["触类旁通","超级直觉","思维并联","道","法","器","势"]:
                        wc({
                            "src": "自愈系统",
                            "rel": "打破循环",
                            "dst": dim,
                            "dimension": dim,
                            "content": f"自动注入·打破聚焦惯性→{dim}",
                            "tags": ["自愈", "破局", dim],
                            "strength": 0.4
                        })
                    actions.append(f"已注入跨维链打破{name}")
                except Exception as e:
                    actions.append(f"破局失败: {e}")
            
            elif name == "watchdog_cron" or "watchdog" in name:
                # 重建看门狗
                wd_script = CLUSTER / "brain_watchdog.sh"
                if wd_script.exists():
                    try:
                        r = subprocess.run(
                            ["crontab", "-l"], capture_output=True, text=True, timeout=5)
                        new_cron = (r.stdout or "") + \
                            f"\n* * * * * {CLUSTER}/brain_watchdog.sh >> {CLUSTER}/.brain_watchdog.log 2>&1\n"
                        with subprocess.Popen(["crontab"], stdin=subprocess.PIPE,
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as proc:
                            proc.communicate(input=new_cron.encode(), timeout=5)
                        actions.append("看门狗cron已重建")
                    except Exception as e:
                        actions.append(f"看门狗重建失败: {e}")
            
            elif name == "state_freshness":
                # 重建state文件
                try:
                    import time, json
                    (CLUSTER / ".brain_state.json").write_text(json.dumps(
                        {"cycle": 0, "timestamp": time.time(), "status": "recovered"}))
                    actions.append("state文件已重建")
                except Exception as e:
                    actions.append(f"state重建失败: {e}")
    
    healed = len(actions)
    if healed > 0:
        log(f"  ⚡ 自愈: {'; '.join(actions)}")
    else:
        log("  ⚡ 自愈: 无可自动修复项")
    
    return {"healed": healed, "actions": actions}


def inspect_and_report():
    """执行检查并报告（供brain/daemon.py调用）"""
    results = full_inspection()
    
    # 写入检查快照
    snapshot_path = CLUSTER / ".brain_inspection.json"
    snapshot_path.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    
    # 自修复：若发现缺陷则生成提案
    if results["summary"]["failed"] > 0:
        _generate_fix_proposals(results)
    
    return results  # 返回完整dict，供heal()使用


def auto_strengthen_检查(persist=3):
    """自愈: 维度检查连续weak≥3周期 → 自动强化"""
    from brain.share import write_chain as _wc, log as _log
    _log(f"反馈自愈[检查]: persist={persist}")
    _wc({
        "src": "反馈·自愈", "rel": "弱维触发",
        "dst": "检查", "dimension": "检查",
        "content": f"自动自愈函数: 连续weak≥{persist}周期触发",
        "strength": 0.65 + 0.05 * min(persist, 5)
    })
    return True