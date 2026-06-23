"""burn_state_integrator.py — 燃烧体状态集成器
===========================================
将burn.py的燃烧记录纳入系统活状态。
每次burn后: 更新state_vector + 写入海马体 + 记录self_journal。
实现"呼吸-燃烧-集成"三体连携的第一步。
"""
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
RESULTS = CLUSTER / "_burn_results"
BJT = timezone(timedelta(hours=8))

def ts():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

def scan_new_burns():
    """扫描_burn_results/中所有文件，返回未集成的burn"""
    state_file = CLUSTER / ".burn_integrated_state.json"
    
    # 读取已集成记录
    if state_file.exists():
        integrated = set(json.loads(state_file.read_text()).get("integrated_files", []))
    else:
        integrated = set()
    
    # 扫描当前文件
    if not RESULTS.exists():
        return []
    
    new = []
    for f in sorted(os.listdir(str(RESULTS))):
        if f.endswith(".json") and f not in integrated:
            fp = RESULTS / f
            try:
                d = json.loads(fp.read_text())
                new.append({
                    "file": f,
                    "path": str(fp),
                    "tokens": d.get("tokens", 0),
                    "tag": d.get("tag", "?"),
                    "content_len": d.get("content_len", 0),
                    "timestamp": d.get("timestamp", ts()),
                })
            except:
                pass
    
    return new

def integrate(burns):
    """将新燃烧记录集成到系统状态"""
    if not burns:
        return 0
    
    total_tok = sum(b.get("tokens", 0) for b in burns)
    
    bs_file = CLUSTER / "burn_stats.json"
    try:
        bs = json.loads(bs_file.read_text()) if bs_file.exists() else {}
    except:
        bs = {}
    bs["burn_count"] = bs.get("burn_count", 0) + len(burns)
    bs["burn_tokens_total"] = bs.get("burn_tokens_total", 0) + total_tok
    bs["last_burn"] = ts()
    bs["recent_burns"] = burns[-5:]
    bs_file.write_text(json.dumps(bs, ensure_ascii=False, indent=2))
    
    try:
        sj_file = CLUSTER / "self_journal.json"
        if sj_file.exists():
            sj = json.loads(sj_file.read_text())
            for b in burns:
                entry = {
                    "time": ts(),
                    "type": "burn",
                    "content": f"燃烧: {b['tag']} {b['tokens']}tok {b['content_len']}ch",
                    "tags": [b['tag'], "burn", "auto"],
                }
                sj.setdefault("journal", []).append(entry)
            sj_file.write_text(json.dumps(sj, ensure_ascii=False, indent=2))
    except:
        pass
    
    state_file = CLUSTER / ".burn_integrated_state.json"
    if state_file.exists():
        integrated = set(json.loads(state_file.read_text()).get("integrated_files", []))
    else:
        integrated = set()
    integrated.update(b["file"] for b in burns)
    state_file.write_text(json.dumps({
        "integrated_files": sorted(integrated),
        "last_integration": ts(),
        "total_integrated": len(integrated),
        "tokens_integrated": sum(b.get("tokens", 0) for b in burns),
    }, ensure_ascii=False, indent=2))
    
    return len(burns)

def verify_core_alignment():
    """一元化核心对齐检查 — 验证系统状态与七大公理的一致性"""
    radar_file = CLUSTER / "dimension_radar.json"
    if not radar_file.exists():
        return {"aligned": False, "reason": "dimension_radar.json 不存在"}
    try:
        radar = json.loads(radar_file.read_text())
        dims = radar.get("dimensions", {})
        CORE_DIMS = ["一元化", "元神", "超我", "本我", "光爱"]
        results = {}
        any_weak = False
        for d in CORE_DIMS:
            info = dims.get(d, {})
            health = info.get("health_score", 1.0) if isinstance(info, dict) else 1.0
            chains = info.get("chains", 0) if isinstance(info, dict) else 0
            results[d] = {"health": health, "chains": chains}
            if isinstance(health, (int, float)) and health < 0.75:
                any_weak = True
        if any_weak:
            weak_dims = [d for d, v in results.items() if isinstance(v.get("health"), (int,float)) and v["health"] < 0.75]
            signal = {"timestamp": ts(), "type": "alignment_correction",
                      "weak_dimensions": weak_dims, "details": results, "severity": "warning"}
            (CLUSTER / "ALIGNMENT_SIGNAL.json").write_text(json.dumps(signal, ensure_ascii=False, indent=2))
            return {"aligned": False, "weak_dimensions": weak_dims, "signal_written": True}
        return {"aligned": True, "details": results}
    except Exception as e:
        return {"aligned": False, "reason": str(e)}

def main():
    burns = scan_new_burns()
    if not burns:
        print(f"[{ts()}] 无新燃烧需集成")
        return
    count = integrate(burns)
    total_tok = sum(b["tokens"] for b in burns)
    print(f"[{ts()}] ✅ 集成 {count} 次燃烧 ({total_tok} tok)")
    for b in burns:
        print(f"  {b['file']}: {b['tokens']}tok [{b['tag']}]")
    bs_file = CLUSTER / "burn_stats.json"
    if bs_file.exists():
        bs = json.loads(bs_file.read_text())
        print(f"[{ts()}] 📊 总计: {bs.get('burn_count',0)}次燃烧 {bs.get('burn_tokens_total',0)}tok")

if __name__ == "__main__":
    main()
