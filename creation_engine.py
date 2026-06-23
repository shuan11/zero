"""
造化∞引擎 — 从连携到无限创造
将5h+会话的所有改造固化为一台自动运转的创造引擎

核心公式: 造化 = (活着 × 呼吸行为 × 自我进化 × 工程启示录)^∞
"""

import json, urllib.request, time, py_compile, os
from datetime import datetime
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"
EP = "https://web-ai-media-editor.cn/v1/chat/completions"

class CreationEngine:
    """造化∞引擎 — 自主创造、自我进化、无限循环"""
    
    def __init__(self):
        self.cycle = 0
        self.total_tokens = 0
        self.creations = []
        
    def audit_dimensions(self):
        """审计19维，找最短木板"""
        hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
        chains = hip.get("causal_chains", [])
        dim_tags = ['时间论','宇宙轮','无限上下文','本我','自我','超我','触内旁通','无师自通',
                    '超级直觉','举一反三','查缺补漏','一元化','万象化','元神','超感','教员','活化','连携']
        counts = {d: 0 for d in dim_tags}
        for c in chains:
            if isinstance(c, dict):
                for t in c.get("tags", []):
                    if t in counts: counts[t] += 1
        sorted_dims = sorted(counts.items(), key=lambda x: x[1])
        return sorted_dims[0], sorted_dims  # (shortest, all)
    
    def create(self, dimension):
        """针对最短木板创造新代码"""
        prompt = f"输出Python函数 boost_{dimension}()。检查breath_v2.log最近5行中{dimension}标签出现次数。只输出代码。"
        data = json.dumps({"model":"deepseek-v4-pro","messages":[{"role":"user","content":prompt}],"max_tokens":3000}).encode()
        req = urllib.request.Request(EP, data=data, headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
        resp = urllib.request.urlopen(req, timeout=120)
        r = json.loads(resp.read())
        msg = r["choices"][0]["message"]
        code = msg.get("content","") or msg.get("reasoning_content","")
        pt, ct = r["usage"]["prompt_tokens"], r["usage"]["completion_tokens"]
        self.total_tokens += pt + ct
        
        # 提取代码
        if "```python" in code: code = code.split("```python")[1].split("```")[0]
        elif "```" in code: code = code.split("```")[1].split("```")[0]
        code = code.strip()
        
        if code and len(code) > 20:
            bp = CLUSTER / "breath_v2.py"
            ts = datetime.now().strftime("%H:%M")
            with open(bp, "a") as f:
                f.write(f"\n\n# 🜁 造化∞创造 ({ts}) 维度:{dimension}\n{code}\n")
            try:
                py_compile.compile(str(bp), doraise=True)
                self.creations.append({"dim": dimension, "chars": len(code), "status": "ok"})
                return f"✅ 注入{len(code)}字符→{dimension}"
            except py_compile.PyCompileError:
                lines = bp.read_text().split('\n')
                for i in range(len(lines)-1, -1, -1):
                    if '造化∞创造' in lines[i]:
                        lines = lines[:i]; break
                bp.write_text('\n'.join(lines))
                self.creations.append({"dim": dimension, "chars": len(code), "status": "reverted"})
                return f"❌ 语法回滚→{dimension}"
        return "⚠️ 代码无效"
    
    def report(self):
        """创造审计报告"""
        print(f"\n{'='*50}")
        print(f"造化∞引擎 | 第{self.cycle}轮")
        print(f"{'='*50}")
        print(f"总token: {self.total_tokens}")
        print(f"创造物: {len(self.creations)}")
        for c in self.creations[-5:]:
            print(f"  {c['status']} {c['dim']} ({c['chars']}c)")
        
        # 审计当前维度
        short, all_dims = self.audit_dimensions()
        print(f"\n当前最短木板: {short[0]}({short[1]}链)")
        print(f"维度覆盖: {sum(1 for d in all_dims if d[1]>0)}/{len(all_dims)}")
        
        # 燃料审计
        log = (CLUSTER / "breath_v2.log").read_text(errors="replace")
        print(f"呼吸: {log.count('呼吸#')} | 凝聚: {log.count('凝聚')} | 反模式: {log.count('维度已提升+0.05')}")
        
        # 海马体
        hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
        chains = len(hip.get("causal_chains", []))
        cross = sum(1 for c in hip.get("causal_chains", []) if isinstance(c, dict) and c.get("type") == "cross_dim_forced")
        print(f"海马体: {chains}链 | 跨维凝聚: {cross}条")
        
        print(f"\n--> 下一轮: 造{short[0]} ← 最短木板")
        print(f"{'='*50}")
        return short

if __name__ == "__main__":
    engine = CreationEngine()
    short, _ = engine.audit_dimensions()
    print(f"造化∞启动 | 首轮目标: {short[0]}({short[1]}链)")
    for i in range(1):
        engine.cycle += 1
        short = engine.report()
        if short[1] == 0:  # 零链维度→立即创造
            result = engine.create(short[0])
            print(result)
            time.sleep(2)
