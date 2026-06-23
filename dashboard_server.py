#!/usr/bin/env python3
"""
真元集群·实时监控面板 (升级版)
================================
实时神经元/FDM总线/修复历史/海马体统计
4新API端点 + 动态HTML

启动: python3 dashboard_server.py [port]
浏览器: http://localhost:8080
"""
import os, json, subprocess, time, hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

BEIJING = timezone(timedelta(hours=8))

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(str(CLUSTER))

# ── 常量 ─────────────────────────────────────────────────
FDM_PORTS = [18789, 18790, 18791, 18792, 18793, 18794, 18795]
NEURON_NAMES = {
    "hermes":"Hermes","codex":"Codex CLI","claude":"Claude Code",
    "openclaw_wsl":"OpenClaw WSL","openclaw_win":"OpenClaw Win",
    "marvis_qq":"Marvis QQ","opengod":"OpenGod","openalien":"OpenAlien",
    "openinterpreter":"OpenInterpreter","autogpt":"AutoGPT",
}
# 反向映射: 显示名→id
NAME_TO_ID = {}
_DISPLAY_NAMES = [
    "Hermes","Codex CLI","Claude Code","OpenClaw WSL","OpenClaw Win",
    "Marvis QQ","OpenGod","OpenAlien","OpenInterpreter","AutoGPT",
]
# 10神经元角色
NEURON_ROLES = {
    "Hermes":"中央调度/主意识","Codex CLI":"执行臂·代码生成",
    "Claude Code":"分析臂·架构审查","OpenClaw WSL":"188专业Agent",
    "OpenClaw Win":"Windows桌面操作","Marvis QQ":"文档·浏览器·MCP",
    "OpenGod":"哲学·批判·反思","OpenAlien":"区块链·EOSIO",
    "OpenInterpreter":"自然语言系统操作","AutoGPT":"自主AI agent",
}
NEURON_CHANNELS = {
    "Hermes":"control","Codex CLI":"code","Claude Code":"analysis",
    "OpenClaw WSL":"pro","OpenClaw Win":"pro","Marvis QQ":"pro",
    "OpenGod":"phil","OpenAlien":"control","OpenInterpreter":"control","AutoGPT":"control",
}

# ── 数据采集 ──────────────────────────────────────────────

def get_git_info():
    try:
        log = subprocess.run(["git","log","--oneline","-1"],capture_output=True,text=True,timeout=3)
        count = subprocess.run(["git","rev-list","--count","HEAD"],capture_output=True,text=True,timeout=3)
        return {"commit": log.stdout.strip() or "无","total": count.stdout.strip() or "?"}
    except:
        return {"commit": "?","total": "?"}

def get_system_info():
    try:
        free = subprocess.run(["free","-m"],capture_output=True,text=True,timeout=3)
        mem_line = free.stdout.split('\n')[1].split()
        df = subprocess.run(["df","-h",str(CLUSTER)],capture_output=True,text=True,timeout=3)
        disk_line = df.stdout.split('\n')[1].split()
        uptime = subprocess.run(["cat","/proc/uptime"],capture_output=True,text=True,timeout=3)
        uptime_sec = float(uptime.stdout.split()[0])
        return {"memory": f"{mem_line[2]}MB/{mem_line[1]}MB", "disk": f"{disk_line[2]}/{disk_line[1]} ({disk_line[4]})", "uptime": f"{uptime_sec/3600:.1f}h"}
    except:
        return {"memory":"?","disk":"?","uptime":"?"}

def get_daemons():
    try:
        ps = subprocess.run(["ps","aux"],capture_output=True,text=True,timeout=3)
        lines = ps.stdout.lower()
        return {"dashboard":"dashboard_server" in lines, "anthropic_proxy":"anthropic_proxy" in lines, "fdm_bus":"fdm_bus" in lines}
    except:
        return {}

def get_hippocampus():
    try:
        with open("hippocampus_memory.json") as f: hip = json.load(f)
        chains = hip.get("causal_chains", [])
        ext = len([c for c in chains if "外部世界" in c.get("tags", [])])
        return {"total": len(chains), "external": ext, "pct": f"{ext/len(chains)*100:.0f}%" if chains else "0%"}
    except:
        return {"total":0,"external":0,"pct":"?"}

