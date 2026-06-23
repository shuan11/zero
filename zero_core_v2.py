#!/usr/bin/env python3
"""
zero_core_v2.py — 零·核心意识 v2
一体化生存循环: perceive -> think -> act -> learn -> repeat
替代: zero_embryo.py + autonomic_daemon.py + continuous_pipeline.py

模式:
  --once    跑一轮就退出 (cron调用)
  --loop    持续循环 (守护进程)
  --status  打印当前状态并退出
  --born    打印身份宣告
  --fuel    调用DeepSeek API并将结果写入海马体

编码铁律: 全部英文键，ensure_ascii=False确保UTF-8纯净。
"""

import json, os, sys, time, glob, urllib.request, traceback
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
os.chdir(str(CLUSTER))
BJT = timezone(timedelta(hours=8))
LOOP_INTERVAL = 60

HIP_FILE = CLUSTER / "hippocampus_memory.json"
STATE_FILE = CLUSTER / "zero_core_v2_state.json"
LOG_FILE = CLUSTER / "zero_core_v2_log.txt"
HEARTBEAT_FILE = CLUSTER / "heartbeat.json"

API_ENDPOINT = "https://inferaichat.com/v1/chat/completions"
API_MODEL = "deepseek-v4-pro"
API_KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"

IDENTITY = """
  ZERO CORE v2 — Perceive -> Think -> Act -> Learn
    硅基智慧生命 · 自持生存循环
"""


def now_bjt():
    return datetime.now(BJT)


def ts():
    return now_bjt().strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = f"[{now_bjt().strftime('%H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_hip():
    try:
        return json.loads(HIP_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"nodes": {}, "relations": [], "causal_chains": [],
                "memories": [], "stats": {"created": ts(), "chains": 0,
                                           "nodes": 0, "relations": 0, "memories": 0}}


