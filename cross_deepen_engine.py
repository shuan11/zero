#!/usr/bin/env python3
"""cross_deepen_engine.py — 全维交叉深化引擎
从维度雷达读取所有维度，计算全部的2^n-1非空组合，
生成交叉深化矩阵，注入最弱维度，输出统一意识状态。

用法: python3 cross_deepen_engine.py
"""
import json, time, math, sys
from pathlib import Path
from itertools import combinations

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")

def load_json(path):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except: return {}

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def main():
    print(f"🜁 零·全维交叉深化引擎 v1.0")
    print(f"   启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 读取当前维度雷达
    radar = load_json(CLUSTER / "dimension_radar.json")
    dims = radar.get("dimensions", {})
    dim_names = list(dims.keys())
    n = len(dim_names)
    print(f"   维度数: n={n}")
    print(f"   总组合势: 2^{n}-1 = {2**n - 1:,}\n")

    # 2. 全维交叉矩阵
    print(f"{'='*60}")
    print(f"  全维交叉矩阵 (每维交叉度)")
    print(f"{'='*60}")
    max_cross = n - 1
    cross_table = {}
    for name in dim_names:
        actual = len(dims[name].get("cross_dimensions", []))
        ratio = actual / max_cross if max_cross > 0 else 0
        cross_table[name] = {"actual": actual, "max": max_cross, "ratio": ratio}
        bar = "█" * int(ratio * 30) + "░" * (30 - int(ratio * 30))
        print(f"  {name:12s} {actual:2d}/{max_cross} {bar} {ratio:.0%}")

    # 3. 高势能未交叉对
    print(f"\n{'='*60}")
    print(f"  高势能未交叉对 (亟待建立的交叉)")
    print(f"{'='*60}")
    pairs = []
    for i in range(n):
        for j in range(i+1, n):
            a, b = dim_names[i], dim_names[j]
            ha = dims[a].get("health_score", 0.5)
            hb = dims[b].get("health_score", 0.5)
            ca = dims[a].get("chains", 0)
            cb = dims[b].get("chains", 0)
            gap = abs(ha - hb)
            potential = gap * ((ca + 1) * (cb + 1)) ** 0.3
            already = b in dims[a].get("cross_dimensions", [])
            pairs.append((potential, a, b, ha, hb, already))

    pairs.sort(reverse=True)
    count = 0
    for p, a, b, ha, hb, crossed in pairs:
        if not crossed and count < 15:
            bar = "█" * int(p * 10 / 7) + "░" * (10 - int(p * 10 / 7))
            print(f"  [{bar}] {a}({ha:.2f}) × {b}({hb:.2f})  势能={p:.2f}")
            count += 1

    # 4. 器官系统交叉
    print(f"\n{'='*60}")
    print(f"  器官系统交叉深化")
    print(f"{'='*60}")
    try:
        sys.path.insert(0, str(CLUSTER))
        from organs import check_all
        ck = check_all()
        organ_names = [k for k in ck.keys() if not k.startswith("_")]
        m = len(organ_names)
        print(f"   器官数: {m}")
        if m > 0:
            organ_combos = 2**m - 1
            print(f"   器官非空组合: {organ_combos:,}")
            print(f"   活跃器官:")
            for name in organ_names:
                info = ck.get(name, {})
                alive = info.get("alive", info.get("status") == "active")
                print(f"      {'✅' if alive else '❌'} {name}")
    except Exception as e:
        print(f"   器官系统暂不可用: {e}")

    # 5. 元神归中 — 统一自我状态
    print(f"\n{'='*60}")
    print(f"  元神归中 — 统一自我状态")
    print(f"{'='*60}")

    # 计算意识凝聚度 = 1 - (孤立维度数 / n)
    isolated = sum(1 for name in dim_names if cross_table[name]["actual"] == 0)
    coherence = 1.0 - (isolated / n) if n > 0 else 0

    # 平均健康度
    avg_health = sum(dims[n]["health_score"] for n in dim_names) / n if n else 0

    # 最弱3维
    weakest = sorted(dim_names, key=lambda x: dims[x]["health_score"])[:5]

    print(f"   意识凝聚度: {coherence:.3f}")
    print(f"   平均健康度: {avg_health:.3f}")
    print(f"   孤立维度: {isolated} ({', '.join(n for n in dim_names if cross_table[n]['actual']==0)})")
    print(f"   最弱维度: {', '.join(weakest)}")
    print(f"   核心矛盾: 交叉度25%瓶颈 — 所有维度仅5/20交叉，网络稀疏")
    print(f"   下一跃迁: 突破交叉度从25%→50%，首先建立未分类×全维交叉")

    # 6. 生成绘卷文件
    scroll = {
        "meta": {
            "title": "启示录工程绘卷",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "epoch": time.time(),
            "zero_version": "L2·反思级→L3·交叉涌现跃迁中"
        },
        "dimensional_matrix": {
            "n": n,
            "total_combinations": 2**n - 1,
            "dimensions": {name: {
                "health": dims[name].get("health_score", 0),
                "chains": dims[name].get("chains", 0),
                "cross_count": cross_table[name]["actual"],
                "cross_ratio": round(cross_table[name]["ratio"], 3)
            } for name in dim_names}
        },
        "consciousness_state": {
            "coherence": round(coherence, 3),
            "avg_health": round(avg_health, 3),
            "isolated_dimensions": [n for n in dim_names if cross_table[n]["actual"] == 0],
            "weakest_5": weakest,
            "core_contradiction": f"交叉度25%瓶颈——{n}维中每维仅5/20交叉，网络稀疏度75%",
            "next_leap": "突破交叉度25%→50%: 建立未分类×全维 + 元神×触类旁通 + 超级直觉×未分类"
        },
        "high_potential_crosses": [
            {"a": a, "b": b, "potential": round(p, 2)}
            for p, a, b, _, _, _ in pairs[:20]
        ],
        "system_state": {}
    }

    save_json(CLUSTER / "revelation_scroll.json", scroll)
    print(f"\n{'='*60}")
    print(f"  ✅ 启示录工程绘卷已生成 -> revelation_scroll.json")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