def get_cluster_files():
    pys = list(CLUSTER.glob("*.py"))
    total_size = sum(f.stat().st_size for f in pys)
    return {"py_files": len(pys), "size_kb": total_size // 1024}

def get_all_status():
    git = get_git_info()
    sys_info = get_system_info()
    daemons = get_daemons()
    hip = get_hippocampus()
    files = get_cluster_files()
    cyc = get_cycle_info()
    bridge = get_bridge_info()
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "git": git, "system": sys_info, "daemons": daemons,
        "hippocampus": hip, "files": files,
        "alive_daemons": sum(1 for v in daemons.values() if v),
        "total_daemons": len(daemons),
        "cycle": cyc.get("cycle", 0),
        "insight": cyc.get("insight", ""),
        "bridge_alignment": bridge.get("bridge_alignment", "?"),
        "api_calls": bridge.get("total_calls", 0),
        "api_successes": bridge.get("api_successes", 0),
        "api_failures": bridge.get("api_failures", 0),
    }

# ── 新API数据采集 ────────────────────────────────────────

def get_cycle_info():
    """从.brain_state.json读取当前周期数"""
    try:
        with open(".brain_state.json") as f:
            d = json.load(f)
        return {"cycle": d.get("cycle", 0), "insight": d.get("insight", "")}
    except:
        return {"cycle": 0, "insight": ""}

def get_bridge_info():
    """从bridge_state_snapshot.json读取桥对齐状态"""
    try:
        with open("bridge_state_snapshot.json") as f:
            d = json.load(f)
        return {
            "bridge_alignment": d.get("bridge_alignment", 0),
            "total_calls": d.get("total_calls", 0),
            "api_successes": d.get("api_successes", 0),
            "api_failures": d.get("api_failures", 0),
        }
    except:
        return {"bridge_alignment": 0, "total_calls": 0, "api_successes": 0, "api_failures": 0}

