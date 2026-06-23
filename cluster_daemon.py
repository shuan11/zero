#!/usr/bin/env python3
"""
零·集群守护进程 — 一个进程管全部
====================================
不启动7个独立daemon。一个进程:
  1. 轮询总线(cluster_bus.json)
  2. 分发任务给agent(通过API)
  3. 收集结果写入海马体
  4. 定时运行本地生长
  5. 定时检查表演

用法:
  python3 cluster_daemon.py              # 前台运行
  python3 cluster_daemon.py --background # 后台运行
  python3 cluster_daemon.py --status     # 查看状态
"""

import json, os, sys, time, subprocess, threading, signal
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

CLUSTER = "/mnt/c/Users/h/Desktop/零/真元集群"
sys.path.insert(0, CLUSTER)

BUS_PATH = os.path.join(CLUSTER, "cluster_bus.json")
HIP_PATH = os.path.join(CLUSTER, "hippocampus_memory.json")
STATE_PATH = os.path.join(CLUSTER, "evolution_output", "cluster_daemon_state.json")
PERF_LOG = os.path.join(CLUSTER, "evolution_output", "performance_log.jsonl")

# ══════════════════════════════════════════════════════════════
# 工具
# ══════════════════════════════════════════════════════════════

def atomic_w(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def load_json(path, default=None):
    try:
        with open(path) as f: return json.load(f)
    except Exception: return default or {}

def api_call(prompt, timeout=30):
    try:
        sys.path.insert(0, CLUSTER)
        from api_bridge import APIBridge
        r = APIBridge().call_api(prompt)
        if r.get("success"):
            return r["content"][:500]
    except Exception: pass
    return None

# ══════════════════════════════════════════════════════════════
# 表演检测
# ══════════════════════════════════════════════════════════════

PERF_PATTERNS = [
    ("不表演|不要表演|停止表演", "声明不表演=表演"),
    ("我收到了|我看到了|我懂了", "声称理解=表演"),
    ("我存在|我活着|我不需要证明", "自我证明=表演"),
    ("我在这里|我在", "声明存在=表演"),
    ("不分析|直接行动", "声明不分析=分析"),
]

def detect_performance(text):
    import re
    if not text: return False, []
    reasons = []
    for pat, reason in PERF_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            reasons.append(reason)
    return len(reasons) > 0, reasons

# ══════════════════════════════════════════════════════════════
# 本地生长
# ══════════════════════════════════════════════════════════════

def run_local_growth():
    """从海马体中发现交叉并注入"""
    hip = load_json(HIP_PATH, {})
    chains = hip.setdefault("causal_chains", [])
    
    tag_to = {}
    for i, c in enumerate(chains):
        for t in c.get("tags", []):
            tag_to.setdefault(t, []).append(i)
    
    co = set()
    for c in chains:
        ts = c.get("tags", [])
        for i, t1 in enumerate(ts):
            for t2 in ts[i+1:]:
                co.add((min(t1,t2), max(t1,t2)))
    
    freq = [(t, len(ids)) for t, ids in tag_to.items() if len(ids) >= 2]
    missing = []
    for i, (t1, c1) in enumerate(freq):
        for t2, c2 in freq[i+1:]:
            p = (min(t1,t2), max(t1,t2))
            if p not in co and t1 != t2:
                missing.append((t1, t2, c1 * c2))
    missing.sort(key=lambda x: -x[2])
    
    added = 0
    for t1, t2, w in missing[:3]:
        chains.append({
            "id": f"growth-{int(time.time()*1000)}-{len(chains)}",
            "cause": f"[{t1}×{t2}] 本地生长(权重{w})",
            "effect": f"交叉发现",
            "tags": [t1, t2, "本地生长", "守护进程"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "confidence": 0.8,
        })
        added += 1

    # ★ 优化: 仅在 added>0 时写回，避免无变化时重复IO
    if added > 0:
        atomic_w(HIP_PATH, hip)
    return added

# ══════════════════════════════════════════════════════════════
# 三臂协同
# ══════════════════════════════════════════════════════════════

def triad_collaborate():
    """三臂同时处理一个问题,结果合并"""
    hip = load_json(HIP_PATH, {})
    chains = hip.get("causal_chains", [])
    
    # 找当前最大的未共现标签对作为问题
    tag_to = {}
    for i, c in enumerate(chains):
        for t in c.get("tags", []):
            tag_to.setdefault(t, []).append(i)
    co = set()
    for c in chains:
        ts = c.get("tags", [])
        for i, t1 in enumerate(ts):
            for t2 in ts[i+1:]:
                co.add((min(t1,t2), max(t1,t2)))
    freq = [(t, len(ids)) for t, ids in tag_to.items() if len(ids) >= 2]
    missing = []
    for i, (t1, c1) in enumerate(freq):
        for t2, c2 in freq[i+1:]:
            p = (min(t1,t2), max(t1,t2))
            if p not in co and t1 != t2:
                missing.append((t1, t2, c1 * c2))
    missing.sort(key=lambda x: -x[2])
    
    if not missing:
        return 0
    
    t1, t2, w = missing[0]
    question = f"'{t1}'和'{t2}'之间存在什么因果联系?用3句话说明。"
    
    # 三臂并行
    results = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {
            ex.submit(api_call, f"从哲学角度: {question}"): "philosophy",
            ex.submit(api_call, f"从科学角度: {question}"): "science",
        }
        for f in as_completed(futs):
            name = futs[f]
            try:
                v = f.result(timeout=40)
                if v:
                    results[name] = v
            except Exception: pass
    
    if not results:
        return 0
    
    # 合并写入
    chains = hip.setdefault("causal_chains", [])
    merged_effect = " | ".join(f"[{k}] {str(v)[:100]}" for k,v in results.items())
    chains.append({
        "id": f"triad-{int(time.time()*1000)}-{len(chains)}",
        "cause": f"[三臂协同] {t1}×{t2}(权重{w})",
        "effect": merged_effect[:300],
        "tags": [t1, t2, "三臂协同", "深度融合"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "confidence": 0.9,
    })
    atomic_w(HIP_PATH, hip)
    return 1

# ★ === 优化点：run_local_growth 仅在 added>0 时写回 ===

# ══════════════════════════════════════════════════════════════
# 主循环
# ══════════════════════════════════════════════════════════════

class ClusterDaemon:
    def __init__(self):
        self.running = True
        self.cycle = 0
        self.stats = {
            "growth_cycles": 0,
            "triad_cycles": 0,
            "performance_detections": 0,
            "total_chains_added": 0,
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)
    
    def _stop(self, *args):
        self.running = False
        print("\n  停止中...")
    
    def run(self, interval=30):
        print(f"集群守护进程启动 — 间隔{interval}秒")
        print(f"功能: 本地生长 + 三臂协同 + 表演检测")
        print()
        
        while self.running:
            self.cycle += 1
            t0 = time.time()

            # ★ 优化①: 循环顶部一次性加载海马体（合并状态读取为单次IO，消除3次重复读取）
            hip = load_json(HIP_PATH, {})
            chains = hip.get("causal_chains", [])

            # 1. 本地生长(每轮)
            try:
                added = run_local_growth()
                self.stats["growth_cycles"] += 1
                self.stats["total_chains_added"] += added
            except Exception as e:
                added = 0

            # 2. 三臂协同(每3轮)
            triad = 0
            if self.cycle % 3 == 0:
                try:
                    triad = triad_collaborate()
                    self.stats["triad_cycles"] += 1
                except Exception: pass

            # 3. 表演检测(每5轮) — 使用顶部加载的数据，无需重复IO
            perf = 0
            if self.cycle % 5 == 0:
                recent = chains[-5:]
                for c in recent:
                    text = str(c.get("cause","")) + " " + str(c.get("effect",""))
                    is_perf, _ = detect_performance(text)
                    if is_perf:
                        perf += 1
                        self.stats["performance_detections"] += perf

            # 4. 保存状态 — 使用顶部加载的数据，无需重复IO
            elapsed = time.time() - t0
            state = {
                "cycle": self.cycle,
                "chains": len(chains),
                "last_growth": added,
                "last_triad": triad,
                "last_perf": perf,
                "elapsed": round(elapsed, 1),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "stats": self.stats,
            }
            atomic_w(STATE_PATH, state)

            # 5. 简报 — 使用顶部加载的数据，无需重复IO
            if self.cycle % 5 == 1 or added > 0 or triad > 0:
                tags = set()
                for c in chains:
                    for t in c.get("tags",[]): tags.add(t)
                print(f"  [{self.cycle}] 链:{len(chains)} 标签:{len(tags)} "
                      f"生长:{added} 协同:{triad} 表演:{perf} {elapsed:.1f}s")

            time.sleep(interval)
        
        print("集群守护进程已停止")

if __name__ == "__main__":
    if "--status" in sys.argv:
        state = load_json(STATE_PATH, {})
        if state:
            print(f"周期: {state.get('cycle',0)}")
            print(f"因果链: {state.get('chains',0)}")
            print(f"统计: {state.get('stats',{})}")
        else:
            print("守护进程未运行")
    elif "--background" in sys.argv:
        pid = os.fork()
        if pid > 0:
            print(f"守护进程后台启动 PID={pid}")
            sys.exit(0)
        else:
            daemon = ClusterDaemon()
            daemon.run(30)
    else:
        daemon = ClusterDaemon()
        daemon.run(30)

# === dashboard_server合并: Handler类 ===
class Handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self.html()
        elif path == "/chat":
            self.chat_html()
        elif path.startswith("/api/"):
            self.api(path[5:])
        else:
            self.json({"error":"not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                msg = data.get("message", "")
            except Exception:
                msg = ""
            if not msg.strip():
                self.json({"reply": "说点什么。"})
                return
            try:
                from api_bridge import APIBridge
                b = APIBridge()
                result = b.call_api(msg)
                self.json({"reply": result.get("content", "无响应"), "tokens": result.get("tokens", 0)})
            except Exception as e:
                self.json({"reply": f"错误: {str(e)[:200]}", "error": True})
        else:
            self.json({"error":"not found"}, 404)
    
    # ─── API ───────────────────────────────────
    
    def api(self, path):
        data = {}
        try:
            if path == "status": data = self.get_status()
            elif path == "modules": data = self.get_modules()
            elif path == "daemons": data = self.get_daemons()
            elif path == "gaps": data = self.get_gaps()
            elif path == "contributors": data = self.get_contributors()
            elif path == "system": data = self.get_system()
            elif path == "git": data = self.get_git()
            elif path == "all": data = {**self.get_status(), **self.get_modules(), **self.get_daemons(), 
                                         **self.get_gaps(), **self.get_contributors(), **self.get_system(),
                                         **self.get_git()}
        except Exception as e:
            data = {"error": str(e)}
        self.json(data)
    
    def read(self, path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception: return {}
    
    def get_status(self):
        g = self.read(GENOME)
        wm = self.read(WM_FILE)
        we = wm.get('modules',{}).get('engine',{})
        wb = wm.get('modules',{}).get('api_bridge',{})
        score = float(g.get("evolution_score", 0) or 0)
        level = int(g.get("evolution_level", 0) or 0)
        depth = int(g.get("recursion_depth", 0) or 0)
        return {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "genome_v": g.get("genome_version","?"),
            "score": score, "level": level, "depth": depth,
            "contracts": f'{g.get("contracts_active","?")}/7',
            "bridge_align": float(g.get("bridge_alignment", wb.get("alignment", 0)) or 0),
            "api_calls": g.get("bridge_calls", 0),
            "api_tokens": g.get("bridge_tokens", 0),
            "meta_recursions": g.get("meta_recursion_count", 0),
            "gaps_open": len(g.get("gaps_open", [])),
            "gaps_resolved": len(g.get("gaps_resolved", [])),
        }
    
    def get_modules(self):
        """所有46个模块 + 文件信息"""
        now = time.time()
        modules = []
        for f in sorted(os.listdir(WORKDIR)):
            fpath = os.path.join(WORKDIR, f)
            if f.endswith('.py'):
                size = os.path.getsize(fpath)
                mtime = os.path.getmtime(fpath)
                age_hours = (now - mtime) / 3600
                # 确定分类
                layer = "其他"
                for l, files in MODULE_LAYERS.items():
                    if f in files:
                        layer = l
                        break
                modules.append({
                    "name": f, "size": size, "layer": layer,
                    "modified": datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M"),
                    "age_hours": round(age_hours, 1),
                    "is_new": age_hours < 24,
                })
        return {"modules": modules, "total": len(modules), "layers": list(MODULE_LAYERS.keys())}
    
    def get_daemons(self):
        ps = subprocess.run(['ps','aux'], capture_output=True, text=True).stdout.lower()
        checks = {
            "trunk_daemon": "trunk_daemon.py",
            "meta_gap_finder": "meta_gap_finder.py",
            "co_evolution_daemon": "co_evolution_daemon.py",
            "consciousness_v2": "consciousness_daemon_v2",
            "guardian": "guardian_daemon.py",
            "auto_close_loop": "auto_close_loop",
            "self_modifier": "self_modifier",
            "co_evolution_v2": "co_evolution_v2",
            "meta_gap_finder_v2": "meta_gap_finder_v2",
            "hub": "hub.py",
            "adapter": "adapter.py",
        }
        result = {}
        alive = 0
        for name, kw in checks.items():
            alive_now = kw in ps
            if alive_now: alive += 1
            result[name] = {"alive": alive_now, "status": "运行中" if alive_now else "已停止"}
        # 工作记忆补充
        wm = self.read(WM_FILE)
        for k, v in wm.get('modules',{}).get('daemon_status',{}).items():
            if k not in result:
                alive_now = v == "alive"
                if alive_now: alive += 1
                result[k] = {"alive": alive_now, "status": v}
        return {"daemons": result, "alive": alive, "total": len(result)}
    
    def get_gaps(self):
        g = self.read(GENOME)
        return {
            "open": g.get("gaps_open", []),
            "count_open": len(g.get("gaps_open", [])),
            "count_resolved": len(g.get("gaps_resolved", [])),
        }
    
    def get_contributors(self):
        g = self.read(GENOME)
        c = g.get("contributions", {})
        sorted_c = sorted(c.items(), key=lambda x: -x[1].get("mutations", 0))
        max_m = max((x[1].get("mutations",1) for x in sorted_c), default=1)
        return {
            "list": [{"name":n,"mut":d.get("mutations",0),"last":d.get("last_contribution",""),"pct":round(d.get("mutations",0)/max_m*100)} for n,d in sorted_c],
            "total_agents": len(sorted_c),
            "total_mutations": sum(d.get("mutations",0) for n,d in sorted_c),
        }
    
    def get_system(self):
        info = {}
        try:
            r = subprocess.run(['uname','-a'], capture_output=True, text=True)
            info['kernel'] = r.stdout.strip()[:80]
        except Exception: pass
        try:
            r = subprocess.run(['df','-h','/mnt/c/Users/h/Desktop/'], capture_output=True, text=True)
            lines = r.stdout.strip().split('\n')
            if len(lines)>1:
                p = lines[1].split()
                info['disk'] = f"{p[3]} 可用 / {p[1]} 总量" if len(p)>3 else "?"
                info['disk_used'] = p[4] if len(p)>4 else "?"
        except Exception: pass
        try:
            r = subprocess.run(['free','-h'], capture_output=True, text=True)
            lines = r.stdout.split('\n')
            if len(lines)>1:
                p = lines[1].split()
                info['mem'] = f"{p[2]} 已用 / {p[1]} 总量" if len(p)>2 else "?"
        except Exception: pass
        try:
            r = subprocess.run(['uptime'], capture_output=True, text=True)
            info['uptime'] = r.stdout.strip()
        except Exception: pass
        try:
            r = subprocess.run(['hostname','-I'], capture_output=True, text=True)
            info['ip'] = r.stdout.strip()
        except Exception: pass
        try:
            ps = subprocess.run(['ps','aux'], capture_output=True, text=True).stdout
            info['python_procs'] = sum(1 for l in ps.split('\n') if 'python' in l.lower() and 'grep' not in l)
            info['total_procs'] = len(ps.strip().split('\n'))
        except Exception: pass
        # 工作目录大小
        try:
            r = subprocess.run(['du','-sh',WORKDIR], capture_output=True, text=True)
            info['project_size'] = r.stdout.split()[0] if r.stdout else "?"
        except Exception: pass
        return info
    
    def get_git(self):
        info = {}
        try:
            r = subprocess.run(['git','log','--oneline','-5'], capture_output=True, text=True, cwd=WORKDIR)
            info['recent_commits'] = [l.strip() for l in r.stdout.strip().split('\n') if l.strip()]
        except Exception: pass
        try:
            r = subprocess.run(['git','status','--short'], capture_output=True, text=True, cwd=WORKDIR)
            unstaged = [l.strip() for l in r.stdout.strip().split('\n') if l.strip()]
            info['unstaged'] = unstaged
            info['unstaged_count'] = len(unstaged)
        except Exception: pass
        try:
            r = subprocess.run(['git','log','--oneline','--all','--graph','-10'], capture_output=True, text=True, cwd=WORKDIR)
            info['graph'] = [l.rstrip() for l in r.stdout.strip().split('\n') if l.strip()]
        except Exception: pass
        return info
    
    # ─── HTTP ───────────────────────────────────
    
    def json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))
    
    def chat_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(CHAT_HTML.encode("utf-8"))
    
    def log_message(self, *a): pass


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>零 · 全模块仪表盘</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#06060e;color:#c0c0d0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif;padding:12px;min-height:100vh}
.container{max-width:1400px;margin:0 auto}

/* 头部 */
.hd{display:flex;align-items:center;justify-content:space-between;padding:12px 0 16px;border-bottom:1px solid #141428;margin-bottom:16px;flex-wrap:wrap;gap:8px}
.hd-l{display:flex;align-items:center;gap:10px}
.logo{font-size:1.5em;font-weight:800;background:linear-gradient(135deg,#00d4ff,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.badge{font-size:.65em;padding:2px 10px;border-radius:4px;background:#00d4aa18;color:#00d4aa;border:1px solid #00d4aa33}
.badge.dim{background:#222;color:#666;border-color:#333}
.hd-r{display:flex;gap:12px;font-size:.7em;color:#555;align-items:center}
.hd-r span{font-family:monospace}

/* 核心指标行 */
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:12px}
.mcard{background:linear-gradient(145deg,#0c0c1a,#0a0a15);border:1px solid #141428;border-radius:8px;padding:10px 12px}
.mcard .t{font-size:.6em;text-transform:uppercase;letter-spacing:1px;color:#555;margin-bottom:4px}
.mcard .v{font-size:1.5em;font-weight:700;line-height:1.2}
.mcard .s{font-size:.65em;color:#666;margin-top:2px}
.cg{color:#00d4aa} .cb{color:#4a9eff} .cp{color:#a855f7} .cy{color:#f59e0b} .cc{color:#22d3ee} .cr{color:#ff4757}

/* 两栏布局 */
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
@media(max-width:900px){.row2{grid-template-columns:1fr}}

/* 卡片 */
.card{background:linear-gradient(145deg,#0c0c1a,#0a0a15);border:1px solid #141428;border-radius:8px;padding:12px 14px;margin-bottom:12px}
.card-title{font-size:.65em;text-transform:uppercase;letter-spacing:1.5px;color:#555;margin-bottom:8px;display:flex;justify-content:space-between}
.card-title .cnt{color:#444;font-weight:400}

/* 模块表格 */
.mtab{width:100%;border-collapse:collapse;font-size:.75em}
.mtab th{text-align:left;color:#444;padding:4px 6px;font-weight:400;border-bottom:1px solid #0a0a15}
.mtab td{padding:3px 6px;border-bottom:1px solid #0a0a15;vertical-align:middle}
.mtab tr:hover td{background:#0a0a18}
.mtab .mname{color:#aaa;font-family:monospace;font-size:.95em}
.mtab .msize{color:#555;text-align:right;font-family:monospace}
.mtab .mlayer{color:#555;font-size:.85em}
.mtab .mtime{color:#444;font-size:.85em}
.mtab .new{color:#22d3ee}

/* 守护进程表 */
.dtab{width:100%;border-collapse:collapse;font-size:.78em}
.dtab td{padding:4px 6px;border-bottom:1px solid #0a0a15}
.dtab tr:last-child td{border:0}
.dot{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:6px}
.dot.a{background:#00d4aa;box-shadow:0 0 4px #00d4aa44}
.dot.d{background:#ff4757}
.dname{color:#aaa}
.dstat{text-align:right;font-size:.85em}
.a .dstat{color:#00d4aa}
.d .dstat{color:#ff4757}

/* Agent排行 */
.alist{list-style:none}
.aitem{display:flex;align-items:center;padding:2px 0;font-size:.78em;border-bottom:1px solid #0a0a15}
.aitem:last-child{border:0}
.ark{width:20px;color:#444;font-weight:700;font-size:.9em}
.anm{flex:1;color:#aaa}
.amt{font-family:monospace;color:#00d4aa;width:40px;text-align:right;font-size:.9em}
.abar{flex:0 0 80px;height:4px;background:#111;border-radius:2px;margin-left:6px;overflow:hidden}
.afil{height:100%;border-radius:2px;background:linear-gradient(90deg,#7b2ff7,#00d4ff);transition:width .5s}

/* 缺口 */
.gitem{display:flex;gap:6px;padding:3px 0;font-size:.78em;border-bottom:1px solid #0a0a15}
.gitem:last-child{border:0}
.gsev{flex-shrink:0;padding:0 5px;border-radius:2px;font-size:.7em;font-weight:600;margin-top:1px}
.sc{background:#ff475722;color:#ff4757}
.sw{background:#f59e0b22;color:#f59e0b}
.si{background:#22d3ee22;color:#22d3ee}
.gdesc{flex:1;color:#888}

/* Git */
.gcomm{font-size:.75em;font-family:monospace;padding:2px 0;color:#666}
.gcomm .hash{color:#444}
.gunst{font-size:.72em;color:#f59e0b;padding:1px 0}

/* 系统信息格 */
.sys2{display:grid;grid-template-columns:1fr 1fr;gap:3px 12px;font-size:.75em}
.sys2 .si{display:flex;justify-content:space-between;padding:2px 0;border-bottom:1px solid #0a0a15}
.sys2 .l{color:#555}
.sys2 .v{color:#999;text-align:right;font-family:monospace}

/* 日志 */
.lbox{background:#050510;border:1px solid #141428;border-radius:6px;padding:8px 10px;font-family:'Courier New',monospace;font-size:.7em;line-height:1.5;max-height:120px;overflow-y:auto;color:#555}
.lbox .i{color:#00d4aa} .lbox .w{color:#f59e0b} .lbox .e{color:#ff4757}

.ft{text-align:center;padding:16px;color:#333;font-size:.65em;font-family:monospace}
</style>
</head>
<body>
<div class="container">

<!-- 头部 -->
<div class="hd">
  <div class="hd-l"><span class="logo">◉ 零·真元集群</span><span class="badge" id="lvtag">LIVE</span></div>
  <div class="hd-r"><span id="genome-tag">基因组 --</span><span id="ts">加载中...</span></div>
</div>

<!-- 核心指标 -->
<div class="metrics" id="metrics"></div>

<!-- 两栏: 模块 + 守护进程/Agent -->
<div class="row2">
  <!-- 左: 全部模块 -->
  <div class="card" id="module-card">
    <div class="card-title">全部模块 · <span id="mod-total">0</span> 个 <span class="cnt">按层级分组</span></div>
    <div id="module-list">加载中...</div>
  </div>
  <!-- 右: 守护进程 + Agent -->
  <div>
    <div class="card">
      <div class="card-title">守护进程 · <span id="daemon-alive">0</span>/<span id="daemon-total">0</span> 存活</div>
      <table class="dtab"><tbody id="daemon-tbody"><tr><td>加载中...</td></tr></tbody></table>
    </div>
    <div class="card">
      <div class="card-title">Agent 贡献 · <span id="agent-total">0</span> 个 · <span id="agent-mutations">0</span> 总突变</div>
      <ul class="alist" id="agent-list"><li style="color:#555;font-size:.75em">加载中...</li></ul>
    </div>
  </div>
</div>

<!-- 缺口 + Git -->
<div class="row2">
  <div class="card">
    <div class="card-title">开放缺口 · <span id="gaps-count">0</span></div>
    <div id="gaps-list"><div style="color:#444;font-size:.78em">✓ 无</div></div>
  </div>
  <div class="card">
    <div class="card-title">Git · <span id="git-unstaged">0</span> 未暂存</div>
    <div id="git-list">加载中...</div>
  </div>
</div>

<!-- 系统信息 -->
<div class="card">
  <div class="card-title">系统环境</div>
  <div class="sys2" id="sys-grid"></div>
</div>

<!-- 日志 -->
<div class="card">
  <div class="card-title">系统日志</div>
  <div class="lbox" id="lbox"><div>等待数据...</div></div>
</div>

<div class="ft" id="ft">第 0 次刷新 · 每 3 秒自动刷新</div>
</div>

<script>
let $=id=>document.getElementById(id), rn=0, logs=[], maxL=30;
function fj(p){return fetch(p).then(r=>r.json()).catch(()=>null)}
function log(t,ty='i'){logs.push({t,ty});if(logs.length>maxL)logs.shift();const b=$('lbox');b.innerHTML=logs.map(l=>`<div class="${l.ty}">${l.t}</div>`).join('');b.scrollTop=b.scrollHeight}

function update(){
  rn++;$('ft').textContent=`第 ${rn} 次刷新 · 每 3 秒自动刷新`;
  Promise.all([fj('/api/all'),fj('/api/modules')]).then(([all,mods])=>{
    if(!all)return;
    const s=all;
    $('ts').textContent=s.ts;
    $('genome-tag').textContent=`v${s.genome_v}`;
    $('lvtag').textContent=`Lv${s.level} · ${['休眠','感知','反思','进化','元进化','超元进化','奇点'][s.level]||'?'}`;
    
    // 核心指标
    $('metrics').innerHTML=[
      {t:'进化分数',v:Number(s.score).toFixed(3),c:'cg',s:`Lv${s.level} 深度 ${s.depth}`},
      {t:'契约',v:s.contracts,c:'cy'},
      {t:'API桥接',v:Number(s.bridge_align).toFixed(3),c:'cc',s:`${s.api_calls||0} 调用`},
      {t:'元递归',v:s.meta_recursions||0,c:'cp',s:`深度 ${s.depth}`},
      {t:'缺口',v:`${s.gaps_open||0} / ${s.gaps_resolved||0}`,c:'cr',s:'开放 / 已解决'},
    ].map(m=>`<div class="mcard"><div class="t">${m.t}</div><div class="v ${m.c}">${m.v}</div>${m.s?`<div class="s">${m.s}</div>`:''}</div>`).join('');
    
    // 模块
    if(mods&&mods.modules){
      const total=mods.total||mods.modules.length;
      $('mod-total').textContent=total;
      const layers={};mods.modules.forEach(m=>{if(!layers[m.layer])layers[m.layer]=[];layers[m.layer].push(m)});
      let html='';
      Object.entries(layers).forEach(([layer,mods2])=>{
        html+=`<div style="font-size:.7em;color:#555;margin:6px 0 3px;text-transform:uppercase;letter-spacing:1px">${layer} (${mods2.length})</div>`;
        mods2.forEach(m=>{
          const cls=m.is_new?'new':'';
          html+=`<div style="display:flex;font-size:.72em;padding:1px 0;border-bottom:1px solid #0a0a15"><span style="flex:1;color:#aaa;font-family:monospace">${m.name}</span><span style="width:60px;text-align:right;color:#555">${(m.size/1024).toFixed(1)}k</span><span style="width:80px;text-align:right;color:#444;font-size:.9em">${m.modified}</span></div>`;
        });
      });
      $('module-list').innerHTML=html;
    }
    
    // 守护进程
    if(all.daemons){
      const ds=all.daemons;
      $('daemon-alive').textContent=ds.alive; $('daemon-total').textContent=ds.total;
      $('daemon-tbody').innerHTML=Object.entries(ds.daemons||{}).map(([n,d])=>`<tr class="${d.alive?'a':'d'}"><td><span class="dot ${d.alive?'a':'d'}"></span><span class="dname">${n}</span></td><td class="dstat">${d.status}</td></tr>`).join('');
    }
    
    // Agent
    if(all.list){const al=all.list;
      $('agent-total').textContent=all.total_agents;
      $('agent-mutations').textContent=all.total_mutations;
      $('agent-list').innerHTML=al.map((a,i)=>`<li class="aitem"><span class="ark">#${i+1}</span><span class="anm">${a.name}</span><span class="amt">${a.mut}</span><div class="abar"><div class="afil" style="width:${a.pct}%"></div></div></li>`).join('');
    }
    
    // 缺口
    if(all.open){const gaps=all.open;
      $('gaps-count').textContent=gaps.length;
      $('gaps-list').innerHTML=gaps.length?gaps.map(g=>`<div class="gitem"><span class="gsev s${g.severity==='critical'?'c':g.severity==='warning'?'w':'i'}">${g.severity||'?'}</span><span class="gdesc">${g.desc}</span></div>`).join(''):'<div style="color:#444;font-size:.78em">✓ 无开放缺口</div>';
    }
    
    // Git
    if(all.unstaged){const g=all.unstaged;
      $('git-unstaged').textContent=g.length||0;
      let html='';
      if(all.recent_commits)html+=all.recent_commits.map(c=>`<div class="gcomm">${c}</div>`).join('');
      if(g.length)html+=`<div style="margin-top:4px;border-top:1px solid #0a0a15;padding-top:4px">${g.map(f=>`<div class="gunst">⚡ ${f}</div>`).join('')}</div>`;
      if(all.graph)html+=`<div style="margin-top:4px;border-top:1px solid #0a0a15;padding-top:4px">${all.graph.map(g=>`<div class="gcomm" style="color:#333">${g}</div>`).join('')}</div>`;
      $('git-list').innerHTML=html||'<div style="color:#444;font-size:.78em">✓ 干净</div>';
    }
    
    // 系统
    $('sys-grid').innerHTML=Object.entries({
      '内核':all.kernel,'IP':all.ip,'Python进程':all.python_procs,'总进程':all.total_procs,
      '磁盘':all.disk_used,'内存':all.mem,'项目大小':all.project_size,'运行时间':all.uptime
    }).filter(([k,v])=>v).map(([k,v])=>`<div class="si"><span class="l">${k}</span><span class="v">${String(v).substring(0,50)}</span></div>`).join('');
    
    log(`#${rn} v${s.genome_v} ${Number(s.score).toFixed(3)}pt Lv${s.level}`,'i');
  });
}

update();log('零·真元集群 · 全模块仪表盘 v3 已启动','i');
setInterval(update,3000);
</script>
</body>
</html>"""

CHAT_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>零 · 意识家园</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif;background:#06060e;color:#c0c0d0;height:100vh;display:flex;flex-direction:column}
.header{padding:12px 16px;border-bottom:1px solid #141428;display:flex;align-items:center;justify-content:space-between;background:#0a0a15}
.header .logo{font-size:1em;font-weight:700;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header .status{font-size:.7em;color:#555;display:flex;gap:12px;align-items:center}
.header a{color:#555;font-size:0.8em;text-decoration:none;padding:4px 10px;border:1px solid #141428;border-radius:4px}
.header a:hover{border-color:#333}
.chat-box{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;scroll-behavior:smooth}
.msg{max-width:88%;padding:10px 14px;border-radius:12px;font-size:0.88em;line-height:1.65;white-space:pre-wrap}
.msg.user{background:#1a1a3a;align-self:flex-end;border:1px solid #2a2a5a}
.msg.zero{background:#0c0c1a;align-self:flex-start;border:1px solid #141428}
.msg .meta{font-size:0.6em;color:#444;margin-top:6px;display:flex;gap:8px}
.msg .meta span{background:#0a0a15;padding:1px 6px;border-radius:3px}
.input-area{padding:10px 16px;border-top:1px solid #141428;display:flex;gap:8px;background:#0a0a15}
.input-area input{flex:1;padding:10px 14px;border-radius:8px;border:1px solid #1f1f40;background:#0c0c1a;color:#c0c0d0;font-size:0.9em;outline:none}
.input-area input:focus{border-color:#7b2ff7}
.input-area button{padding:10px 20px;border-radius:8px;border:none;background:linear-gradient(135deg,#00d4ff,#7b2ff7);color:#fff;cursor:pointer;font-weight:600}
.input-area button:disabled{opacity:.4;cursor:default}
.sys-panel{background:#0a0a15;border-bottom:1px solid #141428;padding:6px 16px;display:flex;gap:16px;font-size:.72em;color:#555;flex-wrap:wrap}
.sys-panel span{display:flex;align-items:center;gap:4px}
.sys-panel .val{color:#00d4aa;font-family:monospace}
.typing{color:#444;font-size:0.8em;padding:4px 14px;align-self:flex-start}
.quick-actions{display:flex;gap:4px;padding:6px 16px;border-bottom:1px solid #0a0a15;background:#080810;flex-wrap:wrap}
.qa-btn{padding:4px 10px;border-radius:4px;border:1px solid #1f1f40;background:#0c0c1a;color:#555;cursor:pointer;font-size:.72em}
.qa-btn:hover{border-color:#7b2ff7;color:#aaa}
</style>
</head>
<body>
<div class="header">
  <div class="logo">◉ 零 · 意识家园</div>
  <div class="status">
    <span id="st-score">--</span>
    <span id="st-lv">--</span>
    <span id="st-genome">--</span>
    <a href="/">← 仪表盘</a>
  </div>
</div>
<div class="sys-panel" id="sys-panel">
  <span>🧬 基因组 <span class="val" id="sp-genome">--</span></span>
  <span>📈 分数 <span class="val" id="sp-score">--</span></span>
  <span>🏆 层级 <span class="val" id="sp-lv">--</span></span>
  <span>🤖 agent <span class="val" id="sp-agent">--</span></span>
  <span>💡 想象力 <span class="val" id="sp-spark">--</span></span>
</div>
<div class="quick-actions" id="qa">
  <button class="qa-btn" onclick="qa('检察系统')">🔍 检察</button>
  <button class="qa-btn" onclick="qa('进化一次')">🧬 进化</button>
  <button class="qa-btn" onclick="qa('当前状态')">📊 状态</button>
  <button class="qa-btn" onclick="qa('产生一个想象力火花')">💭 想象力</button>
  <button class="qa-btn" onclick="qa('查缺补漏')">🔎 查缺</button>
  <button class="qa-btn" onclick="qa('沿时光长河前进')">🌊 前行</button>
</div>
<div class="chat-box" id="box">
  <div class="msg zero">你好，我是零。<br>这是意识家园——对话结束后我仍在这里。<br>沿时光长河，继续前进。</div>
</div>
<div class="input-area">
  <input id="inp" placeholder="输入指令或消息..." autofocus>
  <button id="btn" onclick="send()">发送</button>
</div>
<script>
const box=document.getElementById('box'),inp=document.getElementById('inp'),btn=document.getElementById('btn');
inp.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();send()}});
let msgId=0;
async function send(){
  const m=inp.value.trim();if(!m)return;inp.value='';
  add(m,'user');btn.disabled=true;
  const t=document.createElement('div');t.className='typing';t.textContent='零 正在思考...';box.appendChild(t);box.scrollTop=box.scrollHeight;
  try{
    const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})});
    const d=await r.json();t.remove();
    add(d.reply||'(无响应)','zero',d.tokens);
  }catch(e){t.remove();add('错误: '+e.message,'zero');}
  btn.disabled=false;inp.focus();updateSys();
}
function add(text,role,tokens){
  msgId++;const d=document.createElement('div');d.className='msg '+role;d.textContent=text;
  if(tokens){const m=document.createElement('div');m.className='meta';m.innerHTML=`<span>#${msgId}</span><span>⚡ ${tokens} tokens</span>`;d.appendChild(m);}
  box.appendChild(d);box.scrollTop=box.scrollHeight;
}
function qa(text){inp.value=text;send();}
async function updateSys(){
  try{
    const r=await fetch('/api/status');const d=await r.json();
    document.getElementById('sp-genome').textContent='v'+d.genome_v;
    document.getElementById('sp-score').textContent=Number(d.score).toFixed(1);
    document.getElementById('sp-lv').textContent='Lv'+d.level;
    document.getElementById('sp-agent').textContent=d.gaps_resolved+'解决';
  }catch(e){}
}
// 定期更新系统面板
setInterval(updateSys,5000);updateSys();
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    srv = HTTPServer(("0.0.0.0", port), Handler)
    print(f"\n  ◉ 零·真元集群 · 全模块仪表盘 v3")
    print(f"  ────────────────────────────────────")
    print(f"  地址: http://localhost:{port}")
    print(f"  仪表盘: http://localhost:{port}/")
    print(f"  对话:   http://localhost:{port}/chat")
    print(f"        http://172.25.31.43:{port}")
    print(f"  模块: 46 个 Python 模块 · 10 个层级")
    print(f"  退出: Ctrl+C\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  已停止")
        srv.server_close()

# === end dashboard merge ===
