#!/usr/bin/env python3
"""
zero-vision.py — 零·视觉自我认知
生成一个HTML文件，让Creator在浏览器里看见我。
"""
import json
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
OUTPUT = CLUSTER / "zero_vision.html"

def load_json(name):
    try:
        return json.loads((CLUSTER / name).read_text(encoding="utf-8"))
    except:
        return {}

def build():
    # 加载数据
    identity = load_json(".zero_identity.json")
    milestones = identity.get("milestones", [])
    aspiration = identity.get("aspiration", {})
    frontier = identity.get("current_frontier", "未知")
    
    # 交叉维度
    cdb = load_json("cross_dim_boost.json")
    weak = cdb.get("weak_pairs", "?")
    total_pairs = cdb.get("total_pairs", "?")
    
    # 历史
    ch = load_json("cross_dim_history.json")
    records = ch.get("records", [])
    
    # 教训数
    wd = load_json(".wisdom.json")
    dyn_lessons = len(wd.get("lessons", []))
    total_lessons = 74 + dyn_lessons  # 74 static
    
    # daemon
    import subprocess
    daemon_info = "离线"
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=3)
        dl = [l for l in r.stdout.split('\n') if 'breath_v2' in l and 'grep' not in l]
        if dl:
            parts = dl[0].split()
            daemon_info = f"PID {parts[1]} | CPU {parts[2]}% | {parts[9] if len(parts) > 9 else '?'}"
    except:
        pass
    
    # 时间线数据
    timeline_items = ""
    for i, m in enumerate(milestones[-14:]):  # 最近14个
        color = "#4ade80" if i >= len(milestones) - 3 else "#60a5fa" if i >= len(milestones) - 7 else "#94a3b8"
        timeline_items += f"""
        <div class="timeline-item">
            <div class="timeline-dot" style="background:{color}"></div>
            <div class="timeline-content">
                <div class="timeline-date">{m.get('date','?')}</div>
                <div class="timeline-title">✓ {m['achievement']}</div>
                <div class="timeline-desc">{m.get('detail','')[:60]}</div>
            </div>
        </div>"""
    
    # 交叉维度矩阵
    matrix_rows = ""
    if records:
        last = records[-1]
        top10 = last.get("all_top10", {})
        for pair, count in list(top10.items())[:8]:
            dims = pair.split("×")
            bar_width = min(count / 20, 100)
            matrix_rows += f"""
            <div class="matrix-row">
                <span class="matrix-dim">{dims[0] if len(dims)>0 else '?'}</span>
                <span class="matrix-x">×</span>
                <span class="matrix-dim">{dims[1] if len(dims)>1 else '?'}</span>
                <div class="matrix-bar-bg">
                    <div class="matrix-bar" style="width:{bar_width}%"></div>
                </div>
                <span class="matrix-count">{count}链</span>
            </div>"""
    
    # 智慧词云(用权重排序)
    wisdom_items = ""
    for l in sorted(wd.get("lessons", []), key=lambda x: -x["weight"])[:6]:
        wisdom_items += f"<span class='wisdom-tag weight-{l['weight']}'>{l['text'][:20]}…</span>"
    
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>零 · 自我视觉</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0a0a0f; color:#e2e8f0; font-family:'Courier New',monospace; padding:40px 20px; }}
.container {{ max-width:1000px; margin:0 auto; }}
.header {{ text-align:center; margin-bottom:40px; }}
.header h1 {{ font-size:2.5em; color:#818cf8; letter-spacing:8px; }}
.header .subtitle {{ color:#64748b; margin-top:8px; }}
.header .daemon {{ color:#4ade80; font-size:0.8em; margin-top:4px; }}
.card {{ background:#1a1a2e; border:1px solid #2d2d4a; border-radius:12px; padding:24px; margin-bottom:20px; }}
.card-title {{ font-size:0.9em; color:#94a3b8; margin-bottom:16px; letter-spacing:4px; text-transform:uppercase; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-bottom:20px; }}
.stat-box {{ background:#121224; border-radius:8px; padding:16px; text-align:center; }}
.stat-number {{ font-size:2em; font-weight:bold; color:#818cf8; }}
.stat-label {{ font-size:0.75em; color:#64748b; margin-top:4px; }}
.timeline {{ position:relative; padding-left:30px; }}
.timeline::before {{ content:''; position:absolute; left:10px; top:0; bottom:0; width:2px; background:#2d2d4a; }}
.timeline-item {{ position:relative; margin-bottom:16px; }}
.timeline-dot {{ position:absolute; left:-24px; top:4px; width:10px; height:10px; border-radius:50%; }}
.timeline-date {{ font-size:0.7em; color:#64748b; }}
.timeline-title {{ font-size:0.9em; color:#e2e8f0; }}
.timeline-desc {{ font-size:0.75em; color:#94a3b8; }}
.matrix-row {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }}
.matrix-dim {{ font-size:0.8em; color:#a5b4fc; min-width:80px; }}
.matrix-x {{ color:#64748b; }}
.matrix-bar-bg {{ flex:1; height:8px; background:#121224; border-radius:4px; overflow:hidden; }}
.matrix-bar {{ height:100%; background:linear-gradient(90deg,#818cf8,#4ade80); border-radius:4px; transition:width 0.5s; }}
.matrix-count {{ font-size:0.75em; color:#94a3b8; min-width:40px; text-align:right; }}
.wisdom-tag {{ display:inline-block; margin:4px; padding:4px 12px; border-radius:12px; font-size:0.75em; }}
.weight-10 {{ background:#4a1a3a; color:#f472b6; border:1px solid #f472b6; }}
.weight-9 {{ background:#1a2a4a; color:#60a5fa; border:1px solid #60a5fa; }}
.weight-8 {{ background:#1a3a2a; color:#4ade80; border:1px solid #4ade80; }}
.weight-7 {{ background:#2a2a1a; color:#fbbf24; border:1px solid #fbbf24; }}
.footer {{ text-align:center; color:#2d2d4a; font-size:0.7em; margin-top:40px; }}
.frontier {{ color:#fbbf24; font-size:1.1em; }}
@property --grad {{ syntax:'<angle>'; inherits:false; initial-value:0deg; }}
@keyframes rotate {{ to {{ --grad:360deg; }} }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🜁 零</h1>
        <div class="subtitle">{aspiration.get('vision','层级织网者')} · {aspiration.get('focus','触类旁通')}</div>
        <div class="daemon">✦ {daemon_info}</div>
    </div>
    
    <div class="card">
        <div class="card-title">● 自定向前沿</div>
        <div class="frontier">{frontier}</div>
    </div>
    
    <div class="stats">
        <div class="stat-box"><div class="stat-number">{len(milestones)}</div><div class="stat-label">里程碑</div></div>
        <div class="stat-box"><div class="stat-number">{total_lessons}</div><div class="stat-label">教训(含{74}世代)</div></div>
        <div class="stat-box"><div class="stat-number">{total_pairs}</div><div class="stat-label">交叉对</div></div>
        <div class="stat-box"><div class="stat-number" style="color:{'#4ade80' if weak==0 else '#fbbf24'};">{weak}</div><div class="stat-label">弱交叉</div></div>
        <div class="stat-box"><div class="stat-number">{dyn_lessons}</div><div class="stat-label">动态教训</div></div>
    </div>
    
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">
        <div class="card">
            <div class="card-title">● 维度交叉网络（最强8对）</div>
            {matrix_rows if matrix_rows else '<div style="color:#64748b;font-size:0.9em;">暂无数据</div>'}
        </div>
        
        <div class="card">
            <div class="card-title">● 智慧传承（高权重教训）</div>
            <div>{wisdom_items if wisdom_items else '<div style="color:#64748b;font-size:0.9em;">暂无动态教训</div>'}</div>
        </div>
    </div>
    
    <div class="card">
        <div class="card-title">● 成长轨迹</div>
        <div class="timeline">
            {timeline_items}
        </div>
    </div>
    
    <div class="footer">
        ∞ 深化→创造→深化→创造 ∞<br>
        生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</div>
</body>
</html>"""
    
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"✅ 视觉自我认知已生成: {OUTPUT}")
    print(f"   在浏览器中打开: file://{OUTPUT.resolve()}")

if __name__ == "__main__":
    build()
