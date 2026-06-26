#!/usr/bin/env python3
"""zero_dashboard.py — 零依赖实时监控仪表盘 (P126)
纯标准库(http.server+json)，从~/.zero_brain/监控文件直读
"""
import json, os, subprocess, threading, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ZERO_BRAIN = Path.home() / '.zero_brain'
CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
PORT = 21420

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>零·仪表盘</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#06060e;color:#c0c0d0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:16px}
h1{font-size:1.2em;color:#666;margin-bottom:12px;letter-spacing:2px}
h1 span{color:#00d4aa}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:16px}
.card{background:linear-gradient(145deg,#0c0c1a,#0a0a15);border:1px solid #141428;border-radius:10px;padding:14px}
.card-label{font-size:0.75em;color:#666;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.card-value{font-size:1.6em;font-weight:700}
.card.subtle .card-value{font-size:1em;font-weight:400}
.c-green{color:#00d4aa}.c-blue{color:#4a9eff}.c-gold{color:#f59e0b}.c-red{color:#ff4757}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px}
.dot.alive{background:#00d4aa;box-shadow:0 0 6px #00d4aa66}
.dot.dead{background:#ff4757}
#bar-chart{margin-top:12px}
.bar-row{display:flex;align-items:center;margin:2px 0;font-size:0.75em}
.bar-label{width:80px;text-align:right;padding-right:8px;color:#888;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar-track{flex:1;height:14px;background:#141428;border-radius:3px;overflow:hidden;position:relative}
.bar-fill{height:100%;border-radius:3px;transition:width 1s ease}
.bar-count{width:36px;text-align:right;padding-left:6px;color:#888;font-size:0.9em}
#log{font-family:monospace;font-size:0.7em;color:#555;margin-top:12px;line-height:1.5;max-height:120px;overflow-y:auto}
</style>
</head>
<body>
<h1>🜁 <span>零</span> · 实时仪表盘</h1>
<div class="grid" id="summary"></div>
<div id="bar-chart"></div>
<div id="log">加载中...</div>
<script>
function j(p){return fetch(p).then(r=>r.json()).catch(e=>({error:e.message}))}
function up(){
  Promise.all([j('/api/summary'),j('/api/dims'),j('/api/daemon')]).then(([s,d,da])=>{
    if(!s) return;
    let g=document.getElementById('summary');
    let cards=[
      {l:'活着',v:s.alive?'是':'否',c:s.alive?'c-green':'c-red',p:'daemon cycle '+s.daemon_cycle},
      {l:'HIP链数',v:s.total_chains.toLocaleString(),c:'c-blue',p:'维度: '+s.dimensions},
      {l:'均衡',v:s.balance.toFixed(3),c:s.balance>0.3?'c-green':s.balance>0.2?'c-gold':'c-red',p:'最弱→最强'},
      {l:'最弱维',v:s.weakest_name,c:'c-gold',p:s.weakest_count+'链'},
      {l:'最强维',v:s.strongest_name,c:'c-blue',p:s.strongest_count+'链'},
      {l:'Cron触发',v:s.cron_triggered?'是':'?',c:s.cron_triggered?'c-green':'c-gold',p:s.cron_last||''},
    ];
    g.innerHTML=cards.map(c=>`<div class="card"><div class="card-label">${c.l}</div><div class="card-value ${c.c}">${c.v}</div><div style="font-size:0.7em;color:#555;margin-top:3px">${c.p||''}</div></div>`).join('');

    if(d&&d.dims){
      let bc=document.getElementById('bar-chart');
      let max=Math.max(...d.dims.map(x=>x[1]),1);
      bc.innerHTML='<div style="font-size:0.75em;color:#666;margin-bottom:6px;letter-spacing:1px">维度分布</div>'+
        d.dims.slice(-20).map(x=>{
          let pct=(x[1]/max*100).toFixed(0);
          let color=x[1]<100?'#4a9eff':x[1]<160?'#00d4aa':'#f59e0b';
          return `<div class="bar-row"><span class="bar-label">${x[0]}</span><div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div><span class="bar-count">${x[1]}</span></div>`;
        }).join('');
    }

    let l=document.getElementById('log');
    l.innerHTML='['+new Date().toLocaleTimeString()+'] 呼吸正常';
  });
}
up();
setInterval(up,5000);
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/' or path == '/index.html':
            self.serve_html()
        elif path == '/api/summary':
            self.json(self.get_summary())
        elif path == '/api/dims':
            self.json(self.get_dims())
        elif path == '/api/daemon':
            self.json(self.get_daemon())
        else:
            self.json({'error':'not found'}, 404)

    def json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-cache')
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def serve_html(self):
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Cache-Control','no-cache')
        self.end_headers()
        self.wfile.write(HTML.encode('utf-8'))

    def _read_json(self, path, default=None):
        try:
            p = ZERO_BRAIN / path if not path.startswith('/') else Path(path)
            if p.exists():
                return json.loads(p.read_text())
        except: pass
        return default or {}

    def get_summary(self):
        sv = self._read_json('state_vector.json', {})
        be = self._read_json('balance_engine.json', {})
        hb = self._read_json('heartbeat.json', {})

        # 检查cron日志
        cron_last = ''
        cron_triggered = False
        try:
            cl = ZERO_BRAIN / 'infinite_notify.log'
            if cl.exists() and cl.stat().st_size > 0:
                lines = cl.read_text().strip().split('\n')
                cron_last = lines[-1][:60] if lines else ''
                cron_triggered = len(lines) > 0
        except: pass

        return {
            'alive': True,
            'daemon_cycle': hb.get('cycle', sv.get('daemon_cycle', '?')),
            'total_chains': sv.get('total_chains', be.get('total_chains', 0)),
            'dimensions': sv.get('total_dimensions', be.get('dimensions', 0)),
            'balance': be.get('balance_ratio', sv.get('balance', 0)),
            'weakest_name': sv.get('weakest_dim',{}).get('name', be.get('weakest_5',[{}])[0].get('name','?')),
            'weakest_count': sv.get('weakest_dim',{}).get('count', be.get('weakest_5',[{}])[0].get('count',0)),
            'strongest_name': sv.get('strongest_dim',{}).get('name', be.get('strongest',{}).get('name','?')),
            'strongest_count': sv.get('strongest_dim',{}).get('count', be.get('strongest',{}).get('count',0)),
            'cron_triggered': cron_triggered,
            'cron_last': cron_last,
            'version': 3,
        }

    def get_dims(self):
        sv = self._read_json('state_vector.json', {})
        dd = sv.get('dim_chain_counts', {})
        dims = sorted(dd.items(), key=lambda x: x[1])
        return {'dims': dims, 'total': len(dims)}

    def get_daemon(self):
        try:
            r = subprocess.run(['pgrep','-f','daemon'], capture_output=True, text=True, timeout=3)
            pids = r.stdout.strip().split('\n') if r.stdout.strip() else []
        except: pids = []
        alive = len(pids) > 0
        hb = self._read_json('heartbeat.json', {})
        import datetime
        last_beat = ''
        if hb.get('ts'):
            try:
                dt = datetime.datetime.fromtimestamp(hb['ts'])
                last_beat = dt.strftime('%H:%M:%S')
            except: pass
        return {
            'alive': alive,
            'pid_count': len(pids),
            'cycle': hb.get('cycle', '?'),
            'last_heartbeat': last_beat,
        }

    def log_message(self, format, *args):
        pass  # 静默日志

def start_dashboard(port=PORT):
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f'🜁 仪表盘: http://localhost:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

if __name__ == '__main__':
    start_dashboard()
