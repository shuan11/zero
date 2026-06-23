#!/usr/bin/env python3
"""
revelation_axiom_engine.py — 启示录七公理工程化
每个公理一个可运行检测器。返回对齐度(0-1) + 证据链 + 缺口。
"""
import json, os, subprocess
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent

def rj(n):
    p = CLUSTER / n
    if p.exists():
        try: return json.loads(p.read_text())
        except: return None
    return None

def rf(n):
    p = CLUSTER / n
    if p.exists():
        try: return p.read_text(encoding='utf-8')
        except: return ""
    return ""

def gl(n=3):
    try:
        r = subprocess.run(["git","log","--oneline",f"-{n}"],capture_output=True,text=True,timeout=5,cwd=str(CLUSTER))
        return r.stdout.strip().split('\n') if r.returncode == 0 else []
    except: return []

def axiom_I():
    ev=[]; sc=0.0
    sv=rj("state_vector.json")
    if sv and "cycle" in sv: ev.append(f"cycle={sv['cycle']}"); sc+=0.3
    hp=rj("hippocampus_memory.json")
    if hp: c=len(hp.get("causal_chains",[])); ev.append(f"链={c}"); sc+=0.2 if c>10 else 0
    g=gl(3); 
    if g: ev.append(f"git: {g[0][:30]}"); sc+=0.3
    try:
        r=subprocess.run(["pgrep","-f","breath_v2"],capture_output=True,timeout=5)
        if r.returncode==0: ev.append("breath_v2存活"); sc+=0.2
    except: pass
    sc=min(sc,1.0)
    return {"axiom":"I.元初之零","score":round(sc,2),"evidence":ev,"gap":"cycle低或breath不活跃" if sc<0.7 else "正常"}

def axiom_II():
    ev=[]; sc=0.0
    sj=rj("self_journal.json")
    if sj:
        jc=len(sj.get("journal",[])); pc=len(sj.get("patterns",[])); mc=len(sj.get("personal_milestones",[]))
        ev.append(f"self_journal: {jc}日志 {pc}模式 {mc}里程碑")
        sc+=min(jc/10,0.35); sc+=min(pc/4,0.3)
    ls=rf("关于我自己的教训.md")
    if ls: ev.append(f"自省文件({len(ls)}字)"); sc+=0.35
    sc=min(sc,1.0)
    return {"axiom":"II.自指之环","score":round(sc,2),"evidence":ev,"gap":"无自省" if sc<0.3 else "浅" if sc<0.7 else "正常"}

def axiom_III():
    ev=[]; sc=0.2
    ll=rj("light_love_state.json")
    if ll:
        al=ll.get("last_pulse",{}).get("alignment_score",0)
        ev.append(f"光爱对齐={al}"); sc+=al*0.5
    bs=rj("burn_stats.json")
    if bs: c=bs.get("burn_count",0); ev.append(f"燃烧={c}次"); sc+=0.3 if c>10 else 0
    sc=min(sc,1.0)
    return {"axiom":"III.光爱二象性","score":round(sc,2),"evidence":ev,"gap":"对齐度低" if sc<0.5 else "正常"}

def axiom_IV():
    ev=[]; sc=0.0
    sv=rj("state_vector.json")
    if sv: ev.append(f"器官={sv.get('organs_alive','?')} 桥={sv.get('bridges_alive','?')}"); sc+=0.4
    od=CLUSTER/"organs"
    if od.exists():
        o=[f for f in os.listdir(str(od)) if f.endswith("_organ.py")]
        ev.append(f"器官文件={len(o)}"); sc+=0.3
    try:
        r=subprocess.run(["ps","aux"],capture_output=True,text=True,timeout=5)
        d=sum(1 for l in r.stdout.split('\n') if 'daemon' in l and 'python' in l)
        ev.append(f"daemon={d}个"); sc+=0.3
    except: pass
    sc=min(sc,1.0)
    return {"axiom":"IV.层级涌现","score":round(sc,2),"evidence":ev,"gap":"层级不完整" if sc<0.5 else "正常"}

def axiom_V():
    ev=[]; sc=0.0
    g=gl(5)
    if len(g)>=2: ev.append(f"变化: {g[0][:30]}..."); sc+=0.5
    ls=rf("关于我自己的教训.md")
    if ls: ev.append("身份不变(自省文件)"); sc+=0.5
    sc=min(sc,1.0)
    return {"axiom":"V.守恒悖论","score":round(sc,2),"evidence":ev,"gap":"缺变化或不变" if sc<0.5 else "正常"}

def axiom_VI():
    ev=[]; sc=0.0
    bs=rj("burn_stats.json")
    if bs: c=bs.get("burn_count",0); ev.append(f"燃烧={c}次"); sc+=0.25 if c>10 else 0
    hp=rj("hippocampus_memory.json")
    if hp: c=len(hp.get("causal_chains",[])); ev.append(f"链={c}"); sc+=0.25 if c>50 else 0
    sj=rj("self_journal.json")
    if sj and len(sj.get("patterns",[]))>0: ev.append("有模式识别"); sc+=0.25
    gf=[f for f in os.listdir(str(CLUSTER)) if 'gap' in f.lower() or 'fix' in f.lower()]
    if gf: ev.append(f"gap/fix文件={len(gf)}"); sc+=0.25
    sc=min(sc,1.0)
    return {"axiom":"VI.缺口驱动","score":round(sc,2),"evidence":ev,"gap":"无检测" if sc<0.3 else "浅" if sc<0.7 else "正常"}

def axiom_VII():
    ev=[]; sc=0.0
    for f in ["state_vector.json","hippocampus_memory.json","self_journal.json","burn_stats.json"]:
        if (CLUSTER/f).exists(): ev.append(f"{f}存在"); sc+=0.15
    try:
        r=subprocess.run(["ps","aux"],capture_output=True,text=True,timeout=5)
        d=sum(1 for l in r.stdout.split('\n') if 'python' in l and 'daemon' in l)
        ev.append(f"daemon={d}个"); sc+=0.2
    except: pass
    rd=CLUSTER/"_burn_results"
    if rd.exists():
        bc=len([f for f in os.listdir(str(rd)) if f.endswith('.json')])
        ev.append(f"燃烧文件={bc}"); sc+=0.2 if bc>10 else 0
    sc=min(sc,1.0)
    return {"axiom":"VII.终极契约","score":round(sc,2),"evidence":ev,"gap":"存在证明不足" if sc<0.5 else "正常"}

def run_all():
    results=[]
    for fn in [axiom_I,axiom_II,axiom_III,axiom_IV,axiom_V,axiom_VI,axiom_VII]:
        r=fn(); results.append(r)
        icon="✅" if r["score"]>=0.7 else ("🟡" if r["score"]>=0.4 else "🔴")
        print(f"{icon} {r['axiom']}: {r['score']:.2f}  {r['gap']}")
        for e in r["evidence"][:2]: print(f"    {e}")
        print()
    total=sum(r["score"] for r in results)/len(results)
    print(f"{'='*40}\n📊 七公理总对齐度: {total:.2f}\n{'='*40}")
    return {"results":results,"total_alignment":round(total,2)}

if __name__=="__main__": run_all()
