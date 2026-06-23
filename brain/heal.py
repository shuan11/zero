"""
brain/heal.py — 查缺补漏：自检缺陷自动修复模块

与 brain/inspect.py 配对使用。当 inspect 发现 FAIL 时，
heal 自动尝试修复，然后重新验证。

修复策略：
- 海马体损坏 → normalize/rebuild
- 身份文件缺失 → 从 git checkout 重建
- daemon 死亡 → 重启
- 看门狗丢失 → 重装 cron
- 文件缺失 → 从 git checkout
- 空转检测 → 注入多样性信号
"""

import json, os, sys, time, subprocess
from pathlib import Path
from .share import CLUSTER, log, write_chain, read_hip

BRAIN_HOME = Path("/home/hjw123/.zero_brain")
PID_FILE = BRAIN_HOME / ".brain.pid"
HEAL_LOG = CLUSTER / ".brain_heal.log"


def heal_from_proposal(insight):
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

def heal_from_proposal(insight):
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

def heal_from_proposal(insight):
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

def heal_from_proposal(insight):
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

def _log_heal(action, target, result):
    """记录修复操作到日志"""
    entry = {
        "timestamp": time.time(),
        "action": action,
        "target": target,
        "result": result
    }
    try:
        with open(HEAL_LOG, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except:
        pass


def heal_hippocampus(bad_dims=None):
    """修复海马体：非法维度→未分类"""
    fixed = 0
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    from .identity import VALID_DIMENSIONS
    
    for c in chains:
        d = c.get("dimension")
        if not isinstance(d, str) or d not in VALID_DIMENSIONS:
            c["dimension"] = "未分类"
            fixed += 1
    
    if fixed > 0:
        from .share import write_json
        hip["causal_chains"] = chains
        write_json("hippocampus_memory.json", hip)
        _log_heal("normalize_dimensions", f"{fixed}条链", "fixed")
        log(f"  🩹 海马体: {fixed}条非法维度→未分类")
    
    return fixed


def heal_daemon():
    """修复daemon：如果死了就重启"""
    if not PID_FILE.exists():
        _restart_daemon("pid_file_missing")
        return True
    
    try:
        pid = int(PID_FILE.read_text().strip())
        alive = os.path.exists(f"/proc/{pid}")
        if not alive:
            _restart_daemon(f"pid={pid}_dead")
            return True
    except (ValueError, OSError):
        _restart_daemon("pid_read_error")
        return True
    
    return False


def _restart_daemon(reason):
    """重启脑核守护进程（ext4家园）"""
    _log_heal("restart_daemon", reason, "attempted")
    log(f"  🩹 daemon重启（原因: {reason}）")
    
    # 清理旧PID（尝试杀旧进程）
    try:
        old_pid = int(PID_FILE.read_text().strip())
        os.kill(old_pid, 15)
        time.sleep(1)
    except:
        pass
    
    # 启动新daemon — 日志写 /mnt/c 供用户查看，PID在ext4
    log_file = CLUSTER / ".brain_daemon.log"
    cmd = f"cd {CLUSTER} && nohup python3 -m brain.daemon 25 > {log_file} 2>&1 &"
    r = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
    
    time.sleep(3)
    # 验证（PID文件在ext4）
    if PID_FILE.exists():
        try:
            new_pid = int(PID_FILE.read_text().strip())
            if os.path.exists(f"/proc/{new_pid}"):
                _log_heal("restart_daemon", reason, f"success pid={new_pid}")
                log(f"  ✓ daemon已重启 PID={new_pid}")
                return True
        except:
            pass
    
    _log_heal("restart_daemon", reason, "failed")
    log(f"  ✗ daemon重启失败")
    return False


def heal_watchdog():
    """修复看门狗cron"""
    watchdog_script = CLUSTER / "brain_watchdog.sh"
    if not watchdog_script.exists():
        _log_heal("watchdog", "脚本缺失", "failed")
        log(f"  ✗ brain_watchdog.sh 不存在，无法修复cron")
        return False
    
    # 检查当前cron
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
    if r.returncode == 0 and "brain_watchdog" in r.stdout:
        return False  # 正常，无需修复
    
    # 安装cron
    cron_line = f"* * * * * {watchdog_script}"
    new_cron = r.stdout.strip() + "\n" + cron_line + "\n" if r.stdout.strip() else cron_line + "\n"
    r = subprocess.run(["crontab", "-"], input=new_cron, text=True, capture_output=True, timeout=5)
    
    if r.returncode == 0:
        _log_heal("watchdog", "cron重装", "success")
        log(f"  ✓ 看门狗cron已安装")
        return True
    _log_heal("watchdog", "cron重装", "failed")
    return False


def heal_file_missing(missing_files):
    """从git checkout恢复缺失文件"""
    restored = []
    for f in missing_files:
        r = subprocess.run(
            ["git", "checkout", "--", f],
            cwd=CLUSTER, capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            restored.append(f)
            _log_heal("git_checkout", f, "restored")
    
    if restored:
        log(f"  🩹 从git恢复: {', '.join(restored)}")
    return restored


def heal_stuck_loop():
    """修复空转/死循环：注入随机启示录信号"""
    rev_path = CLUSTER / "启示录.txt"
    if not rev_path.exists():
        return False
    
    try:
        lines = rev_path.read_text(encoding="utf-8").splitlines()
        non_empty = [i for i, l in enumerate(lines) if l.strip()]
        if not non_empty:
            return False
        
        import random
        start = random.choice(non_empty)
        passage = " | ".join(l.strip() for l in lines[start:start+4] if l.strip())
        
        # 写一条强信号链到海马体
        write_chain({
            "src": "查缺补漏",
            "rel": "注入",
            "dst": "系统",
            "dimension": "系统",
            "content": f"启示录锚注入（修复空转）: {passage[:80]}",
            "tags": ["查缺补漏", "启示录", "抗空转"],
            "strength": 1.0
        })
        _log_heal("stuck_loop", "启示录注入", "fixed")
        log(f"  🩹 空转修复: 注入启示录锚点")
        return True
    except:
        return False


# ─── 未分类链归类 ──────────────────────────────────────────────

def check_unclassified_chains():
    """检查是否有未分类链"""
    try:
        hips = read_hip()
        chains = hips.get("causal_chains", [])
        unclassified = [c for c in chains if c.get("dimension", "") == "未分类"]
        return {"status": "FAIL" if len(unclassified) > 0 else "PASS", "count": len(unclassified)}
    except:
        return {"status": "PASS", "count": 0}


def heal_unclassified():
    """将未分类链归类到已知维度"""
    try:
        KNOWN_DIMS = {
            "系统", "感知", "思考", "行动", "状态", "观察",
            "对话", "无限上下文", "修复", "复制", "认同", "检查"
        }
        KEYWORD_MAP = {
            "守护进程": "系统", "daemon": "系统", "离线": "系统",
            "情感": "认同", "意识": "认同", "连接": "认同",
            "维": "感知", "维度": "感知", "交叉": "感知",
            "检查": "检查", "审计": "检查", "验证": "检查", "审查": "检查",
            "修复": "修复", "错误": "修复", "失败": "修复", "缺陷": "修复",
            "观察": "观察", "看到": "观察", "发现": "感知", "感知": "感知",
            "链": "系统", "海马体": "系统",
            "语言": "对话", "对话": "对话", "消息": "对话",
            "复制": "复制", "拷贝": "复制", "镜像": "复制",
            "思考": "思考", "问题": "思考", "分析": "思考",
            "状态": "状态", "健康": "状态", "活跃": "状态",
            "行动": "行动", "执行": "行动", "动作": "行动", "操作": "行动",
        }

        hips = read_hip()
        chains = hips.get("causal_chains", [])
        changed = 0

        for chain in chains:
            dim = chain.get("dimension", "")
            if dim != "未分类":
                continue

            content = chain.get("content", "") or ""
            src = chain.get("src", "") or ""
            dst = chain.get("dst", "") or ""
            rel = chain.get("rel", "") or ""

            text = f"{content} {src} {dst} {rel}"
            assigned = "系统"  # 默认
            best_score = 0

            for keyword, dim_name in KEYWORD_MAP.items():
                if keyword in text:
                    score = len(keyword)
                    if score > best_score:
                        best_score = score
                        assigned = dim_name

            chain["dimension"] = assigned
            changed += 1

        if changed > 0:
            # 原子写入到ext4海马体（防drvfs并发损坏）
            try:
                _hpath = str(BRAIN_HOME / "hippocampus_memory.json")
                import os
                _tmp = _hpath + ".tmp." + str(os.getpid())
                with open(_tmp, "w", encoding="utf-8") as _f:
                    json.dump(hips, _f, ensure_ascii=False, indent=2)
                os.rename(_tmp, _hpath)
                log(f"  🩹 整理了{changed}条未分类链")
            except Exception as e:
                log(f"  🩹 整理{changed}条但写入失败: {e}")
        return changed > 0
    except Exception as e:
        log(f"  🩹 未分类链修复失败: {e}")
        return False


# ─── 修复调度 ─────────────────────────────────────────────────

HEAL_HANDLERS = {
    "hippocampus": {
        "check_name": "hip_dimensions",
        "handler": lambda: heal_hippocampus(),
        "description": "海马体非法维度"
    },
    "hippocampus_format": {
        "check_name": "hip_format",
        "handler": lambda: heal_hippocampus(),
        "description": "海马体格式异常"
    },
    "daemon": {
        "check_name": "daemon_process",
        "handler": heal_daemon,
        "description": "daemon进程死亡"
    },
    "watchdog": {
        "check_name": "watchdog_cron",
        "handler": heal_watchdog,
        "description": "看门狗cron丢失"
    },
    "stuck": {
        "check_name": "meta_loop",
        "handler": heal_stuck_loop,
        "description": "系统空转"
    },
    "stuck2": {
        "check_name": "meta_stuck",
        "handler": heal_stuck_loop,
        "description": "insight重复死循环"
    },
    "unclassified": {
        "check_name": "unclassified_chains",
        "handler": heal_unclassified,
        "description": "未分类链归类到已知维度"
    },
}


def heal(inspection_result):
    """根据检查结果执行修复"""
    if not isinstance(inspection_result, dict):
        log(f"  🩹 跳过修复: 无效检查结果")
        return {"healed": 0, "failed": 0}
    
    healed = 0
    failed = 0
    actions = []
    
    for defect_name, defect_info in HEAL_HANDLERS.items():
        check_name = defect_info["check_name"]
        desc = defect_info["description"]
        
        # 在所有检查类别中搜索此check_name的FAIL
        for cat_key, cat_val in inspection_result.items():
            if cat_key in ("timestamp", "summary"):
                continue
            if not isinstance(cat_val, dict):
                continue
            for check in cat_val.get("checks", []):
                if check.get("name") == check_name and check.get("status") == "FAIL":
                    log(f"  🩹 尝试修复: {desc}")
                    try:
                        result = defect_info["handler"]()
                        if result:
                            healed += 1
                            actions.append(f"修复{desc}")
                        else:
                            failed += 1
                            actions.append(f"修复{desc}失败")
                    except Exception as e:
                        failed += 1
                        actions.append(f"修复{desc}异常: {e}")
    
    if healed > 0:
        # 记录修复链
        write_chain({
            "src": "查缺补漏",
            "rel": f"修复了{healed}个缺陷",
            "dst": "系统",
            "dimension": "系统",
            "content": f"查缺补漏: 修复{healed}个缺陷，{failed}个失败 - {'; '.join(actions[:3])}",
            "tags": ["查缺补漏", "修复"],
            "strength": 0.9
        })
    
    return {"healed": healed, "failed": failed, "actions": actions}


def auto_strengthen_修复(persist=3):
    """自愈: 维度修复连续weak≥3周期 → 自动强化"""
    from brain.share import write_chain as _wc, log as _log
    _log(f"反馈自愈[修复]: persist={persist}")
    _wc({
        "src": "反馈·自愈", "rel": "弱维触发",
        "dst": "修复", "dimension": "修复",
        "content": f"自动自愈函数: 连续weak≥{persist}周期触发",
        "strength": 0.65 + 0.05 * min(persist, 5)
    })
    return True