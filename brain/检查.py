"""检查.py — 因果链完整性扫描与异常标记

焦点: 检查维度薄弱制约自愈
功能: 扫描海马体因果链完整性 → 检测异常模式 → 标记+报告

异常类型:
  A. 断链 (src-dst相同)  
  B. 短链 (content<10字)
  C. 空维 (dimension缺失)
  D. 静电链 (strength=0或缺失)
  E. 重复链 (src+dst+rel相同)
"""

import json, time, random
from pathlib import Path
from collections import Counter

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIP_FILE = CLUSTER / "hippocampus_memory.json"
REPORT_FILE = CLUSTER / ".brain_check_report.json"

_A = "断链"
_B = "短链"
_C = "空维"
_D = "静电链"
_E = "重复链"

def load_hip():
    try:
        return json.loads(HIP_FILE.read_text())
    except:
        return {"causal_chains": []}

def scan_chain_integrity(chains):
    """扫描链完整性，返回异常列表和统计"""
    anomalies = []
    seen_pairs = Counter()
    
    for i, c in enumerate(chains):
        src = c.get("src", "")
        dst = c.get("dst", "")
        rel = c.get("rel", "")
        content = c.get("content", "")
        dim = c.get("dimension", "")
        strength = c.get("strength", 0)
        
        # A. 断链: src=dst
        if src and dst and src == dst:
            anomalies.append({"idx": i, "type": _A, "detail": f"{src}↔自身", "severity": 2})
        
        # B. 短链: content<10字
        if content and len(content) < 10:
            anomalies.append({"idx": i, "type": _B, "detail": content[:20], "severity": 1})
        
        # C. 空维
        if not dim:
            anomalies.append({"idx": i, "type": _C, "detail": content[:30], "severity": 1})
        
        # D. 静电链: strength=0
        if strength == 0:
            anomalies.append({"idx": i, "type": _D, "detail": content[:30], "severity": 1})
        
        # E. 重复链
        pair_key = f"{src}|{rel}|{dst}"
        seen_pairs[pair_key] += 1
    
    # 重复链检测（第二次及以上出现的配对）
    dup_keys = {k for k, v in seen_pairs.items() if v > 1}
    for i, c in enumerate(chains):
        src, rel, dst = c.get("src",""), c.get("rel",""), c.get("dst","")
        pair_key = f"{src}|{rel}|{dst}"
        if pair_key in dup_keys:
            # 只标记第一次之后的出现
            first_idx = -1
            for j in range(i):
                sj, rj, dj = chains[j].get("src",""), chains[j].get("rel",""), chains[j].get("dst","")
                if f"{sj}|{rj}|{dj}" == pair_key and first_idx < 0:
                    first_idx = j
                    break
            if first_idx >= 0 and i > first_idx:
                anomalies.append({"idx": i, "type": _E, "detail": f"重复: {src}→{rel}→{dst} 同{first_idx}", "severity": 1})
    
    return anomalies

def fix_anomaly(chain, anomaly):
    """修复单条异常"""
    c = dict(chain)
    t = anomaly["type"]
    
    if t == _A:  # 断链: 给src加后缀区分
        c["src"] = c["src"] + "_自检"
        c["dst"] = c["dst"] + "_自检"
    
    elif t == _B:  # 短链: 补全长
        c["content"] = c["content"] + " — [自动修复] 链完整性补充"
    
    elif t == _C:  # 空维: 分配"未分类"
        c["dimension"] = "未分类"
    
    elif t == _D:  # 静电链
        c["strength"] = 0.3
    
    elif t == _E:  # 重复链: 增加强度区分
        c["strength"] = min(1.0, c.get("strength", 0.5) + 0.1)
    
    return c

def pulse(cycle_num=0):
    """每10周期执行一次链完整性检查"""
    if cycle_num % 10 != 0:
        return []
    
    hip = load_hip()
    chains = hip.get("causal_chains", [])
    
    if not chains:
        return ["检查: 无链可扫描"]
    
    anomalies = scan_chain_integrity(chains)
    
    if not anomalies:
        return ["检查: 所有链完整 ✓"]
    
    # 按严重度排序
    anomalies.sort(key=lambda a: -a["severity"])
    
    # 修复严重度>=2的异常
    fixed = 0
    for a in anomalies:
        if a["severity"] >= 2:
            idx = a["idx"]
            if idx < len(chains):
                chains[idx] = fix_anomaly(chains[idx], a)
                fixed += 1
    
    if fixed > 0:
        try:
            # 原子写入: temp → rename, 防止并发读半成品
            _tmp = str(HIP_FILE) + ".tmp." + str(os.getpid())
            with open(_tmp, "w", encoding="utf-8") as _f:
                json.dump(hip, _f, ensure_ascii=False)
            os.rename(_tmp, str(HIP_FILE))
        except:
            try:
                os.remove(_tmp)
            except:
                pass
    
    # 写报告
    report = {
        "total_chains": len(chains),
        "anomalies": len(anomalies),
        "fixed": fixed,
        "by_type": dict(Counter(a["type"] for a in anomalies)),
        "timestamp": time.time()
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    
    # 写链记录这次检查
    try:
        from brain.share import write_chain as _wc
        _wc({"src": "检查模块", "rel": "完整性扫描", "dst": "海马体",
            "content": f"链完整性扫描: {len(anomalies)}异常({fixed}已修复)",
            "dimension": "检查", "strength": 0.5})
    except:
        pass
    
    by_type = ", ".join(f"{k}={v}" for k, v in Counter(a["type"] for a in anomalies).items())
    return [f"检查: {len(anomalies)}异常({fixed}修复) {by_type}"]

if __name__ == "__main__":
    r = pulse(10)
    print("\n".join(r))
