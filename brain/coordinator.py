"""
动作协调器 — Action Coordinator
═════════════════════════════════════
P135: 让gen文件从"各自为战"变成"目标对齐"的关键桥梁。

问题:
- 78个gen文件各自独立注册动作，可能冲突
- 系统目标(brain_goal.json)不指导动作执行
- 重复动作堆积队列

方案:
1. 收集所有已注册动作
2. 读取系统目标(目标类型/聚焦维度/描述)
3. 计算每个动作的目标对齐度得分
4. 检测冲突(相同genome键不同值)
5. 抑制低优先级冲突动作
6. 反馈→目标系统知道正在执行什么

集成点:
- 在loader.py中: gen文件全部运行后→coordinate()→再执行
- 在daemon.py中: 周期报告协调状态
"""
import json, time, re
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
GOAL_FILE = CLUSTER / ".brain_goal.json"
COORD_LOG = CLUSTER / ".brain_coordinator.json"


def _load_goal():
    """读取当前系统目标"""
    try:
        return json.loads(GOAL_FILE.read_text(encoding="utf-8"))
    except:
        return {}


def _score_goal_alignment(action, goal):
    """
    计算动作的目标对齐度。
    返回: -1~+1 的分数
      +1.0 = 完全对齐
       0.0 = 中性
      -1.0 = 完全冲突
    """
    if not goal:
        return 0.0  # 无目标→中性
    
    gtype = goal.get("goal_type", "")
    focus = goal.get("focus_dim", "")
    description = goal.get("description", "").lower()
    
    atype = action["type"]
    params = action.get("params", {})
    source = action.get("source", "")
    
    score = 0.0
    
    # ─── 目标类型感知 ───
    if gtype == "explore":
        # 探索目标：聚焦弱维
        if focus and focus in source:
            score += 0.5  # 动作来源匹配聚焦维
        # write_chain 写入弱维也加分
        if atype == "write_chain":
            chain_dim = params.get("chain", {}).get("dimension", "")
            if focus and chain_dim == focus:
                score += 0.4
        # create_gen_file 创建弱维文件
        if atype == "create_gen_file":
            if focus and params.get("dimension") == focus:
                score += 0.6
                
    elif gtype == "deepen":
        # 深化目标：聚焦强维
        if focus and focus in source:
            score += 0.3
        # update_genome 修改参数更相关
        if atype == "update_genome":
            score += 0.2
            
    elif gtype == "synthesize":
        # 合成目标：关注交叉
        if atype == "write_chain":
            content = params.get("chain", {}).get("content", "")
            if "×" in content:
                score += 0.5
        if atype == "update_genome":
            score += 0.1  # 参数调整也对合成有帮助
    
    # ─── 通用加分 ───
    # signal_alert 在探索目标下更有价值
    if atype == "signal_alert":
        if gtype in ("explore", "consolidate"):
            score += 0.3
    
    return max(-1.0, min(1.0, score))


def _detect_conflicts(actions):
    """
    检测动作间的冲突。
    冲突定义: 两个动作都修改同一genome键但目标值不同。
    
    返回: [(action_a_id, action_b_id, conflict_key, value_a, value_b)]
    """
    conflicts = []
    # 只检查 update_genome 类型的冲突
    genome_changes = {}  # key -> [(action_id, value, priority)]
    
    for a in actions:
        if a["type"] != "update_genome":
            continue
        changes = a.get("params", {}).get("changes", {})
        for key, val in changes.items():
            if key not in genome_changes:
                genome_changes[key] = []
            genome_changes[key].append((a["id"], val, a["priority"], a["source"]))
    
    for key, entries in genome_changes.items():
        if len(entries) < 2:
            continue
        # 检查是否有不同的值
        values = set(str(v) for _, v, _, _ in entries)
        if len(values) > 1:
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    if str(entries[i][1]) != str(entries[j][1]):
                        conflicts.append((
                            entries[i][0], entries[j][0],
                            key, entries[i][1], entries[j][1],
                            entries[i][2], entries[j][2],  # priorities
                            entries[i][3], entries[j][3],  # sources
                        ))
    
    return conflicts


