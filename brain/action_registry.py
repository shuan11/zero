"""
基因动作注册表 — Gene Action Registry
═════════════════════════════════════
让gen文件从"报告器"变成"执行器"的关键桥梁。

机制:
1. gen文件在engineer_*()中调用register_action()注册动作
2. daemon周期或loader在处理完全部gen文件后调用execute_actions()
3. 执行器按优先级处理动作队列

动作类型:
- update_genome: 修改基因组参数
- write_chain: 写入因果链(带质量保障)
- create_gen_file: 创建新的gen文件(基因表达)
- spawn_process: 创建后台进程
- signal_alert: 发出紧急信号
- inject_rule: 注入行为规则

架构: 全局动作队列(线程安全)，非阻塞执行，失败不中断。
"""
import time
import json
from pathlib import Path
from collections import defaultdict

# 全局动作队列
_action_queue = []
_queue_lock = False  # 简单的锁协议(因全单线程，无竞态)

# 动作类型白名单
VALID_ACTIONS = {
    "update_genome",     # 修改基因组
    "write_chain",       # 写入因果链
    "create_gen_file",   # 创建gen文件
    "signal_alert",      # 紧急信号
    "update_goal",       # 更新目标
}

def register_action(action_type, params=None, priority=5, source="unknown"):
    """注册一个动作到队列。
    
    Args:
        action_type: 动作类型 (来自VALID_ACTIONS)
        params: 动作参数字典
        priority: 优先级 1-10 (1=最高)
        source: 动作来源(如gen_感受)
    
    Returns:
        action_id: 动作ID(用于追踪)
    """
    global _action_queue, _queue_lock
    
    if action_type not in VALID_ACTIONS:
        return None
    
    action = {
        "id": f"act_{int(time.time()*1000)}_{len(_action_queue)}",
        "type": action_type,
        "params": params or {},
        "priority": priority,
        "source": source,
        "registered_at": time.time(),
        "executed": False,
        "result": None
    }
    
    _action_queue.append(action)
    # 按优先级排序
    _action_queue.sort(key=lambda a: a["priority"])
    
    return action["id"]


def execute_actions(max_actions=10):
    """执行队列中的动作。
    
    Args:
        max_actions: 单次最多执行的动作数
    
    Returns:
        results: [(action_id, success, result)]
    """
    global _action_queue
    
    results = []
    executed = 0
    
    for action in _action_queue[:]:
        if action["executed"] or action.get("_suppressed"):
            _action_queue.remove(action)
            continue
        
        if executed >= max_actions:
            break
        
        try:
            success, result = _execute_single_action(action)
            action["executed"] = True
            action["result"] = result
            results.append((action["id"], success, result))
            executed += 1
            # 记录执行历史(供验证器)
            _record_history(action)
        except Exception as e:
            action["executed"] = True
            action["result"] = str(e)
            results.append((action["id"], False, str(e)))
        
        # 从队列移除已执行的
        _action_queue.remove(action)
    
    return results


def _execute_single_action(action):
    """执行单个动作。"""
    atype = action["type"]
    params = action["params"]
    
    if atype == "update_genome":
        return _exec_update_genome(params)
    elif atype == "write_chain":
        return _exec_write_chain(params)
    elif atype == "create_gen_file":
        return _exec_create_gen_file(params)
    elif atype == "signal_alert":
        return _exec_signal_alert(params)
    elif atype == "update_goal":
        return _exec_update_goal(params)
    
    return False, f"未知动作类型: {atype}"


def _exec_update_genome(params):
    """修改基因组参数。"""
    from brain.genome import update_genome
    changes = params.get("changes", {})
    if not changes:
        return False, "无修改"
    update_genome(changes)
    return True, f"基因组已更新: {changes}"


def _exec_write_chain(params):
    """写入因果链。"""
    try:
        from brain.share import write_chain
        
        # params本身即为链数据（或包含chain键）
        chain_data = params.get("chain", params)
        if not chain_data.get("content"):
            return False, "因果链缺少content"
        
        write_chain(chain_data)
        return True, f"链已写入: {chain_data.get('src','?')}→{chain_data.get('dimension','?')}"
    except Exception as e:
        return False, f"写入失败: {e}"


def _exec_create_gen_file(params):
    """创建新的gen文件(基因表达)。"""
    try:
        from brain.gene_expression import create_gene_engine
        dim_name = params.get("dimension", "")
        dim_count = params.get("chain_count", 0)
        insight = params.get("insight", f"为{dim_name}维度自动创建gen文件")
        generation = params.get("generation", 0)
        
        success, result = create_gene_engine(dim_name, dim_count, insight, generation)
        return success, result
    except Exception as e:
        return False, f"创建失败: {e}"


def _exec_signal_alert(params):
    """发出紧急信号。"""
    level = params.get("level", "info")
    message = params.get("message", "")
    
    # 写入特殊维度链标记
    try:
        from brain.share import write_chain
        write_chain({
            "src": f"警报@{params.get('source','gen')}",
            "rel": f"信号:{level}",
            "dst": f"level_{level}",
            "dimension": "系统",
            "content": f"[{level.upper()}] {message}",
            "strength": 0.95
        })
        return True, f"警报已发送: {level}/{message[:50]}"
    except:
        return False, "警报发送失败"


def _exec_update_goal(params):
    """更新系统目标。"""
    try:
        new_goal = params.get("goal", "")
        priority = params.get("priority", 5)
        
        from brain.genome import update_genome
        update_genome({"system.goal": new_goal})
        
        from brain.share import write_chain
        write_chain({
            "src": "动作引擎",
            "rel": f"设置目标#{priority}",
            "dst": f"priority:{priority}",
            "dimension": "系统",
            "content": f"目标[{new_goal[:50]}] 优先级{priority}",
            "strength": 0.9
        })
        return True, f"目标已设置: {new_goal[:50]}"
    except Exception as e:
        return False, f"目标设置失败: {e}"


def get_queue_status():
    """获取动作队列状态。"""
    global _action_queue
    pending = [a for a in _action_queue if not a["executed"]]
    return {
        "total": len(_action_queue),
        "pending": len(pending),
        "by_type": dict(
            (t, len([a for a in pending if a["type"] == t]))
            for t in VALID_ACTIONS
        ),
        "oldest_pending": min(
            (a["registered_at"] for a in pending),
            default=0
        )
    }


def clear_queue():
    """清空动作队列。"""
    global _action_queue
    _action_queue.clear()


def _record_history(action):
    """记录动作执行历史(供验证器用)。"""
    try:
        from brain.action_verifier import _record_execution_history
        _record_execution_history(action)
    except:
        pass
