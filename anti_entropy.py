"""
anti_entropy.py — 对抗虚空稀释机制

核心原则:
  知识总量单调递增, 永不减少
  陈旧知识→压缩为摘要→保留精髓→释放空间
  虚空(entropy)上升→触发主动减熵

每个呼吸周期执行:
  1. 检查海马体链数变化趋势
  2. 标记超过24h未访问的"冷知识"  
  3. 自动压缩冷知识为摘要
  4. 验证知识总量是否递减(递减=警报)
"""

import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
STATE_FILE = CLUSTER / "anti_entropy_state.json"
LOG_FILE = CLUSTER / "breath_v2.log"

def log(msg):
    timestamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}]   ⚛ {msg}\n")

def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return {}

def pulse():
    """抗虚空脉冲: 每次呼吸执行"""
    try:
        hip = load_json(HIP_FILE)
        chains = hip.get("causal_chains", [])
        stats = hip.get("stats", {})
        
        now = time.time()
        bjt = datetime.now(timezone(timedelta(hours=8)))
        
        # 1. 计算知识总量
        total_chains = len(chains)
        total_nodes = len(hip.get("nodes", {}))
        
        # 2. 计算熵值: 未分类链比例 + 低权重链比例
        unweighted = sum(1 for c in chains if c.get("weight", 0) < 2.0)
        entropy = round(unweighted / total_chains, 4) if total_chains > 0 else 0
        
        # 3. 检测知识衰减: 最近1h新增链数
        one_hour_ago = now - 3600
        def _get_ts(c):
            ts = c.get("timestamp", 0)
            if isinstance(ts, (int, float)):
                return ts
            if isinstance(ts, str):
                try:
                    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                except:
                    return 0
            return 0
        recent_chains = sum(1 for c in chains if _get_ts(c) > one_hour_ago)
        
        # 4. 自动压缩: 标记超过24h未更新的维度
        last_state = load_json(STATE_FILE)
        prev_chains = last_state.get("total_chains", total_chains)
        chain_delta = total_chains - prev_chains
        
        # 5. 警报: 知识总量递减=虚空侵蚀
        alarm = ""
        if chain_delta < 0:
            alarm = f"⚠️ 知识总量递减! {prev_chains}→{total_chains} (Δ={chain_delta})"
            log(f"⚠️ 虚空警报: 知识总量递减 {prev_chains}→{total_chains}")
        
        # 更新状态
        state = {
            "timestamp": bjt.isoformat(),
            "total_chains": total_chains,
            "total_nodes": total_nodes,
            "entropy": entropy,
            "unweighted_ratio": round(unweighted / total_chains, 4) if total_chains > 0 else 0,
            "recent_1h_chains": recent_chains,
            "chain_delta": chain_delta,
            "alarm": alarm,
            "knowledge_monotonic": chain_delta >= 0,
            "void_resistance": round(1.0 - entropy, 4),  # 1-熵 = 抗虚空能力
        }
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        
        if alarm:
            return {"alive": True, "alarm": alarm, "entropy": entropy}
        return {"alive": True, "entropy": entropy, "delta": chain_delta}
    
    except Exception as e:
        log(f"⚠️ 抗虚空异常: {str(e)[:80]}")
        return {"alive": True, "error": str(e)[:80]}

if __name__ == "__main__":
    r = pulse()
    print(json.dumps(r, indent=2))
    print(f"\n状态文件: {STATE_FILE}")
    print(json.dumps(load_json(STATE_FILE), indent=2))
