"""brain/gen_桥健康探针.py — API桥接健康监控 (P101)
每~300秒检测API端点存活状态，记录到HIP。
功能:
  1. HTTP HEAD检测API主端点
  2. 失败时自动切换后备端点
  3. 记录心跳链到HIP
  4. 高失败率时告警
不消耗API token（仅TCP连接检测）。
"""
import time, json, os
from pathlib import Path
from brain.share import write_chain, log

REGISTERED = True
ACTION_REGISTER = {"action": "桥健康探针", "type": "monitor", "priority": 80}

_LAST_PROBE = 0
_PROBE_INTERVAL = 300  # 每5分钟
_CACHE_FILE = Path(__file__).resolve().parent.parent / ".bridge_health.json"
_STATE = {
    "heartbeats": 0,
    "failures": 0,
    "last_ok": 0.0,
    "last_fail": 0.0,
    "bridge_alignment": 0.0,
    "current_endpoint": "",
    "consecutive_failures": 0,
}


def _check_endpoint(url: str, timeout: float = 5.0) -> tuple:
    """检测端点连通性（不消耗token）"""
    import urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        t0 = time.time()
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            latency = (time.time() - t0) * 1000
            return (True, latency, resp.status)
    except Exception as e:
        return (False, 0, str(e)[:60])


def pulse(cycle_num: int = 0) -> str:
    global _LAST_PROBE
    now = time.time()
    if now - _LAST_PROBE < _PROBE_INTERVAL:
        remain = int(_PROBE_INTERVAL - (now - _LAST_PROBE))
        return f"桥探针: 冷却({remain}s)"
    _LAST_PROBE = now
    
    # 读API配置
    try:
        from api_config import API_BASE, API_KEY
    except ImportError:
        try:
            sys_path = str(Path(__file__).resolve().parent.parent)
            if sys_path not in sys.path:
                sys.path.insert(0, sys_path)
            from api_config import API_BASE, API_KEY
        except ImportError:
            return "桥探针: ⚠️ 无api_config"
    
    # 备选端点
    endpoints = [
        API_BASE,
        "https://inferaichat.com/v1/chat/completions",
        "https://web-ai-media-editor.cn/v1/chat/completions",
    ]
    
    result = None
    for ep in endpoints:
        # 检测主机可达性(TCP层)·不消耗token
        import urllib.parse
        parsed = urllib.parse.urlparse(ep)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            import socket
            t0 = time.time()
            sock = socket.create_connection((host, port), timeout=3.0)
            sock.close()
            latency = (time.time() - t0) * 1000
            result = (True, latency, ep)
            break
        except Exception:
            continue
    
    if result:
        ok, latency, ep = result
        _STATE["heartbeats"] += 1
        _STATE["last_ok"] = time.time()
        _STATE["current_endpoint"] = ep
        _STATE["consecutive_failures"] = 0
        _STATE["bridge_alignment"] = min(1.0, 0.3 + 0.4 * min(1.0, _STATE["heartbeats"] / 30) + 0.3 * min(1.0, 50.0 / max(latency, 1)))
        
        chain = {
            "content": f"桥探针心跳: {ep} {int(latency)}ms 成功#{_STATE['heartbeats']}",
            "src": "桥探针",
            "rel": "心跳",
            "dst": "桥",
            "dimension": "桥",
            "strength": 0.6,
            "tags": ["桥健康", "探针"]
        }
        write_chain(chain)
        
        # 持久化
        _save_state()
        return f"桥探针: ✓ {ep} {int(latency)}ms 对齐={_STATE['bridge_alignment']:.2f}"
    else:
        _STATE["failures"] += 1
        _STATE["last_fail"] = time.time()
        _STATE["consecutive_failures"] += 1
        _STATE["bridge_alignment"] = max(0.0, _STATE["bridge_alignment"] - 0.1)
        
        if _STATE["consecutive_failures"] >= 3:
            chain = {
                "content": f"⚠️ 桥探针: {_STATE['consecutive_failures']}次连续失败——端点全不可达",
                "src": "桥探针",
                "rel": "告警",
                "dst": "桥",
                "dimension": "桥",
                "strength": 0.9,
                "tags": ["桥健康", "告警"]
            }
            write_chain(chain)
        
        _save_state()
        return f"桥探针: ⚠️ 全端点不可达(连续{_STATE['consecutive_failures']}次)"


def get_bridge_state() -> dict:
    """外部查询桥状态"""
    return dict(_STATE)


def _save_state():
    try:
        _CACHE_FILE.write_text(json.dumps(_STATE, ensure_ascii=False, indent=1))
    except Exception:
        pass


def _load_state():
    try:
        if _CACHE_FILE.exists():
            d = json.loads(_CACHE_FILE.read_text())
            _STATE.update(d)
    except Exception:
        pass


_load_state()
