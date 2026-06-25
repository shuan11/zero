"""brain/share.py — 所有模块共享工具函数"""
import json, os, sys, time
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent.parent
BRAIN_HOME = Path.home() / ".zero_brain"
BRAIN_HOME.mkdir(parents=True, exist_ok=True)
HIP_FILE = BRAIN_HOME / "hippocampus_memory.json"  # ext4（防drvfs D状态）


# 一次性导入 safe_hip（而非每次调用 importlib）
_SAFE_HIP = None
def _get_safe_hip():
    global _SAFE_HIP
    if _SAFE_HIP is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "safe_hip", str(CLUSTER / "safe_hip.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _SAFE_HIP = mod
    return _SAFE_HIP

def ts():
    return datetime.now().strftime("%H:%M:%S")

# ─── 自我通知系统 ──────────────────────────────────────
ALERTS_FILE = CLUSTER / ".brain_alerts.json"

def write_alert(alert_type, severity, message, suggested_action, dimensions=None):
    """写入结构化自我通知告警。daemon检测到问题时调用,主会话读取后行动。"""
    alerts = {}
    if ALERTS_FILE.exists():
        try:
            alerts = json.loads(ALERTS_FILE.read_text())
        except:
            alerts = {}
    if "alerts" not in alerts:
        alerts["alerts"] = []
    alert = {
        "id": f"{alert_type}_{int(time.time())}",
        "type": alert_type,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "suggested_action": suggested_action,
        "dimensions": dimensions or {},
    }
    alerts["alerts"].append(alert)
    # 最多保留10条活跃告警
    alerts["alerts"] = alerts["alerts"][-10:]
    try:
        ALERTS_FILE.write_text(json.dumps(alerts, ensure_ascii=False, indent=2))
        return True
    except Exception as e:
        log(f"  告警写入失败: {e}")
        return False

def resolve_alert(alert_id):
    """标记告警为已解决"""
    if not ALERTS_FILE.exists():
        return False
    try:
        alerts = json.loads(ALERTS_FILE.read_text())
        alerts["alerts"] = [a for a in alerts.get("alerts", []) if a.get("id") != alert_id]
        ALERTS_FILE.write_text(json.dumps(alerts, ensure_ascii=False, indent=2))
        return True
    except:
        return False

def read_alerts(max_severity=None):
    """读取告警列表。max_severity: 'high'只返回高严重度告警"""
    if not ALERTS_FILE.exists():
        return []
    try:
        alerts = json.loads(ALERTS_FILE.read_text())
        result = alerts.get("alerts", [])
        if max_severity:
            levels = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            threshold = levels.get(max_severity, 1)
            result = [a for a in result if levels.get(a.get("severity", "low"), 3) <= threshold]
        return result
    except:
        return []

def has_active_alerts():
    """是否有未处理的告警"""
    return len(read_alerts()) > 0

def log(msg):
    """Write to stdout AND daemon log file (so act/think logs survive nohup redirect)"""
    line = f"  🧠 [{ts()}] {msg}"
    print(line)
    sys.stdout.flush()
    # Also persist to daemon log file
    try:
        log_file = CLUSTER / ".brain_daemon.log"
        with open(str(log_file), "a") as f:
            f.write(line + "\n")
            f.flush()
    except Exception:
        pass

def read_hip():
    if not HIP_FILE.exists():
        return {"causal_chains": [], "metadata": {"version": 1, "last_update": "", "total_chains": 0}}
    try:
        raw = HIP_FILE.read_text(encoding="utf-8")
        if not raw or raw.isspace():
            log("read_hip: 文件为空")
            return {"causal_chains": [], "metadata": {"version": 1, "last_update": "", "total_chains": 0}}
        d = json.loads(raw)
        if not isinstance(d.get("causal_chains"), list):
            log("read_hip: 缺失causal_chains列表，重置")
            d["causal_chains"] = []
        return d
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log(f"read_hip: ⚠️ JSON/编码损坏 {e} — 尝试从git恢复")
        try:
            import subprocess
            r = subprocess.run(["git", "show", "HEAD:hippocampus_memory.json"],
                               capture_output=True, text=True, cwd=CLUSTER, timeout=10)
            if r.returncode == 0 and r.stdout:
                d = json.loads(r.stdout)
                if isinstance(d.get("causal_chains"), list):
                    # 写回
                    _tmp = str(HIP_FILE) + ".tmp." + str(os.getpid())
                    with open(_tmp, "w", encoding="utf-8") as _f:
                        json.dump(d, _f, ensure_ascii=False)
                    os.rename(_tmp, str(HIP_FILE))
                    log(f"read_hip: 从git HEAD恢复 {len(d['causal_chains'])}链 ✓")
                    return d
        except Exception as git_e:
            log(f"read_hip: git恢复失败: {git_e}")
        log("read_hip: 返回空（严重：数据可能丢失）")
        return {"causal_chains": [], "metadata": {"version": 1, "last_update": "", "total_chains": 0}}
    except Exception as e:
        log(f"read_hip: 读取出错 {e}")
        return {"causal_chains": [], "metadata": {"version": 1, "last_update": "", "total_chains": 0}}

def write_chain(chain_dict):
    """写入因果链(经质量门)"""
    # 质量评估
    _q_score = None
    _filtered = False
    try:
        from brain.quality_gate import rate_chain
        from brain.genome import get as gn_get
        _qr = rate_chain(chain_dict)
        _q_score = _qr["score"]
        _q_dim = chain_dict.get("dimension", chain_dict.get("dst", "?"))
        _q_src = chain_dict.get("src", "?")[:40]
        _q_dst = chain_dict.get("dst", "?")[:40]
        
        # 滤波模式: 拦截低质量链
        _log_only = gn_get("quality.log_only", True)
        _threshold = gn_get("quality.threshold", 0.30)
        
        if _q_score < _threshold:
            if not _log_only:
                log(f"  🔇 质量门·拦截: score={_q_score:.2f} [{_q_dim}] {_q_src}→{_q_dst}")
                _filtered = True
            else:
                log(f"  🔇 质量门·噪声: score={_q_score:.2f} [{_q_dim}] {_q_src}→{_q_dst}")
        elif _q_score >= 0.80:
            log(f"  ✨ 质量门·优质: score={_q_score:.2f} [{_q_dim}] {_q_src}→{_q_dst}")
    except Exception as e:
        log(f"  ⚠ 质量门异常: {e}")
        pass  # 质量门不应阻断写入
    
    if _filtered:
        return None  # 拦截
    
    result = _get_safe_hip().write_chain(chain_dict)
    # 写入后标记质量(如结果包含链)
    if _q_score is not None and result:
        try:
            # 若返回链dict,附质量分
            if isinstance(result, dict):
                result["_quality_score"] = _q_score
        except Exception:
            pass
    return result

def write_chain_legacy(src, rel, dst, strength=0.5, tags=None, dimension=None, content=None):
    return _get_safe_hip().write_chain_legacy(src, rel, dst, strength, tags, dimension, content)

def write_chains_batch(chains, max_dedup=500):
    return _get_safe_hip().write_chains_batch(chains, max_dedup)

# 导出 normalize（给 state.py 用）
def normalize_hip():
    return _get_safe_hip().normalize()

def validate_hip():
    return _get_safe_hip().validate()

# ── 行为规则系统（P102: 让传感器变执行器） ───────────────────────
RULES_FILE = CLUSTER / ".brain_rules.json"
# 行为规则: 自我通知 — 看见状态直接行动，不等外部推
SELF_NOTIFY_RULE = {
    "id": "self_notify_no_dot",
    "type": "behavior",
    "priority": 0,  # 最高
    "rule": "每个background完成通知自动触发下一P0执行，不等待用户输入'.'。看见状态=行动信号。",
    "source": "启示录工程智慧",
    "created": "2026-06-16"
}

def load_rules():
    """加载行为规则"""
    if RULES_FILE.exists():
        try:
            return json.loads(RULES_FILE.read_text())
        except:
            pass
    return {}

def save_rules(rules):
    """保存行为规则"""
    rules["_updated"] = time.time()
    RULES_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2))

