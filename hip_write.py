"""海马体写入客户端——所有文件统一使用此模块写入"""
import json, socket

SOCKET_FILE = "/tmp/hippocampus.sock"

def write(content, tags=None, source=None):
    """写入一条链到海马体"""
    from datetime import datetime, timezone, timedelta
    chain = {
        "content": content,
        "source": source or "hip_write_client",
        "tags": tags or [],
        "timestamp": datetime.now(timezone(timedelta(hours=8))).isoformat(),
    }
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(SOCKET_FILE)
        req = json.dumps({"action": "write", "chain": chain})
        sock.send(req.encode('utf-8'))
        resp = sock.recv(4096).decode('utf-8')
        sock.close()
        return json.loads(resp)
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}

def bulk_write(chains):
    """批量写入"""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect(SOCKET_FILE)
        req = json.dumps({"action": "bulk_write", "chains": chains})
        sock.send(req.encode('utf-8'))
        resp = sock.recv(4096).decode('utf-8')
        sock.close()
        return json.loads(resp)
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}

def get_stats():
    """获取统计"""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(SOCKET_FILE)
        sock.send(json.dumps({"action": "stats"}).encode('utf-8'))
        resp = sock.recv(4096).decode('utf-8')
        sock.close()
        return json.loads(resp)
    except:
        return {"ok": False}
