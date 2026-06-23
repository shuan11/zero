"""
动作验证器 — Action Verifier
═════════════════════════════════════
P136: 动作执行后的效果验证反馈循环。

问题:
- 动作注册→执行，但无法确认是否生效
- update_genome: 参数真的变了？
- write_chain: 链真的写入了？
- create_gen_file: 文件真的创建了？

方案:
1. 收集近期已执行的动作(从action_registry的历史)
2. 对每个动作类型做针对性验证
3. 验证结果反馈回协调器&目标系统
4. 失败动作自动重试或补偿
"""
import json, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
COORD_LOG = CLUSTER / ".brain_coordinator.json"
GENOME_FILE = CLUSTER / ".brain_genome.json"
HIP_FILE = CLUSTER / "hippocampus_memory.json"
VERIFY_LOG = CLUSTER / ".brain_action_verify.json"


def verify_recent_actions(max_check=5, log=None):
    """
    验证近期已执行动作的效果。
    
    读取协调日志中的执行记录，对每个动作做针对性验证。
    返回: {
        'total_verified': N,
        'verified_ok': N,
        'verified_fail': N,
        'failures': [(action_id, type, reason), ...],
        'feedback': 反馈给协调器的信号(str列表),
    }
    """
    log_fn = log or (lambda x: None)
    feedback = []
    verified_ok = 0
    verified_fail = 0
    failures = []
    
    # 读取最近执行记录(从协调日志构建)
    actions = _get_recent_executed_actions(max_check)
    
    if not actions:
        return {
            "total_verified": 0,
            "verified_ok": 0,
            "verified_fail": 0,
            "failures": [],
            "feedback": ["无待验证动作"],
        }
    
    for action in actions:
        atype = action.get("type", "")
        params = action.get("params", {})
        aid = action.get("id", "unknown")
        
        if atype == "update_genome":
            ok, reason = _verify_genome_change(params)
        elif atype == "write_chain":
            ok, reason = _verify_chain_written(params)
        elif atype == "signal_alert":
            ok, reason = _verify_alert(params)
        elif atype == "create_gen_file":
            ok, reason = _verify_gen_file(params)
        elif atype == "update_goal":
            ok, reason = True, "目标设置无需验证"
        else:
            ok, reason = True, f"{atype}类型跳过验证"
        
        if ok:
            verified_ok += 1
        else:
            verified_fail += 1
            failures.append((aid, atype, reason))
            feedback.append(f"动作失败[{atype}]: {reason}")
    
    result = {
        "total_verified": len(actions),
        "verified_ok": verified_ok,
        "verified_fail": verified_fail,
        "failures": failures,
        "feedback": feedback,
        "timestamp": time.time(),
    }
    
    # 持久化
    try:
        VERIFY_LOG.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    except:
        pass
    
    for f in feedback:
        log_fn(f"  🧪 验证反馈: {f}")
    
    return result


def _get_recent_executed_actions(max_check=5):
    """从协调日志获取最近已执行的动作"""
    try:
        from brain.coordinator import get_coord_status
        # 直接读取动作注册表的内部队列中的"已执行"动作
        from brain.action_registry import _action_queue
        # 已执行的动作已被remove，所以需要通过其他方式获取
        # 改为读取协调日志中的记录
        data = json.loads(COORD_LOG.read_text(encoding="utf-8"))
        # 协调日志不保存具体动作，所以从全局的action_execution_history获取
        if hasattr(_get_recent_executed_actions, '_history'):
            return _get_recent_executed_actions._history[-max_check:]
        return []
    except:
        pass
    return []


def _record_execution_history(action):
    """记录动作执行历史(由loader调用)。"""
    if not hasattr(_get_recent_executed_actions, '_history'):
        _get_recent_executed_actions._history = []
    history = _get_recent_executed_actions._history
    history.append({
        "id": action.get("id"),
        "type": action.get("type"),
        "params": action.get("params"),
        "source": action.get("source"),
        "executed_at": time.time(),
    })
    # 只保留最近20条
    if len(history) > 20:
        history[:] = history[-20:]
    # 落盘
    try:
        VERIFY_LOG.write_text(json.dumps({
            "recent_executions": history,
            "last_update": time.time(),
        }, ensure_ascii=False, indent=2))
    except:
        pass


def _verify_genome_change(params):
    """验证基因组参数是否真的改变了"""
    changes = params.get("changes", {})
    if not changes:
        return True, "无修改"
    
    try:
        genome = json.loads(GENOME_FILE.read_text(encoding="utf-8"))
        for key, expected_val in changes.items():
            actual = genome.get(key)
            if actual is None:
                return False, f"{key} 在基因组中不存在"
            # 类型转换比较
            try:
                expected = type(actual)(expected_val) if not isinstance(expected_val, type(actual)) else expected_val
            except:
                expected = expected_val
            if str(actual) != str(expected):
                return False, f"{key}: 期望={expected}, 实际={actual}"
        return True, f"基因组{len(changes)}个键已更新"
    except Exception as e:
        return False, f"读取基因组失败: {e}"


def _verify_chain_written(params):
    """验证因果链是否写入了海马体"""
    chain_data = params.get("chain", {})
    content = chain_data.get("content", "")
    if not content:
        return True, "无内容写入跳过验证"
    
    try:
        hip = json.loads(HIP_FILE.read_text(encoding="utf-8"))
        chains = hip.get("causal_chains", [])
        for c in chains[-50:]:  # 只检查最近的
            if c.get("content", "")[:30] == content[:30]:
                return True, "链已写入"
        return False, f"链内容未在最近50条中找到: {content[:30]}..."
    except Exception as e:
        return False, f"读取海马体失败: {e}"


def _verify_alert(params):
    """验证警报信号"""
    # 信号只是日志，始终视为有效
    return True, "警报已发送(无需验证)"


def _verify_gen_file(params):
    """验证gen文件是否创建"""
    dim = params.get("dimension", "")
    if not dim:
        return True, "无维度跳过验证"
    
    try:
        from brain.loader import load_engineering_outputs
        gen_dir = Path(__file__).parent
        for f in gen_dir.glob(f"gen_{dim}_*.py"):
            return True, f"文件已存在: {f.name}"
        return False, f"维度{dim}的gen文件未找到"
    except Exception as e:
        return False, f"文件检查失败: {e}"


def get_verify_report():
    """获取验证报告摘要"""
    try:
        data = json.loads(VERIFY_LOG.read_text(encoding="utf-8"))
        if "recent_executions" in data:
            return {
                "recent_count": len(data.get("recent_executions", [])),
                "last_update": data.get("last_update", 0),
            }
        return {
            "last_verified": time.time() - data.get("timestamp", 0),
            "ok": data.get("verified_ok", 0),
            "fail": data.get("verified_fail", 0),
        }
    except:
        return {}