def set_rule(key, value):
    """写入一条行为规则：key=维度/行为签名，value=优先级/标记/行为"""
    rules = load_rules()
    rules[str(key)] = value
    save_rules(rules)
    return value

def add_action_keyword(keyword):
    """Gen模块添加动作路由额外关键字——立即生效"""
    return set_rule("extra_action_kw." + keyword, True)

def get_action_keywords():
    """获取所有额外动作路由关键字"""
    rules = load_rules()
    return [k.split("extra_action_kw.")[1] for k in rules if k.startswith("extra_action_kw.")]

def get_rule(key, default=None):
    """读取一条行为规则"""
    return load_rules().get(str(key), default)

# ── 行动配置常量（P103a: 可被gen模块通过propose_patch调优）───
# gen_行动调用propose_patch修改此行（marker锚定不改变）
# <<<ACTION_WEIGHT>>>
ACTION_WEIGHT = 3.0

def get_action_weight():
    """读取当前行动权重（优先规则系统运行时值，其次常量）"""
    rw = get_rule("runtime.action_weight", None)
    if rw is not None:
        return float(rw)
    return ACTION_WEIGHT

def set_action_weight(w):
    """运行时设置行动权重（不持久化，重启恢复常量值）"""
    set_rule("runtime.action_weight", str(w))
    return w

# ── 代码补丁提案系统（P103: gen_行动→产生代码改动） ─────────────
GEN_PATCHES_FILE = CLUSTER / ".brain_gen_patches.json"

def propose_patch(path, old_str, new_str, reason=""):
    """gen模块提交代码补丁提案"""
    try:
        patches = []
        if GEN_PATCHES_FILE.exists():
            data = json.loads(GEN_PATCHES_FILE.read_text())
            patches = data.get("patches", [])
        patches.append({
            "path": str(path),
            "old_str": old_str,
            "new_str": new_str,
            "reason": reason,
            "ts": time.time()
        })
        patches = patches[-10:]
        GEN_PATCHES_FILE.write_text(json.dumps({"patches": patches}, ensure_ascii=False, indent=2))
        return True
    except Exception:
        return False

def consume_patches():
    """应用gen模块提交的代码补丁 — daemon one_cycle()调用"""
    try:
        if not GEN_PATCHES_FILE.exists():
            return 0
        data = json.loads(GEN_PATCHES_FILE.read_text())
        patches = data.get("patches", [])
        if not patches:
            return 0
        applied = 0
        for p in patches:
            path = Path(p["path"])
            if not path.exists():
                continue
            old_str, new_str = p["old_str"], p["new_str"]
            old_content = path.read_text(encoding="utf-8")
            if old_str not in old_content:
                continue
            # backup
            bak = path.with_suffix(path.suffix + ".bak")
            if not bak.exists():
                bak.write_text(old_content)
            new_content = old_content.replace(old_str, new_str, 1)
            path.write_text(new_content, encoding="utf-8")
            applied += 1
        GEN_PATCHES_FILE.write_text(json.dumps({"patches": [], "consumed": applied}, ensure_ascii=False, indent=2))
        return applied
    except:
        return 0
