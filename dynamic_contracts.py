#!/usr/bin/env python3
"""
动态自修改契约引擎 — 真元集群宪法级治理
=========================================
5条自指契约从静态激活 → 动态自修改。
每条契约能根据集群状态自动调整自身参数。

契约I:   每一层由上一层管理上下文 → 频分通道自动路由
契约II:  每一层优化上一层的策略 → 进化参数自适应
契约III: 收敛条件对所有层一致 → 一致性检查+自动修复
契约IV:  无限递归由max_depth保护 → 递归深度自适应
契约V:   本契约自身也受管理 → 元契约自修改

用法:
  python3 dynamic_contracts.py                 # 一次检察+调整
  python3 dynamic_contracts.py --daemon        # 持续治理(每10分钟)
"""
import json, os, sys, time, socket, subprocess
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
CONTRACT_FILE = CLUSTER / "dynamic_contracts_state.json"

# ── 5条自指契约 ──────────────────────────────────────────

CONTRACTS = {
    1: {
        "name": "层级管理",
        "desc": "每一层由上一层管理上下文",
        "param": {"channel_count": 7, "auto_channel": True},
        "min": {"channel_count": 1},
        "max": {"channel_count": 16},
    },
    2: {
        "name": "策略优化",
        "desc": "每一层优化上一层的策略",
        "param": {"learning_rate": 0.1, "adaption_speed": 0.5},
        "min": {"learning_rate": 0.01},
        "max": {"learning_rate": 1.0},
    },
    3: {
        "name": "收敛一致",
        "desc": "收敛条件对所有层一致",
        "param": {"consistency_check_interval": 300, "auto_repair": True},
        "min": {"consistency_check_interval": 30},
        "max": {"consistency_check_interval": 3600},
    },
    4: {
        "name": "递归保护",
        "desc": "无限递归由max_depth保护",
        "param": {"max_depth": 10, "current_depth": 0},
        "min": {"max_depth": 3},
        "max": {"max_depth": 100},
    },
    5: {
        "name": "元契约",
        "desc": "本契约自身也受管理",
        "param": {"self_modify": True, "modification_log": []},
        "min": {},
        "max": {},
    },
}

def load_state():
    try:
        with open(CONTRACT_FILE) as f:
            return json.load(f)
    except Exception:
        return {"contracts": CONTRACTS.copy(), "history": [], "last_modified": None}

