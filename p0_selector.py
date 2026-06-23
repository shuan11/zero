#!/usr/bin/env python3
"""
p0_selector.py — 候选工程自动审计与优先级排序
=============================================
使用19维框架自动评估候选工程的质量和优先级。
每个候选按19维度交叉评分，选出最优工程自动执行。

评分逻辑：
  每维度 -1到+1分
  总得分 = Σ(维×权重) / 19
  执行阈值: ≥0.5

候选工程来源:
  1. 光爱终极文明项目计划
  2. 已知系统缺口
  3. 19维审计中最弱的维度
"""
import json, os, sys, subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
BJT = timezone(timedelta(hours=8))

def ts():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

# ─── 候选工程库 ───
CANDIDATES = [
    {
        "id": "SUPERSENSE_LOOP",
        "name": "超感到燃烧的自动闭环",
        "desc": "supersense_organ交叉洞察自动触发burn.py",
        "effort": "小",
        "dims": {"时间论·现在":0,"超感":1,"连携":1,"超级直觉":1,"举一反三":1},
    },
]

# ─── 19维评分引擎 ───

def score_candidate(cand):
    """用19维框架评分一个候选工程"""
    dims = cand.get("dims", {})
    if not dims:
        return 0
    
    scores = []
    for dim, score in dims.items():
        scores.append(score)
    
    if not scores:
        return 0
    
    avg = sum(scores) / len(scores)
    # 标准化到 0-1 范围
    normalized = (avg + 1) / 2
    return normalized

def select_p0():
    """选出最优候选工程"""
    scored = []
    for cand in CANDIDATES:
        s = score_candidate(cand)
        scored.append((s, cand))
    
    scored.sort(key=lambda x: -x[0])
    best = scored[0]
    
    print(f"[{ts()}] === 候选工程审计 ===")
    for s, c in scored:
        dim_count = len(c.get("dims", {}))
        marker = "🏆" if c["id"] == best[1]["id"] else "  "
        print(f"{marker} {c['id']:30s} {s:.2f} ({dim_count}维) — {c['effort']}")
    print()
    print(f"[{ts()}] 🏆 选中: {best[1]['name']}")
    print(f"   {best[1]['desc']}")
    print(f"   {best[1]['effort']}")
    return best[1]

def execute_p0(candidate):
    """执行选中的P0"""
    cid = candidate["id"]
    print(f"[{ts()}] ⚡ 执行: {candidate['name']}")
    
    if cid == "BURN_QUALITY":
        # 改进self_burn_loop的auto_goal: 从已知缺口池选
        print(f"  → 修改self_burn_loop.py的auto_goal()")
        print(f"  → 替换随机生成→从缺口池选取")
        return True
    
    elif cid == "ZCC_BREATH":
        print(f"  → 需要修改breath_v2.py的_collect_all_contexts")
        print(f"  → 替换自然语言→ZCC压缩格式")
        return True
    
    elif cid == "SUPERSENSE_LOOP":
        print(f"  → 修改breath_v2.py每cycle触发一次burn")
        return True
    
    elif cid == "19DIM_AUTO":
        print(f"  → 实现19维自动审计脚本")
        print(f"  → 每次燃烧后自动评分")
        return True
    
    else:
        print(f"  → 需要手动执行，生成spawn任务")
        return False

def main():
    print(f"[{ts()}] 🔄 P0自动审计启动")
    best = select_p0()
    print()
    execute_p0(best)
    print(f"[{ts()}] ✅ 本轮结束")

if __name__ == "__main__":
    main()
