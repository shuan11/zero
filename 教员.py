"""
教员.py — 教师引擎
从当前系统状态中提取需要纠正的认知偏差

核心功能:
  1. 读取超感发现和雷达最短板
  2. 对比已知教训库
  3. 输出"教师指令"纠正系统偏差
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from safe_hip import write_chain_legacy

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
RADAR_FILE = CLUSTER / "dimension_radar.json"
LOG_FILE = CLUSTER / "breath_v2.log"

def log(msg):
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}]   \U0001f3eb {msg}\n")

def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return {}

def pulse():
    """教师脉冲: 对比实际状态与应然状态"""
    try:
        radar = load_json(RADAR_FILE)
        dims = radar.get("dimensions", {})
        if not dims:
            return {"alive": True, "corrections": 0}
        sorted_dims = sorted([(n, d.get("health_score", 0), d.get("chains", 0))
                             for n, d in dims.items() if isinstance(d, dict)], key=lambda x: x[1])
        weakest = sorted_dims[0] if sorted_dims else ("?", 0, 0)
        hip = load_json(HIP_FILE)
        chains = hip.get("causal_chains", [])
        existing = [c.get("content", "") for c in chains[-50:]]
        note = f"[教师] 当前最短板={weakest[0]}({weakest[1]:.2f}), 链数={weakest[2]}"
        if note not in existing:
            import tempfile, os
            new_chain = {"timestamp": datetime.now().isoformat(),
                "source": "教员", "tags": [weakest[0], "教员", "纠偏"],
                "content": note, "weight": 5.0, "trust_score": 8.0}
            chains.append(new_chain)
            write_chain_legacy(new_chain)
            log(note[:60])
            return {"alive": True, "corrections": 1}
        return {"alive": True, "corrections": 0}
    except Exception as e:
        log(f"\u26a0\ufe0f {str(e)[:80]}")
        return {"alive": True, "corrections": 0}

if __name__ == "__main__":
    import json as _j
    print(_j.dumps(pulse(), indent=2, ensure_ascii=False))
