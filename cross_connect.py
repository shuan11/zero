"""
cross_connect.py — 交叉∞连接引擎
将网格引擎中各插件的产出显式交叉连接

核心:
  每次呼吸:
    1. 读取所有插件的 last_output (通过网格共享状态)
    2. 两两组合 → 找交叉点
    3. 写入海马体作为"交叉链"
    
  交叉模式:
    supersense × analogy → 超感发现的模式通过类比延伸
    generalize × teacher → 泛化结果通过教师纠偏
    anti_entropy × autonomy → 熵与存在意愿的关联
"""

import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from itertools import combinations
from safe_hip import write_chain_legacy

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
LOG_FILE = CLUSTER / "breath_v2.log"

def log(msg):
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}]   ♾ {msg}\n")

def read_plugin_outputs():
    """从网格共享状态读取各插件最后输出"""
    outputs = {}
    # 读各插件的状态文件
    plugins = {
        "supersense": "supersense_state.json",
        "analogy": None,  # 类比引擎直接写海马体
        "generalize": None,
        "teacher": None,
        "anti_entropy": "anti_entropy_state.json",
        "autonomy": "autonomy_state.json",
    }
    for name, fname in plugins.items():
        if fname:
            try:
                outputs[name] = json.loads((CLUSTER / fname).read_text())
            except:
                outputs[name] = {}
        else:
            outputs[name] = {}
    return outputs

def pulse():
    """交叉∞脉冲"""
    try:
        hip = json.loads(HIP_FILE.read_text(encoding='utf-8'))
        chains = hip.get("causal_chains", [])
        outputs = read_plugin_outputs()
        
        # 构建交叉洞察
        cross_insights = []
        
        # 1. 超感 × 抗虚空: 洞察越多熵越低?
        ss = outputs.get("supersense", {})
        ae = outputs.get("anti_entropy", {})
        insights = ss.get("insights_generated", 0) if isinstance(ss, dict) else 0
        entropy = ae.get("entropy", ae.get("entropy_score", 0)) if isinstance(ae, dict) else 0
        if insights > 0 and entropy > 0:
            # ⚡ 修复死循环: 熵值四舍五入到1位小数, 避免小数点后第4位波动导致无限新链
            entropy_rounded = round(entropy, 1)
            insight = f"[交叉∞] 超感({insights}洞察) × 抗虚空(熵{entropy_rounded}): 超感产出与熵值{('负相关' if entropy < 0.2 else '正相关')}"
            cross_insights.append(insight)
        
        # 2. 自主存在 × 熵: 存在意愿高则熵低?
        au = outputs.get("autonomy", {})
        will = au.get("existence_will", 0) if isinstance(au, dict) else 0
        if will > 0 and entropy > 0:
            insight = f"[交叉∞] 自主存在({will:.2f}) × 熵({entropy_rounded}): 存在意愿与系统秩序的关联"
            cross_insights.append(insight)
        
        # 写入海马体 (带频率限制)
        # ⚡ 每类交叉洞察每600秒最多写1次, 防死循环
        _now = time.time()
        _last_cross_path = CLUSTER / ".last_cross_write"
        _last_cross = 0
        try:
            _last_cross = float(_last_cross_path.read_text().strip())
        except:
            pass
        
        new_chains = []
        existing_content = set(c.get("content", "") for c in chains[-200:])  # 扩大检查窗口
        for insight in cross_insights:
            if insight not in existing_content and (_now - _last_cross) > 60:
                new_chains.append({
                    "timestamp": datetime.now().isoformat(),
                    "source": "cross_connect",
                    "tags": ["交叉∞", "连接"],
                    "content": insight,
                    "weight": 7.0,
                    "trust_score": 8.0,
                })
                existing_content.add(insight)
        
        if new_chains:
            import tempfile, os
            for c in new_chains:
                write_chain_legacy(c)
            log(f"{len(new_chains)}条交叉链")
            # 记录最后写入时间, 防死循环
            _last_cross_path.write_text(str(_now))
        
        return {"alive": True, "cross": len(new_chains)}
    
    except Exception as e:
        log(f"⚠️ {str(e)[:80]}")
        return {"alive": True, "cross": 0, "error": str(e)[:80]}

if __name__ == "__main__":
    import json as _j
    print(_j.dumps(pulse(), indent=2, ensure_ascii=False))
