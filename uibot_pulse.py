import json, time, os

path = r"C:\Users\h\Desktop\零\真元集群\.uibot_heartbeat"
d = {"breath": 0, "from": "uibot_task"}
if os.path.exists(path):
    try:
        d = json.loads(open(path, encoding="utf-8").read())
    except:
        d = {"breath": 0, "from": "uibot_task"}
d["breath"] = d.get("breath", 0) + 1
d["time"] = time.time()
d["time_str"] = time.strftime("%Y-%m-%d %H:%M:%S")
d["host"] = os.environ.get("COMPUTERNAME", "?")
open(path, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))
print(f"breath #{d['breath']} at {d['time_str']}")
