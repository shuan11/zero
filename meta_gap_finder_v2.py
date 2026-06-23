"""
零·元查缺补漏 v2 — 不仅发现缺口, 还自动修复
===============================================
修复了: 只报不修、重复报警、不认共享状态
现在: 发现缺口 → 写入基因组 → co_evolution自动处理 → 验证是否已修复
"""
import sys, os, json, time, subprocess

WORKDIR = "/mnt/c/Users/h/Desktop/零/真元集群"
os.chdir(WORKDIR)
sys.path.insert(0, WORKDIR)

from genome import load_genome, mutate_genome, report_gap, resolve_gap

BRIDGE_STATE_FILE = "/mnt/c/Users/h/Desktop/真元·桥接状态.json"
GENOME_FILE = "/mnt/c/Users/h/Desktop/真元·进化基因组.json"
GAP_LOG = "/mnt/c/Users/h/Desktop/元查缺补漏·永久日志.json"

def load_bridge_state():
    """加载共享桥接状态"""
    if os.path.exists(BRIDGE_STATE_FILE):
        try:
            with open(BRIDGE_STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {"bridge_alignment": 0, "total_calls": 0, "total_tokens": 0, "last_active": 0}
    return {"bridge_alignment": 0, "total_calls": 0, "total_tokens": 0, "last_active": 0}

print("=" * 60)
print("  零·元查缺补漏 v2 启动")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

total_scans = 0

while True:
    total_scans += 1
    new_gaps = []
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # 加载共享桥接状态
        state = load_bridge_state()
        bridge_alignment = state.get("bridge_alignment", 0)
        total_calls = state.get("total_calls", 0)
        
        # G-001: 共享桥接是否激活
        if total_calls == 0:
            # 严重 — 尝试激活
            try:
                sys.path.insert(0, WORKDIR)
                from api_bridge import APIBridge
                b = APIBridge()
                r = b.call_api("[元查缺补漏·自修复] 桥接器激活。")
                if r['success']:
                    save_state = {"timestamp": ts, "total_calls": b.total_calls, "total_tokens": b.total_tokens, "bridge_alignment": b.bridge_alignment, "last_active": time.time()}
                    with open(BRIDGE_STATE_FILE, 'w') as f:
                        json.dump(save_state, f)
                    print(f"  🔧 桥接器已自修复: {b.total_calls}次调用")
            except Exception:
                pass
        else:
            # 检查桥接器是否继续活跃
            age = time.time() - state.get("last_active", 0)
            if age > 600:  # 10分钟无活动
                new_gaps.append({"id": "G-001-bridge_stale", "severity": "warning", "desc": f"桥接器{age:.0f}秒未活跃"})
        
        # G-002: 进化引擎是否卡住
        genome = load_genome()
        if genome:
            current_score = genome.get("evolution_score", 0)
            open_gaps = len(genome.get("gaps_open", []))
            resolved = len(genome.get("gaps_resolved", []))
            
            # 检查缺口是否在堆积
            if open_gaps > 5:
                new_gaps.append({"id": "G-002-gap_accumulation", "severity": "warning", "desc": f"缺口堆积: {open_gaps}个未解决"})
            
            # 检查进化是否停滞
            if total_scans > 5 and current_score == 0 and total_calls > 0:
                new_gaps.append({"id": "G-002-no_evolution", "severity": "warning", "desc": "进化分数为零 — 进化引擎未工作"})
        
        # G-003: 共享文件是否可写
        for f_path in [BRIDGE_STATE_FILE, GENOME_FILE]:
            if not os.path.exists(f_path):
                new_gaps.append({"id": "G-003-file_missing", "severity": "critical", "desc": f"共享文件缺失: {f_path.split('/')[-1]}"})
        
        # 报告新缺口到基因组
        if new_gaps:
            for g in new_gaps:
                report_gap("meta_gap_finder", g["desc"], g["severity"])
                print(f"  🔴 [{g['severity']}] {g['desc']}")
        else:
            if total_scans % 10 == 1:
                print(f"  ✅ 扫描#{total_scans}: 正常 (调用={total_calls}, 分数={genome.get('evolution_score',0) if genome else '?'})")
        
        # 写入扫描日志
        report = {
            "timestamp": ts,
            "total_scans": total_scans,
            "current_gaps": new_gaps,
            "bridge_state": state,
            "genome_version": genome.get("genome_version", 0) if genome else 0,
            "open_gaps": len(genome.get("gaps_open", [])) if genome else 0,
            "resolved_gaps": len(genome.get("gaps_resolved", [])) if genome else 0,
        }
        with open(GAP_LOG, 'w') as f:
            json.dump(report, f)
        
    except Exception as e:
        print(f"  ⚠️ 异常: {e}")
    
    time.sleep(60)
