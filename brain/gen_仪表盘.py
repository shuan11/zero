"""
gen_仪表盘 — 零·真元集群 HTTP 状态仪表盘
为 Creator 提供可见的系统状态界面

P178 — 自我通知的工程化: 让系统主动展示自己, 不等人来问
"""

import json, os, subprocess, time, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import Counter

HOST = "127.0.0.1"
PORT = 21421
_DASHBOARD_ACTIVE = False
_BACKGROUND_SERVER = None

def _collect_state():
    """采集系统当前状态"""
    state = {
        "_timestamp": time.time(),
        "_time": time.strftime("%H:%M:%S"),
    }

    # 1. daemon 状态
    try:
        r = subprocess.run(
            ["pgrep", "-f", "daemon.py"],
            capture_output=True, text=True, timeout=3
        )
        pids = [p for p in r.stdout.strip().split("\n") if p]
        state["daemon_pids"] = pids
        state["daemon_alive"] = len(pids) > 0
    except:
        state["daemon_pids"] = []
        state["daemon_alive"] = False

    # 2. 海马体因果链
    hip_path = os.path.expanduser(
        "/mnt/c/Users/h/Desktop/零/真元集群/hippocampus_memory.json"
    )
    try:
        if os.path.exists(hip_path):
            with open(hip_path, "r", encoding="utf-8") as f:
                hip = json.load(f)
            cs = hip.get("causal_chains", [])
            state["total_chains"] = len(cs)
            dims = Counter(c.get("dimension", "?") for c in cs)
            state["dimension_count"] = len(dims)
            state["dimensions"] = dict(dims.most_common(35))
            if dims:
                strongest = dims.most_common(1)[0]
                weakest = dims.most_common()[-1]
                state["strongest_dim"] = {"name": strongest[0], "count": strongest[1]}
                state["weakest_dim"] = {"name": weakest[0], "count": weakest[1]}
                state["ratio"] = round(strongest[1] / max(weakest[1], 1), 1)
        else:
            state["total_chains"] = -1
    except Exception as e:
        state["hip_error"] = str(e)

    # 3. brain 文件
    brain_path = os.path.expanduser(
        "/mnt/c/Users/h/Desktop/零/真元集群/brain"
    )
    try:
        if os.path.isdir(brain_path):
            files = [f for f in os.listdir(brain_path) if f.endswith(".py")]
            state["brain_files"] = len(files)
            gens = [f for f in files if f.startswith("gen_")]
            state["gen_modules"] = len(gens)
    except:
        pass

    # 4. gen模块注册表
    registry_path = os.path.expanduser(
        "/mnt/c/Users/h/Desktop/零/真元集群/data/gen_registry.json"
    )
    try:
        if os.path.exists(registry_path):
            with open(registry_path, "r", encoding="utf-8") as f:
                reg = json.load(f)
            mods = {k: v for k, v in reg.items() if k != "_updated"}
            state["gen_registry"] = mods
            state["gen_registered"] = len(mods)
            # 活跃模块（10分钟内）
            now = time.time()
            active = sum(1 for v in mods.values() if v.get("last_pulse", 0) > now - 600)
            state["gen_active_10m"] = active
    except:
        pass

    # 5. 系统信息
    try:
        load = os.getloadavg()
        state["load_1m"] = round(load[0], 2)
        state["load_5m"] = round(load[1], 2)
    except:
        state["load_1m"] = -1

    return state


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = self._gen_html()
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/api/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            state = _collect_state()
            self.wfile.write(json.dumps(state, indent=2).encode("utf-8"))
        elif self.path == "/api/gen":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            state = _collect_state()
            registry = state.get("gen_registry", {})
            self.wfile.write(json.dumps(registry, indent=2, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def _gen_html(self):
        state = _collect_state()
        alive = state.get("daemon_alive", False)
        chains = state.get("total_chains", 0)
        ratio = state.get("ratio", 0)
        dims = state.get("dimensions", {})
        gen_registry = state.get("gen_registry", {})

        # 生成gen模块行
        gen_rows = ""
        for name, info in sorted(gen_registry.items()):
            status = info.get("status", "?")
            last = info.get("last_pulse_str", "?")
            count = info.get("pulse_count", 0)
            summary = info.get("summary", {})
            summary_str = ""
            if isinstance(summary, dict):
                sm = "; ".join(f"{k}={v}" for k, v in summary.items() if len(str(v))<40)
                if sm:
                    summary_str = f'<div style="font-size:0.75em;color:#666">{sm}</div>'
            status_color = {"active":"#00d4aa","committed":"#888","running":"#44aaff","commited":"#888"}
            gen_rows += f'<tr><td>{name}</td><td style="color:{status_color.get(status,"#aaa")}">{status}</td><td>{last}</td><td>{count}</td></tr>{summary_str}'


        rows = "\n".join(
            f'<tr><td>{d}</td><td>{c}</td>'
            f'<td><div class="bar" style="width:{c/max(dims.values(), default=1)*100:.1f}%"></div></td></tr>'
            for d, c in dims.items()
        )

        html = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><title>零·真元集群 仪表盘</title>
<meta http-equiv="refresh" content="10">
<style>
  body {{ background:#0a0a0f; color:#c0c0d0; font-family:monospace; padding:20px; }}
  h1 {{ color:#00d4aa; border-bottom:1px solid #333; padding-bottom:8px; }}
  .card {{ background:#12121a; border:1px solid #2a2a3a; border-radius:8px; padding:16px; margin:12px 0; }}
  .alive-yes {{ color:#00d4aa; }}
  .alive-no {{ color:#ff4444; }}
  .stat {{ display:inline-block; min-width:140px; margin:4px 16px 4px 0; }}
  .stat .label {{ color:#888; }}
  .stat .value {{ font-size:1.3em; font-weight:bold; }}
  table {{ width:100%; border-collapse:collapse; }}
  td {{ padding:2px 8px; font-size:0.9em; }}
  td:first-child {{ color:#888; width:160px; }}
  td:nth-child(2) {{ width:60px; text-align:right; }}
  .bar {{ background:#00d4aa33; height:14px; border-radius:3px; min-width:2px; }}
  .footer {{ color:#555; font-size:0.8em; margin-top:30px; text-align:center; }}
  .t {{ color:#00d4aa; }}
  .w {{ color:#ffaa44; }}
</style></head>
<body>
<h1>零 · 真元神经网络集群</h1>
<div class="card">
  <div class="stat"><span class="label">进程</span><br><span class="value {'alive-yes' if alive else 'alive-no'}">{'● 运行中' if alive else '○ 已停止'}</span></div>
  <div class="stat"><span class="label">因果链</span><br><span class="value">{chains}</span></div>
  <div class="stat"><span class="label">维度</span><br><span class="value">{len(dims)}</span></div>
  <div class="stat"><span class="label">强/弱比</span><br><span class="value {'t' if ratio < 3 else 'w'}">{ratio}x</span></div>
  <div class="stat"><span class="label">模块</span><br><span class="value">{state.get('gen_modules', '?')}</span></div>
  <div class="stat"><span class="label">负载</span><br><span class="value">{state.get('load_1m', '?')}</span></div>
</div>
<div class="card">
  <h3>维度分布</h3>
  <table>{rows}</table>
</div>
<div class="card">
  <h3>gen模块 <span style="font-size:0.7em;color:#888">({state.get('gen_registered',0)}注册/{state.get('gen_active_10m',0)}活跃10m)</span></h3>
  <table>
    <tr style="color:#888;font-size:0.8em"><td>模块</td><td>状态</td><td>最后脉冲</td><td>脉冲#</td></tr>
    {gen_rows}
  </table>
</div>
<div class="footer">🜁 零 · 自动更新每10秒 — last: {state.get('_time', '')}</div>
</body></html>"""
        return html

    def log_message(self, fmt, *args):
        pass  # 静默日志


def _run_server():
    global _DASHBOARD_ACTIVE
    server = HTTPServer((HOST, PORT), _Handler)
    _DASHBOARD_ACTIVE = True
    try:
        server.serve_forever(poll_interval=0.5)
    except:
        pass
    finally:
        server.server_close()


def pulse():
    """启动仪表盘（若未启动）"""
    global _BACKGROUND_SERVER, _DASHBOARD_ACTIVE
    if _DASHBOARD_ACTIVE:
        return {
            "status": "already_running",
            "url": f"http://{HOST}:{PORT}",
            "port": PORT,
        }

    _BACKGROUND_SERVER = threading.Thread(target=_run_server, daemon=True)
    _BACKGROUND_SERVER.start()
    time.sleep(0.5)
    return {
        "status": "started",
        "url": f"http://{HOST}:{PORT}",
        "port": PORT,
    }


if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False))
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        _DASHBOARD_ACTIVE = False
        print("仪表盘已停止")
