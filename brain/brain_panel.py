#!/usr/bin/env python3
"""脑核实时状态面板 — 零依赖"""
import os, json, subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(str(CLUSTER))

def readj(path, default=None):
    f = CLUSTER / path
    if not f.exists(): return default
    try: return json.loads(f.read_text("utf-8"))
    except: return default

def tail(path, n=20):
    f = CLUSTER / path
    if not f.exists(): return ""
    try:
        lines = f.read_text("utf-8", errors="replace").strip().split("\n")
        return "\n".join(lines[-n:])
    except: return ""

def get_status():
    goal = readj(".brain_goal.json", {})
    daemon_alive, daemon_pid, daemon_uptime = False, 0, ""
    try:
        r = subprocess.run(["pgrep", "-f", "^python3.*brain/daemon\\.py"],
                          capture_output=True, text=True, timeout=3)
        if r.stdout.strip():
            pid = r.stdout.strip().split("\n")[0]
            daemon_alive, daemon_pid = True, int(pid)
            r2 = subprocess.run(["ps", "-p", pid, "-o", "etime="],
                               capture_output=True, text=True, timeout=3)
            daemon_uptime = r2.stdout.strip()
    except: pass
    journal = []
    jf = CLUSTER / ".brain_journal.jsonl"
    if jf.exists():
        try:
            lines = jf.read_text("utf-8").strip().split("\n")
            if lines:
                last = json.loads(lines[-1])
                journal = [f"#{last.get('cycle','?')}", f"{last.get('total_chains','?')}链",
                          f"{last.get('dimensions','?')}维"]
        except: pass
    # meta_observer健康
    meta_health = {}
    mf = Path("/home/hjw123/.zero_brain/.meta_health.json")
    if mf.exists():
        try:
            mh = json.loads(mf.read_text("utf-8"))
            hist = mh.get("history", [])
            if hist:
                meta_health = hist[-1]
        except: pass
    return {
        "daemon": {"alive": daemon_alive, "pid": daemon_pid, "uptime": daemon_uptime},
        "goal": {"type": goal.get("goal_type","无"), "focus": goal.get("focus_dim",""),
                 "desc": goal.get("description","")},
        "journal": journal,
        "log_tail": tail(".brain_daemon.log", 5),
        "trend": read_trend(),
        "meta_health": meta_health,
    }