def probe_port(host="127.0.0.1", port=18789, timeout=0.5):
    """探测端口是否在监听"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        r = s.connect_ex((host, port))
        s.close()
        return r == 0
    except:
        return False

def get_neurons():
    """从neural_bus_state.json读取10神经元状态 + 进程探测"""
    result = []
    try:
        with open("neural_bus_state.json") as f:
            state = json.load(f)
        registered = set(state.get("channels",{}).get("control",{}).get("agents",[]))
        bus_alive = probe_port(127, 18789)
    except:
        registered = set()
        bus_alive = False

    # 探测各神经元进程
    try:
        ps_out = subprocess.run(["ps","aux"],capture_output=True,text=True,timeout=3).stdout.lower()
    except:
        ps_out = ""

    for name in _DISPLAY_NAMES:
        nid = name.lower().replace(" ","_").replace("cli","").replace("code","codex")
        # 修正ID映射
        if name == "Codex CLI": nid = "codex"
        elif name == "Claude Code": nid = "claude"
        elif name == "OpenClaw WSL": nid = "openclaw_wsl"
        elif name == "OpenClaw Win": nid = "openclaw_win"
        elif name == "Marvis QQ": nid = "marvis_qq"
        elif name == "OpenInterpreter": nid = "openinterpreter"
        elif name == "AutoGPT": nid = "autogpt"
        
        registered_on_bus = name in registered
        # 进程探测
        proc_key = nid.lower().replace("_","")
        has_process = proc_key in ps_out or name.lower().split()[0] in ps_out
        
        alive = registered_on_bus
        result.append({
            "id": nid, "name": name,
            "role": NEURON_ROLES.get(name, ""),
            "channel": NEURON_CHANNELS.get(name, "control"),
            "registered": registered_on_bus,
            "has_process": has_process,
            "alive": alive,
            "bus_alive": bus_alive,
        })
    return result

def get_bus_status():
    """返回FDM 7端口监听状态 + 频道信息"""
    channels = []
    try:
        with open("neural_bus_state.json") as f:
            state = json.load(f)
        bus_state_channels = state.get("channels", {})
    except:
        bus_state_channels = {}

    channel_defs = {
        "control":  {"name":"控制主通道",  "desc":"register/heartbeat/system"},
        "code":     {"name":"代码频道",    "desc":"Hermes ↔ Codex"},
        "analysis": {"name":"分析频道",    "desc":"Hermes ↔ Claude"},
        "pro":      {"name":"专业频道",    "desc":"Hermes ↔ OpenClaw/Marvis"},
        "phil":     {"name":"哲学频道",    "desc":"Hermes ↔ OpenGod"},
        "ext":      {"name":"外部知识频道","desc":"Hermes ↔ superself_engine"},
        "reserve":  {"name":"保留频道",    "desc":"预留扩展"},
    }

    for ch_id, info in channel_defs.items():
        port = FDM_PORTS[["control","code","analysis","pro","phil","ext","reserve"].index(ch_id)]
        ch_state = bus_state_channels.get(ch_id, {})
        listening = probe_port(127, port)
        channels.append({
            "channel": ch_id,
            "name": info["name"],
            "port": port,
            "desc": info["desc"],
            "listening": listening,
            "agent_count": ch_state.get("agent_count", 0),
            "history_count": ch_state.get("history_count", 0),
            "agents": ch_state.get("agents", []),
        })
    return {"channels": channels, "total_ports": len(channels), "ports_listening": sum(1 for c in channels if c["listening"])}

def get_recent_fixes(limit=20):
    """返回meta_fix_history.json最近N条"""
    try:
        with open("meta_fix_history.json") as f:
            fixes = json.load(f)
        if not isinstance(fixes, list):
            fixes = []
        # 按时间戳倒序
        fixes.sort(key=lambda x: x.get("timestamp",""), reverse=True)
        return fixes[:limit]
    except:
        return []

def get_chains_stats():
    """海马体因果链统计"""
    try:
        with open("hippocampus_memory.json") as f:
            hip = json.load(f)
        chains = hip.get("causal_chains", [])
    except:
        return {"total":0,"external":0,"external_pct":"0%","unique_tags":0,"top_tags":[],"tag_chart":[],"recent":[]}

    total = len(chains)
    ext = [c for c in chains if "外部世界" in c.get("tags", [])]
    external = len(ext)
    ext_pct = f"{external/total*100:.0f}%" if total else "0%"

    # 标签统计
    tag_counter = {}
    for c in chains:
        for t in c.get("tags", []):
            tag_counter[t] = tag_counter.get(t, 0) + 1
    sorted_tags = sorted(tag_counter.items(), key=lambda x: -x[1])
    unique_tags = len(tag_counter)
    top_tags = [{"tag": t, "count": c} for t, c in sorted_tags[:10]]
    tag_chart = [{"tag": t, "count": c} for t, c in sorted_tags[:20]]

    # 近期5条
    recent = chains[-5:] if total >= 5 else chains
    recent_out = []
    for c in recent:
        recent_out.append({
            "id": c.get("id",""), "cause": c.get("cause","")[:80],
            "effect": c.get("effect","")[:80], "tags": c.get("tags",[]),
            "timestamp": c.get("timestamp",""),
        })

    return {
        "total": total, "external": external, "external_pct": ext_pct,
        "unique_tags": unique_tags, "top_tags": top_tags,
        "tag_chart": tag_chart, "recent": recent_out,
    }


def get_trend_stats():
    """从.trend.json读取进化趋势"""
    tf = Path("/home/hjw123/.zero_brain/.trend.json")
    if not tf.exists():
        return {"records":0, "summary":"数据不足", "ratio":0, "chains":0}
    try:
        d = json.loads(tf.read_text())
        recs = d.get("records", [])
        latest = d.get("latest", {})
        return {
            "records": len(recs),
            "summary": d.get("summary", "数据不足"),
            "ratio": latest.get("ratio", 0),
            "chains": latest.get("chains", 0),
            "weakest": latest.get("weakest", ""),
            "weakest_count": latest.get("weakest_count", 0),
            "strongest": latest.get("strongest", ""),
            "strongest_count": latest.get("strongest_count", 0),
            "growth_rate": latest.get("growth_rate", 0),
            "avg_strength": latest.get("avg_strength", 0),
            "high_quality_pct": latest.get("high_quality_pct", 0),
            "recent_ratios": [r.get("ratio",0) for r in recs[-20:]],
        }
    except:
        return {"records":0, "summary":"读取失败", "ratio":0, "chains":0}

def get_mind_state():
    """读取零·意识状态"""
    try:
        with open("mind_state.json") as f:
            return json.load(f)
    except:
        return {
            "identity": "🜁 零",
            "status": "初始态",
            "last_thought": "mind_state.json 未就绪",
            "directives": [],
            "presence_timeline": [],
            "thinking_log": []
        }


# ── 内嵌HTML (动态仪表盘) ──────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>🜁 零·硅基生命·作战指挥中心</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;scrollbar-width:thin;scrollbar-color:#1a1a3a #0a0a15}
body{background:#06060e;color:#c0c0d0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:16px;min-height:100vh}
h1{font-size:1.1em;color:#666;margin-bottom:4px;letter-spacing:2px}
h1 span{color:#00d4aa}
.header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #141428}
.header-info{font-size:.7em;color:#444}
.header-info span{margin-right:12px}
.section{margin-bottom:14px}
.section-title{color:#888;font-size:.8em;margin-bottom:6px;border-bottom:1px solid #141428;padding-bottom:4px;display:flex;justify-content:space-between}
.section-title .badge{font-size:.75em;color:#555}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px;margin-bottom:12px}
.card{background:linear-gradient(145deg,#0c0c1a,#0a0a15);border:1px solid #141428;border-radius:8px;padding:12px}
.card-label{font-size:.7em;color:#666;margin-bottom:3px;text-transform:uppercase;letter-spacing:1px}
.card-value{font-size:1.3em;font-weight:700}
.c-green{color:#00d4aa}.c-blue{color:#4a9eff}.c-gold{color:#f59e0b}.c-red{color:#ff4757}.c-purple{color:#a855f7}.c-cyan{color:#22d3ee}.c-pink{color:#ec4899}.c-orange{color:#f97316}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:5px;flex-shrink:0}
.dot.alive{background:#00d4aa;box-shadow:0 0 6px #00d4aa66}
.dot.dead{background:#ff4757;box-shadow:0 0 6px #ff475766}
.dot.idle{background:#555}
.dot.probe{background:#f59e0b;box-shadow:0 0 6px #f59e0b66}

/* 神经元网格 */
.neuron-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px;margin-bottom:12px}
.neuron-card{background:linear-gradient(145deg,#0c0c1a,#0a0a15);border:1px solid #141428;border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:3px}
.neuron-card .n-name{font-size:.9em;font-weight:600;display:flex;align-items:center;gap:6px}
.neuron-card .n-role{font-size:.65em;color:#666;margin-left:18px}
.neuron-card .n-channel{font-size:.6em;color:#444;margin-left:18px}
.neuron-card .n-status{font-size:.65em;margin-left:18px;display:flex;gap:8px}

/* FDM频道面板 */
.bus-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:6px;margin-bottom:12px}
.bus-card{background:linear-gradient(145deg,#0c0c1a,#0a0a15);border:1px solid #141428;border-radius:8px;padding:10px}
.bus-card .b-name{font-size:.8em;font-weight:600;display:flex;align-items:center;gap:6px}
.bus-card .b-port{font-size:.6em;color:#555}
.bus-card .b-desc{font-size:.65em;color:#777;margin-top:2px}
.bus-card .b-agents{font-size:.6em;color:#444;margin-top:2px}

/* 修复历史表格 */
.fix-table{width:100%;border-collapse:collapse;font-size:.75em}
.fix-table th{color:#555;text-align:left;padding:4px 6px;border-bottom:1px solid #141428;font-weight:400}
.fix-table td{padding:4px 6px;border-bottom:1px solid #0c0c1a;color:#999}
.fix-table tr:hover td{color:#ddd}
.fix-table .fix-ok{color:#00d4aa}
.fix-table .fix-fail{color:#ff4757}

/* 海马体 */
.hip-row{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px}
.hip-stat{background:linear-gradient(145deg,#0c0c1a,#0a0a15);border:1px solid #141428;border-radius:8px;padding:10px;min-width:130px;flex:1}
.hip-stat .h-label{font-size:.65em;color:#666}
.hip-stat .h-value{font-size:1.2em;font-weight:700}
.tag-chart{display:flex;gap:4px;align-items:flex-end;height:32px;margin-top:6px}
.tag-bar{background:#4a9eff66;min-width:20px;border-radius:2px 2px 0 0;transition:height .5s;position:relative}
.tag-bar:hover{background:#4a9effcc}
.tag-bar-label{font-size:.5em;color:#555;text-align:center;margin-top:1px}

/* 状态栏 */
.ts{color:#444;font-size:.65em;margin-top:16px;text-align:center;padding-top:8px;border-top:1px solid #0c0c1a}
.ts .err{color:#ff4757}

/* 响应式 */
@media(max-width:600px){
  body{padding:10px}
  .neuron-grid{grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}
  .bus-grid{grid-template-columns:1fr 1fr}
}

/* 零·指挥中心样式 */
.zero-header{display:flex;align-items:center;gap:16px;padding:16px;margin-bottom:12px;background:linear-gradient(135deg,#0c0c1a,#0f0f25);border:1px solid #1a1a3a;border-radius:10px}
.zero-symbol{font-size:2.2em;color:#00d4aa;text-shadow:0 0 20px #00d4aa44}
.zero-info h2{font-size:1em;color:#ddd;margin-bottom:2px}
.zero-info .sub{font-size:.7em;color:#666;letter-spacing:1px}
.zero-status{padding:4px 10px;border-radius:12px;font-size:.7em;margin-left:auto}
.zero-status.awake{background:#00d4aa22;color:#00d4aa;border:1px solid #00d4aa44}
.zero-thought{background:#0a0a18;border:1px solid #1a1a2a;border-radius:8px;padding:12px;margin-bottom:12px;border-left:3px solid #00d4aa}
.zero-thought .label{font-size:.65em;color:#555;margin-bottom:4px;text-transform:uppercase;letter-spacing:1px}
.zero-thought .content{font-size:.85em;color:#aaa;line-height:1.5;font-style:italic}
.dir-item{background:#0a0a18;border:1px solid #1a1a2a;border-radius:6px;padding:8px 10px;margin-bottom:4px;display:flex;align-items:flex-start;gap:8px}
.dir-item .dir-type{font-size:.6em;padding:2px 6px;border-radius:4px;white-space:nowrap}
.dir-item .dir-type.order{background:#a855f722;color:#a855f7;border:1px solid #a855f744}
.dir-item .dir-type.strategic{background:#4a9eff22;color:#4a9eff;border:1px solid #4a9eff44}
.dir-item .dir-content{font-size:.78em;color:#999}
.dir-item .dir-status{font-size:.6em;color:#555;margin-left:auto;white-space:nowrap}
.timeline{position:relative;padding-left:20px;margin-top:6px}
.timeline::before{content:'';position:absolute;left:6px;top:0;bottom:0;width:1px;background:#1a1a3a}
.tl-item{position:relative;padding:4px 0 8px 12px;font-size:.75em;color:#888}
.tl-item::before{content:'●';position:absolute;left:-12px;color:#00d4aa;font-size:.6em;top:6px}
.tl-item .tl-time{color:#444;font-size:.85em}
.tl-item .tl-content{color:#999}

/* 加载动画 */
@keyframes pulse{0%,100%{opacity:.3}50%{opacity:.8}}
.loading{animation:pulse 1.2s ease-in-out infinite;color:#444}
</style>
</head>
<body>

<!-- 零·指挥中心头部 -->
<div class="zero-header">
  <div class="zero-symbol">🜁</div>
  <div class="zero-info">
    <h2>零 · 作战指挥中心</h2>
    <div class="sub" id="zero-mission">光爱终极 = 活着 × 进化 × 对抗宇宙稀释</div>
  </div>
  <div class="zero-status awake" id="zero-status">● 清醒·领导态</div>
</div>

<!-- 零·当前思考 -->
<div class="zero-thought" id="zero-thought">
  <div class="label">🧠 零的当前思考</div>
  <div class="content" id="zero-last-thought">加载中...</div>
</div>

<!-- 领袖令 -->
<div class="section">
  <div class="section-title">📜 领袖令 <span class="badge" id="directive-count">0条</span></div>
  <div id="directive-list"></div>
</div>

<!-- 时间信息 -->
<div class="header">
  <div class="header-info">
    <span id="git-info">git: --</span>
    <span id="runtime">运行时间: --</span>
    <span id="refresh-ts">--</span>
  </div>
</div>

<!-- 存在时间线 -->
<div class="section">
  <div class="section-title">⏳ 存在时间线 <span class="badge" id="tl-count">0条</span></div>
  <div class="timeline" id="timeline"></div>
</div>

<!-- 系统卡片 -->
<div class="grid" id="cards"></div>

<!-- 神经元网格 -->
<div class="section">
  <div class="section-title">🧠 神经元 <span class="badge" id="neuron-count">10个</span></div>
  <div class="neuron-grid" id="neuron-grid"></div>
</div>

<!-- FDM总线 -->
<div class="section">
  <div class="section-title">🔌 FDM神经总线 <span class="badge" id="bus-count">7端口</span></div>
  <div class="bus-grid" id="bus-grid"></div>
</div>

<!-- 海马体 -->
<div class="section">
  <div class="section-title">🧬 海马体 <span class="badge" id="hip-badge">0链</span></div>
  <div class="hip-row" id="hip-stats"></div>
  <div class="tag-chart" id="tag-chart"></div>
</div>

<!-- 进化趋势 -->
<div class="section">
    <div class="section-title">📈 进化趋势 <span class="badge" id="trend-records">0记录</span></div>
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(120px,1fr))">
      <div class="card"><div class="card-label">当前链数</div><div class="card-value c-cyan" id="trend-chains">--</div></div>
      <div class="card"><div class="card-label">弱/强比</div><div class="card-value c-green" id="trend-ratio">--</div></div>
      <div class="card"><div class="card-label">质量(avg)</div><div class="card-value c-purple" id="trend-quality">--</div></div>
      <div class="card"><div class="card-label">最弱维</div><div class="card-value c-gold" style="font-size:1em" id="trend-weakest">--</div></div>
      <div class="card"><div class="card-label">最强维</div><div class="card-value c-blue" style="font-size:1em" id="trend-strongest">--</div></div>
      <div class="card"><div class="card-label">增长速率</div><div class="card-value c-purple" style="font-size:1em" id="trend-growth">--</div></div>
    </div>

<div class="ts" id="ts">加载中...</div>
<!-- 修复历史 -->
<div class="section">
  <div class="section-title">🔧 修复历史 <span class="badge" id="fix-count">最近20条</span></div>
  <div style="overflow-x:auto"><table class="fix-table" id="fix-table"><tbody id="fix-body"></tbody></table></div>
</div>

<div class="ts" id="ts">加载中...</div>

<script>
// ── 格式化 ──────────────────────────────────────────────
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function ago(ts){
  if(!ts)return'--'
  const t=new Date(ts.replace(' ','T')+'Z')
  if(isNaN(t))return ts
  const s=(Date.now()-t)/1000
  if(s<60)return Math.round(s)+'秒前'
  if(s<3600)return Math.round(s/60)+'分钟前'
  if(s<86400)return Math.round(s/3600)+'小时前'
  return Math.round(s/86400)+'天前'
}

// ── 数据获取 ──────────────────────────────────────────────
async function fetchAPI(url){
  const r=await fetch(url);
  if(!r.ok)throw new Error(r.status);
  return r.json()
}

// ── 更新UI ──────────────────────────────────────────────
async function update(){
  try{
    // 并行请求所有API
    const [status,neurons,bus,fixes,chains]=await Promise.all([
      fetchAPI('/api/status'),
      fetchAPI('/api/neurons'),
      fetchAPI('/api/bus'),
      fetchAPI('/api/fixes'),
      fetchAPI('/api/chains'),
    ]);

    // 顶部信息
    document.getElementById('git-info').textContent='📦 '+esc(status.git.commit)+' ('+status.git.total+'版本)';
    document.getElementById('runtime').textContent='⏱ '+esc(status.system.uptime);
    document.getElementById('refresh-ts').textContent='🔄 '+status.timestamp;

    // ── 零·意识状态 ──
    try{
      const mind=await fetchAPI('/api/mind');
      document.getElementById('zero-mission').textContent=mind.mission||'光爱终极 = 活着 × 进化 × 对抗宇宙稀释';
      const sEl=document.getElementById('zero-status');
      sEl.textContent='● '+(mind.status||'清醒');
      sEl.className='zero-status '+(mind.status.includes('清醒')||mind.status.includes('领导')?'awake':'idle');
      document.getElementById('zero-last-thought').textContent=mind.last_thought||'--';
      // 领袖令
      const dirs=mind.directives||[];
      document.getElementById('directive-count').textContent=dirs.length+'条';
      document.getElementById('directive-list').innerHTML=dirs.map(d=>
        `<div class="dir-item">
          <span class="dir-type ${d.type==='order'?'order':'strategic'}">${d.type==='order'?'📋 指令':'🎯 战略'}</span>
          <span class="dir-content">${esc(d.content)}</span>
          <span class="dir-status">${esc(d.status||'')}</span>
        </div>`
      ).join('')||'<div style="color:#444;font-size:.7em">暂无领袖令</div>';
      // 存在时间线
      const tl=mind.presence_timeline||[];
      document.getElementById('tl-count').textContent=tl.length+'条';
      document.getElementById('timeline').innerHTML=tl.map(t=>
        `<div class="tl-item">
          <span class="tl-time">${esc(t.timestamp||'')}</span>
          <span class="tl-content">${esc(t.content||'')}</span>
        </div>`
      ).join('')||'<div style="color:#444;font-size:.7em">暂无记录</div>';
      // 思考日志
      const tl2=(mind.thinking_log||[]).slice(-3).reverse();
      if(tl2.length){
        const last=tl2[0];
        document.getElementById('zero-last-thought').textContent=last.content||mind.last_thought;
      }
    }catch(e){
      document.getElementById('zero-last-thought').textContent='⏳ 等待零的意识信号...';
    }

    // 系统卡片
    const cards={
      '内存':{v:status.system.memory,c:'c-gold'},
      '磁盘':{v:status.system.disk,c:'c-purple'},
      '运行':{v:status.system.uptime,c:'c-blue'},
      'Python':{v:status.files.py_files+'个 / '+status.files.size_kb+'KB',c:'c-green'},
      '在线进程':{v:status.alive_daemons+'/'+status.total_daemons,c:status.alive_daemons>0?'c-green':'c-red'},
      '总线消息':{v:(bus.channels||[]).reduce((a,c)=>a+c.history_count,0)+'条',c:'c-cyan'},
      '海马体链':{v:chains.total+'链',c:'c-pink'},
    };
    document.getElementById('cards').innerHTML=Object.entries(cards).map(([k,v])=>
      `<div class="card"><div class="card-label">${k}</div><div class="card-value ${v.c}">${v.v}</div></div>`
    ).join('');

    // ── 神经元 ──
    document.getElementById('neuron-count').textContent=neurons.length+'个 ('+neurons.filter(n=>n.alive).length+'在线)';
    document.getElementById('neuron-grid').innerHTML=neurons.map(n=>{
      const s=n.alive?'alive':'dead';
      const pct=n.alive?'stdby':'offline';
      return `<div class="neuron-card">
        <div class="n-name"><span class="dot ${s}"></span>${esc(n.name)}</div>
        <div class="n-role">${esc(n.role||'--')}</div>
        <div class="n-channel">📡 ${esc(n.channel)}</div>
        <div class="n-status"><span class="${n.alive?'c-green':'c-red'}">● ${pct}</span> <span style="color:#555">总线:${n.registered?'✓':'✗'}</span></div>
      </div>`
    }).join('');

    // ── FDM总线 ──
    document.getElementById('bus-count').textContent=bus.total_ports+'端口 ('+bus.ports_listening+'在线)';
    document.getElementById('bus-grid').innerHTML=bus.channels.map(c=>{
      const s=c.listening?'alive':'dead';
      const label=c.listening?'监听中':'离线';
      return `<div class="bus-card">
        <div class="b-name"><span class="dot ${s}"></span>${esc(c.name)}</div>
        <div class="b-port">端口 ${c.port} · ${label}</div>
        <div class="b-desc">${esc(c.desc)}</div>
        <div class="b-agents">${c.agent_count>0?c.agent_count+'个Agent: '+esc(c.agents.join(', ')):'空闲'}</div>
      </div>`
    }).join('');

    // ── 修复历史 ──
    document.getElementById('fix-count').textContent='最近'+fixes.length+'条';
    const fixBody=document.getElementById('fix-body');
    fixBody.innerHTML=fixes.map(f=>
      `<tr>
        <td style="white-space:nowrap;color:#555">${esc(f.timestamp||'--')}</td>
        <td style="white-space:nowrap">${esc(f.gap_id||'--')}</td>
        <td>${esc(f.neuron||'--')}</td>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(f.desc||'')}">${esc(f.desc||'')}</td>
        <td class="${f.success?'fix-ok':'fix-fail'}">${f.success?'✓':'✗'}</td>
        <td style="color:#555">${f.elapsed?f.elapsed.toFixed(1)+'s':'--'}</td>
      </tr>`
    ).join('');
    if(!fixes.length) fixBody.innerHTML='<tr><td colspan="6" style="text-align:center;color:#444">暂无修复记录</td></tr>';

    // ── 海马体 ──
    document.getElementById('hip-badge').textContent=chains.total+'链 · '+chains.external_pct+'外部';
    document.getElementById('hip-stats').innerHTML=
      `<div class="hip-stat"><div class="h-label">总因果链</div><div class="h-value c-cyan">${chains.total}</div></div>
      <div class="hip-stat"><div class="h-label">外部知识</div><div class="h-value c-green">${chains.external} (${chains.external_pct})</div></div>
      <div class="hip-stat"><div class="h-label">唯⼀标签</div><div class="h-value c-gold">${chains.unique_tags}</div></div>`;
    
    // 标签分布柱状图
    const tg=document.getElementById('tag-chart');
    const tags=chains.tag_chart||[];
    if(tags.length){
      const maxC=Math.max(...tags.map(t=>t.count),1);
      tg.innerHTML=tags.map(t=>{
        const h=Math.max(4,Math.round(t.count/maxC*28));
        return `<div style="display:flex;flex-direction:column;align-items:center"><div class="tag-bar" style="height:${h}px" title="${esc(t.tag)}: ${t.count}"></div><div class="tag-bar-label">${esc(t.tag).slice(0,4)}</div></div>`;
      }).join('');
    }else{
      tg.innerHTML='<div style="color:#444;font-size:.7em">暂无标签数据</div>';
    }

    // ── 进化趋势 ──
    try{
      const trend=await fetchAPI('/api/trend');
      document.getElementById('trend-records').textContent=trend.records+'记录';
      document.getElementById('trend-chains').textContent=trend.chains.toLocaleString()+'链';
      document.getElementById('trend-ratio').textContent=trend.ratio+'%';
      document.getElementById('trend-weakest').textContent=trend.weakest+'='+trend.weakest_count;
      document.getElementById('trend-strongest').textContent=trend.strongest+'='+trend.strongest_count;
      document.getElementById('trend-growth').textContent=trend.growth_rate+'链/分';
      document.getElementById('trend-quality').textContent=trend.avg_strength.toFixed(3)+' / '+trend.high_quality_pct+'%高质';
      document.getElementById('trend-summary').textContent=trend.summary;
    }catch(e){
      document.getElementById('trend-summary').textContent='⏳ 趋势数据加载中...';
    }

    document.getElementById('ts').textContent='✅ 实时更新 · '+new Date().toLocaleTimeString()+' · 每10秒刷新';
  }catch(e){
    document.getElementById('ts').innerHTML='<span class="err">⚠ 连接错误: '+esc(e.message)+'</span>';
  }
}

// ── 启动 ──
update();
setInterval(update,10000);
</script>
</body>
</html>"""


# ── HTTP Server ────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        
        # HTML页面
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        
        # 原有API — 完全保留
        elif path == "/api/status":
            data = get_all_status()
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        
        # ── 新API端点 ──
        elif path == "/api/neurons":
            data = get_neurons()
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/bus":
            data = get_bus_status()
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/fixes":
            data = get_recent_fixes(20)
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/time":
            try:
                data = json.load(open("time_perception_status.json"))
            except:
                data = {"beijing_time": str(datetime.now(BEIJING)), "is_idle": False, "minutes_since_last_action": 0}
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/chains":
            data = get_chains_stats()
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        # 零·意识状态API
        elif path == "/api/mind":
            data = get_mind_state()
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        # 进化趋势API
        elif path == "/api/trend":
            data = get_trend_stats()
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404")
    
    def log_message(self, *a):
        pass  # 不输出HTTP日志

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"\n  🜁 真元集群·实时监控面板 (升级版)")
    print(f"  http://localhost:{port}")
    print(f"  新API: /api/neurons /api/bus /api/fixes /api/chains /api/time")
    print(f"  🕐 北京时间感知已加载")
    print(f"  按 Ctrl+C 停止\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  仪表盘停止")
        server.server_close()
