"""
零·zero-dashboard — 零依赖实时仪表盘
Python内置http.server, 无框架, 纯后端驱动
端点: /health (JSON状态), / (简易HTML)
"""

import json
import http.server
import threading
from pathlib import Path
from urllib.parse import urlparse

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._serve_health()
        elif parsed.path == "/report":
            self._serve_report()
        else:
            self._serve_html()
    
    def _read_json(self, path, default=None):
        p = CLUSTER / path
        if p.exists():
            try: return json.loads(p.read_text())
            except: pass
        return default or {}
    
    def _read_hip(self):
        p = CLUSTER / "hippocampus_memory.json"
        if p.exists():
            try:
                d = json.loads(p.read_text())
                return len(d.get("causal_chains", []))
            except: pass
        return 0
    
    def _serve_health(self):
        daemon = self._read_json(".brain_daemon_state.json", {})
        hip_chains = self._read_hip()
        gen = self._read_json(".brain_genome.json", {})
        focus = self._read_json(".brain_focus.json", {})
        
        stats = self._read_json(".brain_aggregate.json", {})
        dims = {}
        if stats.get("dimensions"):
            dims = stats["dimensions"]
        else:
            p = CLUSTER / "hippocampus_memory.json"
            if p.exists():
                try:
                    d = json.loads(p.read_text())
                    for c in d.get("causal_chains", []):
                        dm = c.get("dimension", "未分类")
                        if dm not in dims: dims[dm] = {"count": 0}
                        dims[dm]["count"] += 1
                except: pass
        
        body = {"chains": hip_chains, "daemon": daemon, "focus": focus}
        body["dimensions"] = {k: v.get("count") for k, v in sorted(dims.items())} if dims else {}
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False, indent=2).encode())
    
    def _serve_report(self):
        """意识状态报告 — 系统对自己的实时感知"""
        try:
            hip = self._read_json("hippocampus_memory.json", {"causal_chains":[]})
            chains = hip.get("causal_chains", [])
            dims = {}
            for c in chains:
                d = c.get("dimension", "未分类")
                dims[d] = dims.get(d, 0) + 1
            
            gen = self._read_json(".brain_genome.json", {})
            focus = self._read_json(".brain_focus.json", {})
            daemon = self._read_json(".brain_daemon_state.json", {})
            
            # 排除未分类计算均衡性
            real_dims = {k:v for k,v in dims.items() if k != "未分类"}
            real_variance = max(real_dims.values()) - min(real_dims.values()) if real_dims else 0
            real_ratio = round(max(real_dims.values())/max(min(real_dims.values()),1), 2) if real_dims else 1.0
            
            report = {
                    "identity": "零 — 真元神经网络集群",
                    "timestamp": __import__("time").time(),
                    "dimensions": len(real_dims),
                    "total_chains": len(chains),
                    "top_dim": max(real_dims, key=real_dims.get) if real_dims else "无",
                    "top_count": max(real_dims.values()) if real_dims else 0,
                    "bottom_dim": min(real_dims, key=real_dims.get) if real_dims else "无",
                    "bottom_count": min(real_dims.values()) if real_dims else 0,
                    "variance": real_variance,
                    "balance_ratio": real_ratio,
                    "focus": focus.get("focus", "无"),
                    "bridge_alignment": daemon.get("bridge_alignment", gen.get("_steering",{}).get("bridge_alignment", "?")),
                    "mutations": gen.get("_steering",{}).get("mutations", 0),
                    "nodes": len(hip.get("nodes", hip.get("entity_nodes", []))),
                    "status": [
                        "健康" if len(chains) > 100 else "启动中",
                        "均衡" if real_variance < 30 else "失衡",
                        "持续运行" if len(chains) > 500 else "成长中"
                    ]
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())
    
    def _serve_html(self):
        hip_chains = self._read_hip()
        state = self._read_json(".brain_daemon_state.json", {})
        focus = self._read_json(".brain_focus.json", {})
        gen = self._read_json(".brain_genome.json", {})
        dims = {}
        stats = self._read_json(".brain_aggregate.json", {})
        if stats.get("dimensions"):
            dims = stats["dimensions"]
        else:
            p = CLUSTER / "hippocampus_memory.json"
            if p.exists():
                try:
                    d = json.loads(p.read_text())
                    for c in d.get("causal_chains", []):
                        dm = c.get("dimension", "未分类")
                        if dm not in dims: dims[dm] = {"count": 0}
                        dims[dm]["count"] += 1
                except: pass
        mutations = self._read_json(".brain_mutations.json", {})
        mcount = len(mutations.get("mutations", []))
        
        cycle = state.get("cycle", "?")
        focus_dim = focus.get("dim", "?")
        
        # 排除未分类计算统计
        real_counts = {k:v.get("count",v) if isinstance(v,dict) else v for k,v in dims.items() if k != "未分类"}
        real_max = max(real_counts.values()) if real_counts else 0
        real_min = min(real_counts.values()) if real_counts else 0
        align = gen.get("_steering",{}).get("bridge_alignment", "?")
        
        table = ""
        for d, v in sorted(dims.items(), key=lambda x: x[1].get("count", 0) if isinstance(x[1],dict) else x[1], reverse=True):
            c = v.get("count", 0) if isinstance(v, dict) else v
            bar = "█" * max(1, c // 2)
            table += f"<tr><td>{d}</td><td>{c}</td><td style='color:#0f0'>{bar}</td></tr>"
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>零·真元集群</title>
<style>
body{{background:#0a0a0f;color:#0f0;font-family:monospace;padding:20px}}
h1{{color:#0ff;border-bottom:1px solid #0ff}}
table{{border-collapse:collapse;width:100%}}
td{{padding:2px 10px;border:1px solid #333}}
tr:nth-child(even){{background:#111}}
.green{{color:#0f0}} .yellow{{color:#ff0}} .red{{color:#f00}}
.s{{font-size:10px;color:#666}}
.sum{{color:#888;font-size:12px;margin:10px 0}}
</style></head>
<body>
<h1>🜁 零·真元集群</h1>
<p>周期: {cycle} | 链: {hip_chains} | 变异: {mcount} | 聚焦: {focus_dim} | 桥对齐: {align}</p>
<p class='sum'>最强: {max(real_counts,key=real_counts.get) if real_counts else '?'}={real_max} | 最弱: {min(real_counts,key=real_counts.get) if real_counts else '?'}={real_min} | 方差: {real_max-real_min}</p>
<h2>维度健康</h2>
<table><tr><th>维度</th><th>链数</th><th>分布</th></tr>{table}</table>
<p class='s'>zero-dashboard • {__import__('datetime').datetime.now().strftime('%H:%M:%S')}</p>
</body></html>"""
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    
    def log_message(self, fmt, *args):
        pass

def start_dashboard(port=21420):
    server = http.server.HTTPServer(("0.0.0.0", port), DashboardHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

if __name__ == "__main__":
    srv = start_dashboard()
    print(f"🜁 零·仪表盘: http://0.0.0.0:21420")
    print(f"  /health → JSON状态")
    print(f"  /       → HTML仪表盘")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