def read_trend():
    tf = Path("/home/hjw123/.zero_brain/.trend.json")
    if not tf.exists(): return {}
    try:
        raw = json.loads(tf.read_text("utf-8"))
        recs = raw.get("records", [])
        if len(recs) > 20:
            recs = recs[-20:]
        return {"records": recs, "summary": raw.get("summary","")}
    except: return {}

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>🜁 脑核面板</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#06060e;color:#c0c0d0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',monospace;padding:20px}
h1{color:#00d4aa;font-size:1.5em;margin-bottom:4px}
.sub{color:#606080;font-size:.85em;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin-bottom:16px}
.card{background:linear-gradient(145deg,#0c0c1a,#0a0a15);border:1px solid #141428;border-radius:10px;padding:16px}
.card h2{color:#7a7aa0;font-size:.75em;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.val{font-size:1.6em;font-weight:700;font-family:monospace}
.green{color:#00d4aa}.blue{color:#4a9eff}.gold{color:#f59e0b}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px}
.dot.alive{background:#00d4aa;box-shadow:0 0 6px #00d4aa}
.dot.dead{background:#ff4757}
.log-box{background:#080812;border:1px solid #141428;border-radius:8px;padding:12px;font-family:monospace;font-size:.82em;line-height:1.5;color:#808090;white-space:pre-wrap}
.goal-tag{display:inline-block;padding:2px 10px;border-radius:4px;font-size:.8em;margin-top:6px}
.goal-tag.explore{background:#1a2a1a;color:#4ae}
.goal-tag.deepen{background:#2a1a2a;color:#f59e0b}
.goal-tag.synthesize{background:#1a1a2a;color:#00d4aa}
.goal-tag.consolidate{background:#1a2a2a;color:#7a7aa0}
</style>
</head>
<body>
<h1>🜁 脑核实时状态</h1>
<div class="sub" id="sub">载入中...</div>
<div class="grid">
  <div class="card"><h2>守护进程</h2><div id="daemon"><span class="dot dead"></span>检查中</div></div>
  <div class="card"><h2>当前目标</h2><div id="goal">--</div></div>
  <div class="card"><h2>周期</h2><div id="cycle">--</div></div>
  <div class="card"><h2>因果链</h2><div id="ratio">--</div></div>
  <div class="card"><h2>元观察健康</h2><div id="meta-health">--</div></div>
</div>
<div class="card"><h2>最近日志</h2><div class="log-box" id="log">等待数据...</div></div>
<div class="card"><h2>趋势 (最近8记录)</h2><div class="log-box" id="trend-log">等待数据...</div></div>
<script>
setInterval(function(){
  fetch('/api/brain').then(function(r){return r.json()}).then(function(d){
    if(!d) return;
    var dm = d.daemon;
    document.getElementById('daemon').innerHTML = dm.alive
      ? '<span class="dot alive"></span><span class="val green">运行中</span><div style="color:#606080;margin-top:4px">PID '+dm.pid+' &middot; '+dm.uptime+'</div>'
      : '<span class="dot dead"></span><span class="val" style="color:#ff4757">离线</span>';
    var gl = d.goal;
    document.getElementById('goal').innerHTML = '<span class="goal-tag '+gl.type+'">'+gl.type+'</span><div style="margin-top:6px">'+gl.desc+'</div>';
    if(d.journal.length>=2){
      document.getElementById('cycle').innerHTML = '<span class="val blue">'+d.journal[0]+'</span>';
      document.getElementById('chains').innerHTML = '<span class="val gold">'+d.journal[1]+'</span>';
    }
    document.getElementById('log').textContent = d.log_tail || '(无日志)';
    document.getElementById('sub').textContent = new Date().toLocaleTimeString('zh-CN',{timeZone:'Asia/Shanghai'})+' &middot; 5秒刷新';
    if(d.trend && d.trend.records && d.trend.records.length>1){
      var recs = d.trend.records, last = recs[recs.length-1];
      var ratioEl = document.getElementById('ratio');
      if(ratioEl){
        var first = recs[0];
        var dc = last.chains - first.chains;
        var dr = (last.ratio - first.ratio).toFixed(1);
        ratioEl.innerHTML = '<span class="val gold">'+last.chains+'链</span>'+
          '<div style="color:#606080;font-size:.85em;margin-top:4px">'+last.ratio+'%比'+
          ' (Δ'+dc+'链 / '+dr+'%) 速率:'+last.growth_rate+'链/cycle</div>';
      }
      var trendLog = document.getElementById('trend-log');
      if(trendLog){
        var html = '';
        for(var i=Math.max(0,recs.length-8);i<recs.length;i++){
          var r = recs[i];
          if(!r) continue;
          html += r.ts_local+' 链='+r.chains+' 比='+r.ratio+'% 反馈='+r.feedback_count+'\n';
        }
        trendLog.textContent = html;
      }
    }
    if(d.meta_health){
      var mh = d.meta_health;
      var healthy = mh.healthy === true;
      var alerts = (mh.alerts || []).length;
      var trendSummary = mh.trend_summary || '';
      document.getElementById('meta-health').innerHTML =
        '<span class="dot '+(healthy?'alive':'dead')+'"></span>' +
        '<span class="val '+(healthy?'green':'')+'" style="'+(healthy?'':'color:#ff4757')+'">'+
        (healthy?'健康':'异常')+'</span>' +
        '<div style="color:#606080;font-size:.82em;margin-top:4px">'+
        '警报: '+alerts+' | '+trendSummary.substring(0,60)+'</div>';
    }
  }).catch(function(){});
}, 5000);
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        elif p == "/api/brain":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(get_status(), ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, *a): pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8081"))
    print("Panel http://0.0.0.0:" + str(port))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
