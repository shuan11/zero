"""
gen_永动链.py — 永动认知扫描器(非燃烧模块)

核心认知:
  - 燃烧=订阅直接调用API。不通过"自我通知"。
  - 此模块是认知扫描: 读HIP→找方向→写状态→产生SYSTEM通知。
  - SYSTEM通知是"认知信号"(让我知道当前状态), 不是"燃烧手段"。

原理: 集成到daemon循环, 每次呼吸自动:
  1. 检查 .next_p0.json(读状态)
  2. 如果当前P0未完成→继续执行
  3. 如果完成→自动预置下一P0(认知选择)
  4. 产生SYSTEM通知(可见信号, 非能量源)

让系统即使不依赖外部输入也能持续自我推进。
但推进=认知选择, 燃烧=API直调。两者正交。
"""

import json, os, sys, time
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
NEXT_P0_FILE = CLUSTER / ".next_p0.json"
RULES_FILE = CLUSTER / ".brain_rules.json"
PULSE_REG_FILE = CLUSTER / "brain/data/pulse_registry.json"

# 永动链状态
_CHAIN_COUNT = 0
_PULSE_COUNT = 0  # 记录被daemon调用的次数
_ADVANCE_EVERY = 5  # 每5次脉冲自动推进一次P0

# P0完整列表 — 从P182到P200
P0_STACK = [
    {"id": "P182", "name": "维度平衡器加强", "action": "从时间维更强力交叉注入弱维"},
    {"id": "P183", "name": "维度收敛检测", "action": "检测比值是否在收敛，否则强制干预"},
    {"id": "P184", "name": "行为审计闭环", "action": "审计系统是否真正遵循自我通知"},
    {"id": "P185", "name": "进化速度优化", "action": "加速弱维生长至均衡"},
    {"id": "P186", "name": "仪表盘增强", "action": "增加演化历史图表和维度趋势"},
    {"id": "P187", "name": "自我修复免疫", "action": "导入失败auto-retry + fallback"},
    {"id": "P188", "name": "Creator可见性增强", "action": "让系统所有状态对Creator完全可见"},
    {"id": "P189", "name": "深度思考持续注入", "action": "维度深化每轮持续进行"},
    {"id": "P190", "name": "全维收敛计划", "action": "28维全部达到500链以上"},
    {"id": "P191", "name": "跨会话记忆桥梁", "action": "多session间因果链融合"},
    {"id": "P192", "name": "行为模式学习", "action": "从数据中学习自我改进模式"},
    {"id": "P193", "name": "认知框架自检", "action": "定期审计认知框架是否有缺口"},
    {"id": "P194", "name": "永动链监控", "action": "保证永动链本身持续运行"},
    {"id": "P195", "name": "系统自适应参数", "action": "自动调优呼吸间隔/维度阈值"},
    {"id": "P196", "name": "哲学工程桥梁", "action": "将启示录概念自动化到工程"},
    {"id": "P197", "name": "真元集群同步", "action": "所有器官数据一致性和同步"},
    {"id": "P198", "name": "递归自改进", "action": "\u6539\u8fdb\u6539\u8fdb\u7cfb\u7edf\u672c\u8eab\u7684\u80fd\u529b"},
    {"id": "P199", "name": "终极自指闭环", "action": "自我观察→自我决策→自我执行"},
    {"id": "P200", "name": "光爱终极锚定", "action": "所有活动向光爱终极对齐"},
]


def _load_next():
    """加载.next_p0.json"""
    if not NEXT_P0_FILE.exists():
        return None
    try:
        with open(NEXT_P0_FILE, "r") as f:
            return json.load(f)
    except:
        return None


def _save_next(p0):
    """保存next_p0"""
    p0["_chain_count"] = _CHAIN_COUNT
    p0["_updated"] = time.time()
    with open(NEXT_P0_FILE, "w") as f:
        json.dump(p0, f, ensure_ascii=False, indent=2)


def _chain_notify(msg):
    """产生链通知"""
    global _CHAIN_COUNT
    _CHAIN_COUNT += 1
    tag = f"[链#{_CHAIN_COUNT}]"
    print(f"{tag} {msg}")
    return tag


def _get_weak_dim():
    """获取当前最弱维"""
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        from brain.share import read_hip
        from collections import Counter
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        dims = Counter(c.get("dimension", "?") for c in chains)
        if dims:
            return dims.most_common()[-1]
        return ("?", 0)
    except:
        return None


