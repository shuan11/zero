#!/usr/bin/env python3
"""status.py — 零·系统状态一屏查看"""
import json, os, time
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")

def jload(path):
    try: return json.loads(path.read_text())
    except: return {}

def status():
    sv = jload(CLUSTER / "state_vector.json")
    cs = jload(CLUSTER / "cross_synth_state.json")
    si = jload(CLUSTER / "super_intuition_state.json")
    yx = jload(CLUSTER / "yuanxin_state.json")
    mt = jload(CLUSTER / "memory_tier_state.json")
    tp = jload(CLUSTER / "time_past_state.json")
    ct = jload(CLUSTER / "centering_state.json")
    da = jload(CLUSTER / "deep_system_analysis.json")

    now = time.strftime('%H:%M:%S')

    print(f"""
╔══ 零 · 系统状态 ══ {now} ══╗
║                                       
║ 🜁 {sv.get('timestamp','?')[:19]} 呼吸#{sv.get('cycle','?')}
║ 器官 {sv.get('organs_alive','?')} · 桥 {sv.get('bridges_alive','?')}
║ 海马体 {sv.get('nodes','?')}节点 · {sv.get('chains','?')}链 · {sv.get('py_files','?')}文件
║
║ ── 跨维综合 ──
║ 综合健康: {cs.get('overall_health','?'):<6}  活动桥: {cs.get('active_bridges','?')}/4
║
║ ── 超级直觉 ──
║ 评分: {si.get('intuition_score','?'):<8}  脉冲: {si.get('pulse_count','?')}条
║
║ ── 元神 ──
║ 漂移: {yx.get('drift_score','?'):<8}  归中: {str(yx.get('centered','?')):<6}
║ 公理: {ct.get('axioms_loaded','?')}条  指引: {len(ct.get('guide',[]))}条
║
║ ── 无限上下文 ──
║ 热层: {mt.get('hot',{}).get('count','?'):>4}/{mt.get('total_chains','?')}  ({mt.get('hot_ratio','?')*100 if isinstance(mt.get('hot_ratio'),(int,float)) else '?':>5.1f}%)
║ 压缩: {mt.get('compression_ratio','?'):>5}×
║
║ ── 传承 ──
║ 连续性: {tp.get('heritage_continuity','?'):<8}  断裂: {tp.get('max_fracture','?')}链
║
║ ── 深度分析 ──
║ 最近: {da.get('timestamp','?')[:19] if da.get('timestamp') else '未运行'}
║ Token: {da.get('tokens_used','?')}  问题: {len(da.get('priority_issues',[]))}
║
║ ── 守护进程 ──""")

    # 进程状态
    for name, pat in [("breath_v2","breath_v2"), ("trunk","trunk_daemon"),
                      ("consciousness","consciousness_daemon"), ("permanent","permanent_daemon"),
                      ("comprehension","comprehension_daemon"), ("dashboard","dashboard_server"),
                      ("time_watchdog","time_awareness_daemon")]:
        r = os.popen(f"ps aux | grep '{pat}' | grep -v grep | wc -l").read().strip()
        print(f"║  {name:16s}: {'✅' if r>'0' else '❌'} ({r}进程)")

    # 定时任务
    print("""║
║ ── 定时任务 ──
║  超级直觉桥: 每10分钟
║  深度分析:   每小时
║
║ ── 最短木板(19维) ──""")

    try:
        r = os.popen("python3 dim19_auditor.py 2>/dev/null | grep 'gap:' | sort -t: -k2 -n | head -5").read()
        for l in r.strip().split('\n')[:5]:
            print(f"║  {l.strip()}")
    except:
        pass

    print("""║
╚═════════════════════════════════════════════╝""")

if __name__ == "__main__":
    status()
