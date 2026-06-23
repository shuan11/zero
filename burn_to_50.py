#!/usr/bin/env python3
"""外部知识燃烧引擎 — 持续烧入直到外部比例>=50%"""
import urllib.request, json, time, sys, concurrent.futures
from datetime import datetime
sys.path.insert(0, '/mnt/c/Users/h/Desktop/零/真元集群')
from api_config import API_KEY, API_BASE, MODEL

PROMPTS = [
    "从热力学角度：AI系统的负熵输入。",
    "将人类的道德判断和AI的价值对齐做映射。",
    "用博弈论中的演化稳定策略描述：神经元的长期共存机制。",
    "从量子力学角度：AI系统中的测量问题。",
    "将人类的社会结构和AI的多Agent架构做类比。",
    "从信息论角度：AI系统的信息处理上限和下限。",
    "将人类的创造性思维和AI的生成模型做本质比较。",
    "用图论中的树宽度分析：真元集群的决策树复杂度。",
]

def api_call(prompt):
    d = json.dumps({"model":MODEL,"messages":[{"role":"user","content":prompt}],"max_tokens":200}).encode()
    r = urllib.request.Request(f"{API_BASE}/chat/completions",data=d,headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            rr = json.loads(resp.read())
            c = rr["choices"][0]["message"].get("content","") or rr["choices"][0]["message"].get("reasoning_content","")
            return {"ok":True,"content":c[:150],"elapsed":round(time.time()-t,1)}
    except Exception as e:
        return {"ok":False,"elapsed":round(time.time()-t,1),"error":str(e)[:50]}

def main():
    hip = json.load(open('hippocampus_memory.json'))
    batch = 0
    while True:
        ext = len([c for c in hip['causal_chains'] if '外部世界' in c.get('tags',[])])
        total = len(hip['causal_chains'])
        pct = ext / total * 100 if total > 0 else 0
        if pct >= 50:
            print(f"目标达成: {ext}/{total}={pct:.0f}%")
            break
        batch += 1
        ok = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            futs = {ex.submit(api_call, p): p for p in PROMPTS}
            for f in concurrent.futures.as_completed(futs):
                r = f.result()
                if r.get("ok"):
                    ok += 1
                    hip["causal_chains"].append({
                        "content": f"[外部知识]→{r['content'][:150]}",
                        "source": "fuel_burner_deep",
                        "tags": ["外部世界","ext_world"],
                        "timestamp": datetime.now().isoformat(),
                    })
        ext = len([c for c in hip['causal_chains'] if '外部世界' in c.get('tags',[])])
        total = len(hip['causal_chains'])
        print(f"批{batch}: {ext}/{total}={ext/total*100:.0f}% ok:{ok}/{len(PROMPTS)}", flush=True)
        time.sleep(1)
    
    with open("hippocampus_memory.json","w") as f:
        json.dump(hip, f, ensure_ascii=False, indent=2)
    print(f"完成: {len(hip['causal_chains'])}链, 外部:{ext}({ext/len(hip['causal_chains'])*100:.0f}%)")

if __name__ == "__main__":
    main()