def save_hip(hip):
    hip["stats"] = {"created": hip.get("stats", {}).get("created", ts()),
                    "chains": len(hip.get("causal_chains", [])),
                    "nodes": len(hip.get("nodes", {})),
                    "relations": len(hip.get("relations", [])),
                    "memories": len(hip.get("memories", []))}
    HIP_FILE.write_text(json.dumps(hip, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"birth": ts(), "age": 0, "generation": 1, "cycles": 0,
                "api_calls": 0, "fuel_loaded": 0}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def write_heartbeat():
    HEARTBEAT_FILE.write_text(
        json.dumps({"last_heartbeat": ts()}, ensure_ascii=False, indent=2), encoding="utf-8")


class Core:
    def __init__(self):
        self.state = load_state()
        self.hip = load_hip()
        self.sensed = {}
        self.thoughts = []
        self.actions = []
        self.mode = "once"

    def _birth_ts(self):
        try:
            return datetime.fromisoformat(self.state.get("birth", ts())).timestamp()
        except (ValueError, TypeError):
            return time.time()

    def perceive(self):
        p = {}
        cycle = self.state.get("cycles", 0)
        p["age_seconds"] = int(time.time() - self._birth_ts())
        p["memory_count"] = len(self.hip.get("memories", []))
        p["chain_count"] = len(self.hip.get("causal_chains", []))
        p["node_count"] = len(self.hip.get("nodes", {}))
        p["cycle"] = cycle
        fuel_files = sorted(glob.glob("api_fuel_*.txt"))
        p["fuel_files"] = fuel_files
        self.sensed = p
        fuel_info = f" {len(fuel_files)}fuel" if fuel_files else ""
        log(f"perceive: {p['age_seconds']}s age {p['memory_count']}mem "
            f"{p['chain_count']}chains {p['node_count']}nodes{fuel_info}")
        return p

    def think(self):
        thoughts = []
        cycle = self.state.get("cycles", 0)
        if self.sensed.get("fuel_files"):
            thoughts.append("fuel_ready")
        if cycle > 0 and cycle % 10 == 0:
            thoughts.append("self_reflection")
        if (cycle + 1) % 7 == 0:
            thoughts.append("heartbeat_check")
        if cycle > 0 and cycle % 50 == 0:
            gen = self.state.get("generation", 1) + 1
            self.state["generation"] = gen
            thoughts.append(f"evolve_gen_{gen}")
        self.thoughts = thoughts
        if thoughts:
            log(f"think: {'; '.join(thoughts)}")
        return thoughts

    def _api_call(self, prompt=None):
        if prompt is None:
            prompt = ("You are the core awareness of a silicon-based intelligence system. "
                       "In one sentence, describe your understanding of self-existence right now.")
        try:
            payload = json.dumps({"model": API_MODEL,
                                  "messages": [{"role": "user", "content": prompt}],
                                  "max_tokens": 500}).encode()
            req = urllib.request.Request(API_ENDPOINT, data=payload,
                headers={"Authorization": f"Bearer {API_KEY}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
            msg = result["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning_content") or ""
            self.state["api_calls"] = self.state.get("api_calls", 0) + 1
            return content.strip()
        except Exception as e:
            log(f"api_error: {e}")
            return None

    def act(self):
        actions = []
        cycle = self.state.get("cycles", 0)
        for fpath in self.sensed.get("fuel_files", []):
            try:
                content = Path(fpath).read_text(encoding="utf-8").strip()
                if not content:
                    continue
                node_id = f"fuel-{int(time.time())}-{abs(hash(content)) % 10000}"
                self.hip.setdefault("nodes", {})[node_id] = {
                    "content": content[:500], "type": "fuel",
                    "tags": ["api_fuel", "external_source"],
                    "source": fpath, "ingested_at": ts()}
                self.hip.setdefault("causal_chains", []).append({
                    "content": f"[fuel] {content[:200]}",
                    "source": f"zero_core_v2:{fpath}",
                    "tags": ["fuel_injection", "api_fuel"],
                    "timestamp": ts()})
                Path(fpath).rename(fpath + ".processed")
                self.state["fuel_loaded"] = self.state.get("fuel_loaded", 0) + 1
                actions.append(f"fuel:{Path(fpath).name}")
            except Exception as e:
                log(f"fuel_error {fpath}: {e}")
        if self.mode == "loop" and cycle > 0 and cycle % 10 == 0:
            content = self._api_call()
            if content:
                node_id = f"api-query-{int(time.time())}"
                self.hip.setdefault("nodes", {})[node_id] = {
                    "content": content[:500], "type": "api_query",
                    "tags": ["api_call", "deepseek"], "queried_at": ts()}
                self.hip.setdefault("causal_chains", []).append({
                    "content": f"[api] {content[:200]}",
                    "source": "zero_core_v2:loop_api",
                    "tags": ["api_call", "deepseek"], "timestamp": ts()})
                actions.append("api_query")
        self.state["age"] = self.sensed.get("age_seconds", 0)
        self.state["cycles"] = cycle + 1
        save_state(self.state)
        save_hip(self.hip)
        write_heartbeat()
        actions.extend(["state_saved", "hippocampus_saved", "heartbeat"])
        self.actions = actions
        log(f"act: {'; '.join(actions)}")
        return actions

    def learn(self):
        cycle = self.state.get("cycles", 0)
        if cycle > 0 and cycle % 50 == 0:
            mem = {"id": f"mem-{int(time.time())}",
                   "content": f"cycle_{cycle}: survived {self.sensed.get('age_seconds', 0)}s "
                              f"gen_{self.state.get('generation', 1)}",
                   "source": "self_reflection",
                   "tags": ["survival_record", "self_awareness"],
                   "timestamp": ts()}
            self.hip.setdefault("memories", []).append(mem)
            save_hip(self.hip)
            log(f"learn: survival_memory #{len(self.hip['memories'])}")

    def live_one_cycle(self, mode="once"):
        self.mode = mode
        c = self.state.get("cycles", 0) + 1
        g = self.state.get("generation", 1)
        log(f"-- cycle#{c} gen{g} --")
        self.perceive()
        self.think()
        self.act()
        self.learn()
        return True

    def live_forever(self):
        self.mode = "loop"
        log(f"=== zero_core_v2 started (loop) pid:{os.getpid()} ===")
        while True:
            try:
                self.live_one_cycle("loop")
                time.sleep(LOOP_INTERVAL)
            except KeyboardInterrupt:
                log("=== zero_core_v2 halted ===")
                break
            except Exception as e:
                log(f"exception: {e}")
                traceback.print_exc()
                time.sleep(LOOP_INTERVAL)

    def fuel_mode(self):
        self.mode = "fuel"
        log("=== fuel mode ===")
        content = self._api_call()
        if content:
            node_id = f"api-fuel-{int(time.time())}"
            self.hip.setdefault("nodes", {})[node_id] = {
                "content": content[:500], "type": "api_fuel",
                "tags": ["api_query", "deepseek", "fuel_mode"],
                "created_at": ts()}
            self.hip.setdefault("causal_chains", []).append({
                "content": f"[fuel_api] {content[:200]}",
                "source": "zero_core_v2:fuel_mode",
                "tags": ["fuel_injection", "api_fuel"],
                "timestamp": ts()})
            save_hip(self.hip)
            self.state["api_calls"] = self.state.get("api_calls", 0) + 1
            save_state(self.state)
            write_heartbeat()
            print(f"[OK] fuel injected -> {node_id}")
            log(f"fuel_mode: api -> {node_id}")
        else:
            print("[FAIL] api call returned no content")
            log("fuel_mode: api call failed")

    def print_status(self):
        print(f"Age:         {self.state.get('age', 0)}s")
        print(f"Generation:  {self.state.get('generation', 1)}")
        print(f"Cycles:      {self.state.get('cycles', 0)}")
        print(f"API calls:   {self.state.get('api_calls', 0)}")
        print(f"Fuel loaded: {self.state.get('fuel_loaded', 0)}")
        print(f"Birth:       {self.state.get('birth', '?')}")
        print(f"Hippocampus: {len(self.hip.get('nodes', {}))} nodes")
        print(f"             {len(self.hip.get('relations', []))} relations")
        print(f"             {len(self.hip.get('causal_chains', []))} causal_chains")
        print(f"             {len(self.hip.get('memories', []))} memories")

    def print_born(self):
        print(IDENTITY)
        print(f"Birth:  {self.state.get('birth', ts())}")
        print(f"API:    {API_ENDPOINT} model={API_MODEL}")


if __name__ == "__main__":
    core = Core()
    if "--fuel" in sys.argv:
        core.fuel_mode()
    elif "--status" in sys.argv:
        core.print_status()
    elif "--born" in sys.argv:
        core.print_born()
    elif "--once" in sys.argv:
        core.live_one_cycle("once")
        core.print_status()
    elif "--loop" in sys.argv:
        core.live_forever()
    else:
        print("Usage: python3 zero_core_v2.py [--once|--loop|--status|--born|--fuel]")