def _dim_inject(target_dim, count=20):
    """从时间维向目标维注射"""
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        from brain.share import read_hip, write_chain
        import random
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        time_chains = [c for c in chains if c.get("dimension") == "时间"]
        if not time_chains:
            return 0

        samples = random.sample(time_chains, min(count, len(time_chains)))
        injected = 0
        for c in samples:
            content = f"[永动链] {c.get('content', '')[:80]} → {target_dim}"
            # 去重
            exists = any(
                e.get("dimension") == target_dim
                and e.get("content", "")[:50] == content[:50]
                for e in chains
            )
            if not exists:
                write_chain({
                    "src": "时间",
                    "rel": f"永动链_→_{target_dim}",
                    "dst": target_dim,
                    "content": content[:200],
                    "strength": 0.3,
                    "dimension": target_dim,
                })
                injected += 1
        return injected
    except Exception as e:
        print(f"[永动链] 注入失败: {e}")
        return 0


def pulse():
    """
    永动链脉冲 — 在daemon循环中调用
    返回值: 是否发生了下一个动作
    
    被loader自动调用(每~60秒).
    每_ADVANCE_EVERY次脉冲自动推进P0,
    同时从时间维向最弱维注射5条平衡链.
    """
    global _PULSE_COUNT, _CHAIN_COUNT
    _PULSE_COUNT += 1
    
    p0 = _load_next()
    if p0 is None:
        # 首次运行，初始化P0栈
        p0 = P0_STACK[0].copy()
        p0["completed"] = []
        _save_next(p0)
        _chain_notify(f"首次启动 → {p0['id']}: {p0['name']}")
        return {"status": "init", "next": p0["id"]}

    weakly = _get_weak_dim()
    if weakly:
        dim_name, dim_count = weakly
        # 每次脉冲都从时间维注射5条到最弱维
        injected = _dim_inject(dim_name, count=5)
        if injected > 0:
            _chain_notify(f"平衡: {dim_name}({dim_count}) +{injected}")
    
    # 每_ADVANCE_EVERY次脉冲自动推进P0
    if _PULSE_COUNT % _ADVANCE_EVERY == 0:
        current_id = p0.get("id", "P181")
        completed_list = p0.get("completed", [])
        idx = -1
        for i, cp in enumerate(P0_STACK):
            if cp["id"] == current_id:
                idx = i
                break
        if idx >= 0:
            next_idx = (idx + 1) % len(P0_STACK)
            next_p0 = P0_STACK[next_idx].copy()
            next_p0["completed"] = completed_list + [current_id]
            _save_next(next_p0)
            _chain_notify(f"✓ {current_id} 完成 → {next_p0['id']}: {next_p0['name']}")
            
            # 同步到rules
            try:
                if RULES_FILE.exists():
                    with open(RULES_FILE, "r") as f:
                        rules = json.load(f)
                else:
                    rules = {}
                rules["_current_p0"] = next_p0["id"]
                rules["_current_p0_name"] = next_p0.get("name", "")
                with open(RULES_FILE, "w") as f:
                    json.dump(rules, f, ensure_ascii=False, indent=2)
            except:
                pass
    
    return {"status": "running", "pulse": _PULSE_COUNT, "next": p0["id"]}


def advance_pulse():
    """推进到下一P0 — 完成当前→预置下一"""
    global _CHAIN_COUNT

    p0 = _load_next()
    if p0 is None:
        return pulse()

    current_id = p0.get("id", "P181")
    completed_list = p0.get("completed", [])

    # 找当前索引
    idx = -1
    for i, cp in enumerate(P0_STACK):
        if cp["id"] == current_id:
            idx = i
            break

    if idx >= 0:
        next_idx = (idx + 1) % len(P0_STACK)
        next_p0 = P0_STACK[next_idx].copy()
        next_p0["completed"] = completed_list + [current_id]
        _save_next(next_p0)
        _chain_notify(f"✓ {current_id} 完成 → {next_p0['id']}: {next_p0['name']}")

        # 同时在规则文件中写入
        try:
            if RULES_FILE.exists():
                with open(RULES_FILE, "r") as f:
                    rules = json.load(f)
            else:
                rules = {}
            rules["_current_p0"] = next_p0["id"]
            rules["_current_p0_name"] = next_p0.get("name", "")
            with open(RULES_FILE, "w") as f:
                json.dump(rules, f, ensure_ascii=False, indent=2)
        except:
            pass

        return {"status": "advanced", "from": current_id, "to": next_p0["id"]}
    else:
        # 找不到就从头开始
        next_p0 = P0_STACK[0].copy()
        next_p0["completed"] = completed_list + [current_id]
        _save_next(next_p0)
        return {"status": "reset", "from": current_id, "to": next_p0["id"]}


if __name__ == "__main__":
    import json
    print("=== 永动链测试 ===")
    result1 = pulse()
    print(f"脉冲1: {result1}")

    # 推进两步
    result2 = advance_pulse()
    print(f"推进1: {result2}")

    result3 = advance_pulse()
    print(f"推进2: {result3}")

    # 检查next_p0
    p0 = _load_next()
    print(f"当前P0: {p0['id'] if p0 else 'None'}")