def coordinate(log=None):
    """
    执行动作协调。
    
    流程:
    1. 读取当前目标
    2. 检查动作队列
    3. 计算每个动作的协调得分
    4. 检测冲突
    5. 抑制低优先冲突动作(标记但不删除)
    6. 记录协调日志
    
    返回: {
        'goal': 当前目标,
        'scores': {action_id: 目标对齐度},
        'conflicts': 冲突列表,
        'suppressed': 被抑制的动作数,
    }
    """
    from brain.action_registry import _action_queue, register_action
    
    log_fn = log or (lambda x: None)
    goal = _load_goal()
    
    if not _action_queue:
        return {
            "goal": goal,
            "scores": {},
            "conflicts": [],
            "suppressed": 0,
            "actions_total": 0,
        }
    
    # 1. 给每个未执行的动作用目标对齐度打分
    scores = {}
    pending = [a for a in _action_queue if not a["executed"]]
    
    for a in pending:
        scores[a["id"]] = _score_goal_alignment(a, goal)
    
    # 2. 检测冲突
    conflicts = _detect_conflicts(pending)
    
    # 3. 抑制冲突动作
    suppressed_ids = set()
    for (aid, bid, key, va, vb, pa, pb, sa, sb) in conflicts:
        score_a = scores.get(aid, 0.0)
        score_b = scores.get(bid, 0.0)
        
        # 计算对齐度差异(若一方显著更对齐则优先保留)
        align_diff = abs(score_a - score_b)
        align_winner = None
        if align_diff > 0.3:  # 显著差异
            align_winner = aid if score_a > score_b else bid
        
        if align_winner:
            # 目标对齐度显著主导→抑制低对齐的
            if align_winner == aid:
                suppressed_ids.add(bid)
                log_fn(f"  协调器: 抑制 {sb} 中 key={key}={vb} "
                       f"(目标对齐度 {score_b:.2f} < {score_a:.2f}，优先保留{sa})")
            else:
                suppressed_ids.add(aid)
                log_fn(f"  协调器: 抑制 {sa} 中 key={key}={va} "
                       f"(目标对齐度 {score_a:.2f} < {score_b:.2f}，优先保留{sb})")
        elif pa == pb:
            # 同优先级→目标对齐度低的被抑制
            if score_a < score_b:
                suppressed_ids.add(aid)
            elif score_b < score_a:
                suppressed_ids.add(bid)
            else:
                log_fn(f"  协调器: 冲突无法协调 key={key}: {sa}={va} vs {sb}={vb} — 两者都执行")
        else:
            # 优先级高的保留(数值越小优先级越高)
            if pa > pb:
                suppressed_ids.add(aid)
                log_fn(f"  协调器: 抑制 {sa}[pri={pa}] 中 key={key}={va} (与{sb}冲突,{sb}优先级更高)")
            elif pb > pa:
                suppressed_ids.add(bid)
                log_fn(f"  协调器: 抑制 {sb}[pri={pb}] 中 key={key}={vb} (与{sa}冲突,{sa}优先级更高)")
    
    # 4. 标记被抑制的动作(标记高优先级使其跳过后执行时不处理)
    for a in _action_queue:
        if a["id"] in suppressed_ids:
            a["priority"] = 99  # 最低优先级，确保不被执行
            a["_suppressed"] = True
    
    # 5. 记录日志
    result = {
        "goal": goal,
        "scores": scores,
        "conflicts": conflicts,
        "suppressed": len(suppressed_ids),
        "actions_total": len(pending),
        "goal_type": goal.get("goal_type", "none"),
        "focus_dim": goal.get("focus_dim", "none"),
        "timestamp": time.time(),
    }
    
    # 6. 持久化
    try:
        COORD_LOG.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    except:
        pass
    
    # 7. 反馈: 如果多个动作被抑制，注册一个反馈动作
    if len(suppressed_ids) >= 2:
        register_action("signal_alert", {
            "level": "info",
            "message": f"协调器: 抑制{len(suppressed_ids)}个冲突动作",
            "source": "coordinator"
        }, priority=3)
    
    return result


def get_coord_status():
    """获取协调状态摘要"""
    try:
        data = json.loads(COORD_LOG.read_text(encoding="utf-8"))
        return {
            "recent_coordination": True,
            "suppressed_total": data.get("suppressed", 0),
            "actions_total": data.get("actions_total", 0),
            "goal_type": data.get("goal_type", "none"),
            "focus": data.get("focus_dim", "none"),
            "conflicts": len(data.get("conflicts", [])),
        }
    except:
        return {}
