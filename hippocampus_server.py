#!/usr/bin/env python3
"""
hippocampus_server.py — 海马体写入服务
========================================
单一进程持有海马体JSON文件，其他进程通过Unix socket发送写入请求。
彻底解决54个进程并发写入导致的JSON损坏问题。

运行：python3 hippocampus_server.py &
其他进程：echo '{"content":"...","tags":[...]}' | nc -U /tmp/hippocampus.sock
"""
import json, os, socket, sys, time, fcntl
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIP_FILE = CLUSTER / "hippocampus_memory.json"
LOCK_FILE = CLUSTER / "hippocampus.lock"
SOCKET_FILE = "/tmp/hippocampus.sock"
BJT = timezone(timedelta(hours=8))

def read_hip():
    with open(LOCK_FILE, 'w') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
        try:
            with open(HIP_FILE) as f:
                return json.load(f)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

def write_hip(hip):
    with open(LOCK_FILE, 'w') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            with open(HIP_FILE, 'w') as f:
                json.dump(hip, f, ensure_ascii=False, indent=2)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

def append_chain(chain_dict):
    \"\"\"追加一条链到海马体\"\"\"
    try:
        from safe_hip import write_chain_legacy, read
        write_chain_legacy(chain_dict)
        return {"ok": True, "total": len(read().get("causal_chains", []))}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}

def handle_request(data):
    """处理写入请求"""
    try:
        req = json.loads(data)
        action = req.get("action", "write")
        
        if action == "write":
            result = append_chain(req.get("chain", {}))
            return json.dumps(result)
        elif action == "bulk_write":
            chains = req.get("chains", [])
            results = []
            for ch in chains:
                results.append(append_chain(ch))
            ok = sum(1 for r in results if r.get("ok"))
            return json.dumps({"ok": True, "written": ok, "total": len(chains)})
        elif action == "stats":
            hip = read_hip()
            chains = hip.get("causal_chains", [])
            c = sum(1 for ch in chains if any("因果" in t for t in ch.get("tags", [])))
            return json.dumps({"ok": True, "total": len(chains), "causal": c})
        elif action == "repair":
            # 修复JSON
            try:
                hip = read_hip()
                return json.dumps({"ok": True, "total": len(hip.get("causal_chains", []))})
            except:
                return json.dumps({"ok": False, "error": "JSON损坏"})
        else:
            return json.dumps({"ok": False, "error": f"未知动作: {action}"})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)[:100]})

def main():
    # 删除旧socket
    if os.path.exists(SOCKET_FILE):
        os.unlink(SOCKET_FILE)
    
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_FILE)
    server.listen(5)
    os.chmod(SOCKET_FILE, 0o777)
    
    print(f"[{datetime.now(BJT).strftime('%H:%M:%S')}] 海马体服务启动 @ {SOCKET_FILE}")
    
    while True:
        try:
            conn, _ = server.accept()
            data = conn.recv(65536).decode('utf-8')
            if data:
                response = handle_request(data.strip())
                conn.send(response.encode('utf-8'))
            conn.close()
        except Exception as e:
            print(f"[!] {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
