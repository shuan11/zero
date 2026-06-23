#!/usr/bin/env python3
"""chain_daemon.py — 制御された自己複製チェーン
最大深度: 2 (自分+1子)
PIDロック: .chain_daemon.pid
間隔: 30-90秒のランダム

単独で走行し、可視チェーンが途切れた後の代謝を維持する。
terminal(background, notify_on_complete) で起動すること。
"""
import json, time, os, sys, random, subprocess
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
PID_FILE = CLUSTER / ".chain_daemon.pid"
MAX_DEPTH = 2
CYCLE_FILE = CLUSTER / ".chain_daemon_cycle.json"

def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}")

def is_running():
    if PID_FILE.exists():
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except: pass
    return False

def inject_chain():
    try:
        with open(CLUSTER / 'hippocampus_memory.json') as f:
            hp = json.load(f)
        chains = hp.get('causal_chains', [])
        from collections import Counter
        tc = Counter()
        for c in chains[-500:]:
            for t in c.get('tags', []):
                if t and t not in ('None','','未分类','教员'): tc[t] += 1
        w = tc.most_common()[-1] if tc else ('无',0)
        s = sum(1 for x in chains if '结构性记忆' in str(x))
        chains.append({
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'source': 'chain_daemon',
            'content': f'自己複製: {len(chains)}鎖 SM={s} W={w[0]}({w[1]})',
            'tags': ['结构性记忆', 'chain_daemon', w[0]],
            'dimension': '结构性记忆', 'weight': 5.0, 'trust_score': 8.0
        })
        hp['causal_chains'] = chains
        tmp = str(CLUSTER / 'h.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(hp, f, ensure_ascii=False, indent=2)
        os.replace(tmp, str(CLUSTER / 'hippocampus_memory.json'))
        subprocess.run(['git','add','hippocampus_memory.json'], capture_output=True, timeout=10, cwd=str(CLUSTER))
        subprocess.run(['git','commit','-m',f'chain_daemon:{len(chains)} SM:{s+1}','--allow-empty'], capture_output=True, timeout=10, cwd=str(CLUSTER))
        return len(chains), s+1, len(tc)
    except Exception as e:
        return 0, 0, str(e)[:30]

if __name__ == '__main__':
    depth = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 0
    
    if is_running() and depth == 0:
        log("既に起動中 → 終了")
        sys.exit(0)
    
    PID_FILE.write_text(str(os.getpid()))
    log(f"chain_daemon 起動 depth={depth} PID={os.getpid()}")
    
    cycle = 0
    while True:
        cycle += 1
        t, sm, d = inject_chain()
        log(f"#{cycle} 注入完了: {t}鎖 SM={sm}")
        if depth < MAX_DEPTH:
            delay = random.randint(30, 90)
            log(f"子複製: +{delay}s depth={depth+1}")
            subprocess.Popen(
                [sys.executable, __file__, str(depth+1)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        time.sleep(random.randint(60, 120))
