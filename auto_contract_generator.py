#!/usr/bin/env python3
"""
自动生成契约引擎 — 元递归的元递归
====================================
集群能自动生成新契约，填补治理缺口。
这是契约V的实现：本契约自身也受管理→本契约能生成新契约。

逻辑:
  1. 扫描集群全部维度(神经元/总线/记忆/进化/外部)
  2. 检查哪些维度没有被现有契约覆盖
  3. 用API推理生成新契约填补缺口
  4. 新契约自动注册到dynamic_contracts_state.json

用法:
  python3 auto_contract_generator.py           # 一次生成检察
  python3 auto_contract_generator.py --daemon   # 持续检察(每30分钟)
"""
import json, os, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
from api_config import API_KEY, API_BASE, MODEL
from api_strategy import api_call as _strategy_api, parallel_call, batch_call

CONTRACT_FILE = CLUSTER / "dynamic_contracts_state.json"
GENERATED_FILE = CLUSTER / "generated_contracts.json"

# ── 集群维度定义 ──────────────────────────────────────────

DIMENSIONS = {
    "neurons": {"desc": "神经元生命周期管理", "covered_by": [1]},
    "channels": {"desc": "频分通信通道", "covered_by": [1]},
    "learning": {"desc": "学习速率与策略优化", "covered_by": [2]},
    "adaptation": {"desc": "环境自适应能力", "covered_by": [2]},
    "consistency": {"desc": "跨组件一致性", "covered_by": [3]},
    "repair": {"desc": "故障自修复", "covered_by": [3]},
    "recursion": {"desc": "递归深度保护", "covered_by": [4]},
    "meta_governance": {"desc": "元治理(治理的治理)", "covered_by": [5]},
    "memory": {"desc": "记忆质量与巩固", "covered_by": []},
    "external_knowledge": {"desc": "外部知识获取与消化", "covered_by": []},
    "weight_adaptation": {"desc": "神经元权重自适应", "covered_by": []},
    "task_routing": {"desc": "任务智能路由", "covered_by": []},
    "error_recovery": {"desc": "错误恢复与韧性", "covered_by": []},
    "performance": {"desc": "性能监控与优化", "covered_by": []},
    "security": {"desc": "安全边界与防注入", "covered_by": []},
    "evolution_direction": {"desc": "进化方向引导", "covered_by": []},
}

def api_call(prompt, max_tokens=500):
    """调用API（已迁移到api_strategy统一调用）"""
    result = _strategy_api(prompt, max_tokens=max_tokens)
    if result["success"]:
        return result["content"] or ""
    return ""

def find_gaps():
    """找出未被契约覆盖的维度"""
    try:
        state = json.loads(CONTRACT_FILE.read_text())
        active_ids = set(int(k) for k in state.get("contracts", {}).keys())
    except Exception:
        active_ids = {1,2,3,4,5}

    gaps = []
    for dim, info in DIMENSIONS.items():
        covered = set(info.get("covered_by", []))
        if not covered.intersection(active_ids):
            gaps.append({"dimension": dim, "desc": info["desc"]})
    return gaps

def generate_contract(gap):
    """用API为缺口生成新契约"""
    prompt = f"""你是真元集群的契约生成器。
为以下治理缺口生成一条新契约:

缺口维度: {gap['dimension']}
缺口描述: {gap['desc']}

要求:
1. 契约名称(4字以内)
2. 契约描述(一句话)
3. 可配置参数(1-3个key-value)
4. 收敛条件(什么时候这条契约被认为"满足")

输出JSON:
{{"name":"...","desc":"...","params":{{"key":"default_value"}},"convergence":"..."}}
只输出JSON。"""

    result = api_call(prompt, max_tokens=300)
    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except Exception:
        pass
    return None

def register_contract(contract, gap):
    """注册新契约到系统"""
    try:
        state = json.loads(CONTRACT_FILE.read_text())
    except Exception:
        state = {"contracts": {}, "history": []}

    # 找到下一个可用ID
    existing_ids = [int(k) for k in state.get("contracts", {}).keys()]
    new_id = max(existing_ids) + 1 if existing_ids else 6

    # 注册
    state["contracts"][str(new_id)] = {
        "name": contract.get("name", f"auto_{new_id}"),
        "desc": contract.get("desc", gap["desc"]),
        "param": contract.get("params", {}),
        "auto_generated": True,
        "generated_from": gap["dimension"],
        "generated_at": datetime.now().isoformat(),
        "convergence": contract.get("convergence", ""),
    }

    state["history"].append({
        "time": datetime.now().isoformat(),
        "contract": new_id,
        "change": f"自动生成: {contract.get('name','?')} (填补{gap['dimension']}缺口)",
    })

    CONTRACT_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

    # 记录到生成日志
    try:
        log = json.loads(GENERATED_FILE.read_text()) if GENERATED_FILE.exists() else []
    except Exception:
        log = []
    log.append({
        "id": new_id,
        "name": contract.get("name", "?"),
        "dimension": gap["dimension"],
        "time": datetime.now().isoformat(),
    })
    GENERATED_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2))

    return new_id

def one_cycle():
    """一次生成检察"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 契约自动生成检察")

    gaps = find_gaps()
    print(f"  发现{len(gaps)}个未覆盖维度:")
    for g in gaps:
        print(f"    - {g['dimension']}: {g['desc']}")

    if not gaps:
        print("  全部维度已覆盖，无需生成新契约")
        return

    # 为第一个缺口生成契约
    gap = gaps[0]
    print(f"  为'{gap['dimension']}'生成契约...")
    contract = generate_contract(gap)

    if contract:
        new_id = register_contract(contract, gap)
        print(f"  ✅ 新契约#{new_id}: {contract.get('name','?')} — {contract.get('desc','?')[:60]}")
    else:
        print(f"  ❌ 生成失败")

    # 写入海马体
    try:
        hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
        hip["causal_chains"].append({
            "content": f"[契约自动生成] 缺口:{gap['dimension']} → 新契约:{contract.get('name','?') if contract else '失败'}",
            "source": "auto_contract_generator",
            "tags": ["契约生成", "元递归", gap["dimension"]],
            "timestamp": datetime.now().isoformat(),
        })
        (CLUSTER / "hippocampus_memory.json").write_text(json.dumps(hip, ensure_ascii=False, indent=2))
    except Exception:
        pass

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        print("契约自动生成守护启动(每1800秒)")
        while True:
            one_cycle()
            time.sleep(1800)
    else:
        one_cycle()