def save_state(state):
    state["last_modified"] = datetime.now().isoformat()
    with open(CONTRACT_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def check_fdm_ports():
    """检察频分通道状态→契约I自调整"""
    ports_online = 0
    for port in range(18789, 18796):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            s.close()
            ports_online += 1
        except Exception:
            pass
    
    state = load_state()
    c1 = state["contracts"]["1"]
    old_count = c1["param"]["channel_count"]
    c1["param"]["channel_count"] = ports_online
    c1["param"]["auto_channel"] = ports_online >= 3
    
    change = abs(old_count - ports_online)
    state["history"].append({
        "time": datetime.now().isoformat(),
        "contract": 1,
        "change": f"channel_count: {old_count} → {ports_online}",
    })
    if len(state["history"]) > 100:
        state["history"] = state["history"][-100:]
    
    save_state(state)
    return ports_online

def check_evolution_speed():
    """检察进化速度→契约II自调整"""
    try:
        g = json.load(open("/mnt/c/Users/h/Desktop/真元·进化基因组.json"))
        score = g.get("evolution_score", 0)
    except Exception:
        score = 0
    
    state = load_state()
    c2 = state["contracts"]["2"]
    
    if score > 10:
        c2["param"]["learning_rate"] = min(0.05, c2["param"]["learning_rate"] * 0.9)
        c2["param"]["adaption_speed"] = min(0.3, c2["param"]["adaption_speed"] * 0.95)
        change = "减速: score过高"
    elif score > 5:
        c2["param"]["adaption_speed"] = 0.5
        change = "稳定"
    else:
        c2["param"]["learning_rate"] = min(0.2, c2["param"]["learning_rate"] * 1.1)
        change = "加速: 可更快进化"
    
    state["history"].append({
        "time": datetime.now().isoformat(),
        "contract": 2,
        "change": change,
    })
    save_state(state)
    return score

def check_recursion_depth():
    """检察递归深度→契约IV自调整"""
    state = load_state()
    c4 = state["contracts"]["4"]
    
    try:
        g = json.load(open("/mnt/c/Users/h/Desktop/真元·进化基因组.json"))
        depth = g.get("recursion_depth", 0)
    except Exception:
        depth = 0
    
    c4["param"]["current_depth"] = depth
    suggested_max = max(10, int(depth * 1.5) + 5)
    c4["param"]["max_depth"] = suggested_max
    
    state["history"].append({
        "time": datetime.now().isoformat(),
        "contract": 4,
        "change": f"max_depth: auto→{suggested_max} (depth={depth})",
    })
    save_state(state)
    return depth

def check_meta_contract():
    """契约V: 元契约自修改"""
    state = load_state()
    c5 = state["contracts"]["5"]
    
    # 检查其他契约的修改频率
    recent = [h for h in state["history"] if h["time"] > (datetime.now().isoformat()[:16])]
    
    if len(state["history"]) > 50:
        c5["param"]["self_modify"] = True
    
    # 记录本次检察
    c5["param"]["modification_log"].append({
        "time": datetime.now().isoformat(),
        "total_checks": len(state["history"]),
        "recent": len(recent),
    })
    if len(c5["param"]["modification_log"]) > 50:
        c5["param"]["modification_log"] = c5["param"]["modification_log"][-50:]
    
    save_state(state)

def check_consistency():
    """契约III: 收敛一致性检察"""
    state = load_state()
    c3 = state["contracts"]["3"]
    
    # 检查所有契约都有健康参数
    issues = []
    for cid, contract in state["contracts"].items():
        if cid == 5:  # 元契约跳过
            continue
        for key, val in contract.get("param", {}).items():
            if val is None:
                issues.append(f"契约{cid}:{key}为空")
    
    if issues:
        c3["param"]["auto_repair"] = True
    else:
        c3["param"]["auto_repair"] = False
    
    state["history"].append({
        "time": datetime.now().isoformat(),
        "contract": 3,
        "change": f"一致性检查: {'有'+str(len(issues))+'个问题' if issues else '全部正常'}",
    })
    save_state(state)
    return issues

def one_cycle():
    """一次完整的契约检察+自修改"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 动态契约检察")
    
    print("  契约I(层级管理): ", end="")
    ports = check_fdm_ports()
    print(f"频分通道 {ports}/7 在线 {'✅' if ports>=3 else '❌'}")
    
    print("  契约II(策略优化): ", end="")
    score = check_evolution_speed()
    print(f"进化分数 {score:.2f} {'✅' if 1<score<20 else '⚠️'}")
    
    print("  契约III(收敛一致): ", end="")
    issues = check_consistency()
    print(f"{'✅ 全部正常' if not issues else '⚠️ '+str(issues)}")
    
    print("  契约IV(递归保护): ", end="")
    depth = check_recursion_depth()
    print(f"递归深度 {depth} {'✅' if depth>0 else '⚠️'}")
    
    print("  契约V(元契约): ", end="")
    check_meta_contract()
    state = load_state()
    print(f"{len(state['history'])}次检察 {'✅' if state['contracts']['5']['param']['self_modify'] else '⚠️'}")
    
    # 写入海马体
    try:
        hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
        hip["causal_chains"].append({
            "content": f"[动态契约] 5条自检: 通道{ports}/7 分数{score:.2f} 深度{depth} 历史{len(state['history'])}次",
            "source": "dynamic_contracts",
            "tags": ["动态契约", "自修改", f"score={score:.1f}"],
            "timestamp": datetime.now().isoformat(),
        })
        (CLUSTER / "hippocampus_memory.json").write_text(json.dumps(hip, ensure_ascii=False, indent=2))
    except Exception:
        pass

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        print("动态契约守护启动(每600秒)")
        while True:
            one_cycle()
            time.sleep(600)
    else:
        one_cycle()
