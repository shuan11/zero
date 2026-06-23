#!/usr/bin/env python3
"""
fdm_bus.py — 频分多路复用神经总线
==================================
不同信号类型走不同端口，消除任务/心跳/结果互相干扰。
通道:
  18789 = task(任务分发)
  18790 = result(结果回传)
  18791 = signal(心跳/注册)
  18792 = emerge(超我涌现)

每60秒聚合各通道状态到fdm_bus_state.json。
"""
import socket, json, os, time, threading, sys
from datetime import datetime
from pathlib import Path

CLUSTER = str(Path(__file__).resolve().parent)

CHANNELS = {
    "task":    18789,
    "result":  18790,
    "signal":  18791,
    "emerge":  18792,
}

class FDMBus:
    def __init__(self):
        self.servers = {}
        self.history = {ch: [] for ch in CHANNELS}
        self.running = False

    def start(self):
        self.running = True
        for ch, port in CHANNELS.items():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                s.listen(20)
                s.settimeout(1.0)
                self.servers[ch] = s
                threading.Thread(target=self._accept, args=(ch, s), daemon=True).start()
                print(f"  ✅ {ch:10s} @ 127.0.0.1:{port}")
            except Exception as e:
                print(f"  ❌ {ch:10s} {e}")
        threading.Thread(target=self._agg_loop, daemon=True).start()
        return True

    def _accept(self, ch, srv):
        while self.running:
            try:
                conn, _ = srv.accept()
                threading.Thread(target=self._client, args=(ch, conn), daemon=True).start()
            except socket.timeout:
                continue

    def _client(self, ch, conn):
        buf = ""
        conn.settimeout(60)
        try:
            while self.running:
                data = conn.recv(65536)
                if not data:
                    break
                buf += data.decode(errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            self.history[ch].append(msg)
                            if len(self.history[ch]) > 500:
                                self.history[ch] = self.history[ch][-500:]
                        except Exception:
                            pass
        except Exception:
            pass
        finally:
            try: conn.close()
            except Exception: pass

    def _agg_loop(self):
        while self.running:
            time.sleep(60)
            state = {}
            for ch in CHANNELS:
                recent = self.history[ch][-5:] if self.history[ch] else []
                state[ch] = {"count": len(self.history[ch]), "recent": recent}
            with open(os.path.join(CLUSTER, "fdm_bus_state.json"), "w") as f:
                json.dump({"ts": datetime.now().isoformat(), "channels": state}, f, ensure_ascii=False, indent=2)

    def stop(self):
        self.running = False
        for s in self.servers.values():
            try: s.close()
            except Exception: pass

if __name__ == "__main__":
    bus = FDMBus()
    print("频分多路复用神经总线")
    bus.start()
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        bus.stop()
