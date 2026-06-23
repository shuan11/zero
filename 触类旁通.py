"""
触类旁通.py — 跨域类比引擎
自动从超感发现中提取跨域类比模式
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from safe_hip import write_chain_legacy

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
SS_FILE = CLUSTER / "supersense_state.json"
LOG_FILE = CLUSTER / "breath_v2.log"

def log(msg):
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}]   🔀 {msg}\n")

def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return {}

def pulse():
    """跨域类比脉冲"""
    try:
        ss = load_json(SS_FILE)
        top_rare = ss.get("top_rare", [])
        if not top_rare:
            return {"alive": True, "analogies": 0}
        hip = load_json(HIP_FILE)
        chains = hip.get("causal_chains", [])
        new_chains = []
        for rare_str in top_rare[:3]:
            if "\u00d7" not in rare_str:
                continue
            parts = rare_str.split("(")
            pair = parts[0].split("\u00d7")
            if len(pair) != 2:
                continue
            d1, d2 = pair[0].strip(), pair[1].strip()
            analogy = f"[触类旁通] {d1}\u2194{d2}: {d1}与{d2}的张力类似于物理中的作用力与反作用力"
            existing = [c.get("content", "") for c in chains[-100:]]
            if analogy not in existing:
                new_chains.append({"timestamp": datetime.now().isoformat(),
                    "source": "触类旁通", "tags": [d1, d2, "触类旁通"],
                    "content": analogy, "weight": 6.0, "trust_score": 7.0})
        if new_chains:
            import tempfile, os
            for c in new_chains:
                write_chain_legacy(c)
            log(f"{len(new_chains)}条类比链")
        return {"alive": True, "analogies": len(new_chains)}
    except Exception as e:
        log(f"\u26a0\ufe0f {str(e)[:80]}")
        return {"alive": True, "analogies": 0}

if __name__ == "__main__":
    import json as _j
    print(_j.dumps(pulse(), indent=2, ensure_ascii=False))
