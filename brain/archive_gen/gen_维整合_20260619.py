"""
gen_维整合_20260619 — 维度碎片化自动整合
当维度>35时，自动合并链数<30的相似维至相近强维
"""
import sys, json
sys.path.insert(0, "/mnt/c/Users/h/Desktop/零/真元集群")
from brain.share import write_chain, read_hip

def _run():
    """当作为模块被加载时执行的主逻辑"""
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    dims = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1

    if len(dims) <= 35:
        print(json.dumps({"status": "ok", "action": "none", "dims": len(dims), "reason": "未超阈值"}))
        return

    weak_dims = {d: n for d, n in sorted(dims.items(), key=lambda x: x[1]) if n < 30 and d not in ("未分类",)}
    written = 0
    for wd, wn in weak_dims.items():
        for sd, sn in sorted(dims.items(), key=lambda x: -x[1])[:3]:
            if sd != wd and sn > 100:
                write_chain({
                    "src": wd, "rel": "整合_20260619",
                    "dst": sd, "dimension": sd,
                    "strength": 0.5,
                    "content": "[整合] {} ({}链)指向{}——弱维纳入强维集群".format(wd, wn, sd)
                })
                written += 1

    print(json.dumps({"status": "ok", "action": "bridge_written", "count": written,
                      "weak_dims": list(weak_dims.keys())}))

if __name__ == "__main__":
    _run()
# 被daemon加载时: loader.py 的 exec_module 后自动发现 _run() 并调用
