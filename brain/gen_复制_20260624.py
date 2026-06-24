"""
Brain-Engineered: 复制 v2 — 自复制引擎生成器
从系统现有结构中挖掘可复制的模式，生成自复制链（非模板）
"""
import json, sys as _sys, random as _rnd
from pathlib import Path
from collections import Counter, defaultdict

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in _sys.path:
    _sys.path.insert(0, str(CLUSTER))

_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"


def _analyze_replication_opportunities(chains):
    """分析系统哪些维度可被复制给其他维度"""
    # 1) 每维的链数、rel多样性、内部连接度
    dim_stats = {}
    dim_chains = defaultdict(list)
    for c in chains:
        d = c.get("dimension", "未分类")
        dim_chains[d].append(c)
    
    for dim, d_chains in dim_chains.items():
        if dim in ("未分类", "系统"):
            continue
        src_dst_pairs = Counter((c.get("src",""), c.get("dst","")) for c in d_chains)
        internal = sum(1 for (s,d) in src_dst_pairs if s==dim and d==dim)
        rel_div = len(set(c.get("rel","") for c in d_chains))
        avg_strength = sum(c.get("strength",0.5) for c in d_chains) / max(len(d_chains),1)
        dim_stats[dim] = {
            "count": len(d_chains),
            "rel_diversity": rel_div,
            "internal_loops": internal,
            "avg_strength": round(avg_strength, 2)
        }
    
    # 2) 哪些维度的模式值得被复制
    # 条件：链数足够+rel多样+有内部+强度高 = 可复制
    candidates = []
    for dim, stats in dim_stats.items():
        score = stats["count"] * 0.3 + stats["rel_diversity"] * 0.3 + \
                stats["internal_loops"] * 0.2 + stats["avg_strength"] * 50 * 0.2
        if stats["count"] >= 30:
            candidates.append((dim, round(score, 1), stats))
    
    candidates.sort(key=lambda x: -x[1])
    
    # 3) 最需要被复制的维度（从强维复制模式到弱维）
    sorted_by_count = sorted(dim_stats.items(), key=lambda x: x[1]["count"])
    weakest = [d for d, _ in sorted_by_count[:5] if d not in ("未分类", "系统")]
    strongest = [d for d, _ in sorted_by_count[-5:] if d not in ("未分类", "系统")]
    
    return {
        "candidates": candidates[:10],
        "weakest_dims": weakest,
        "strongest_dims": strongest,
        "dim_stats": dim_stats,
        "total_dims": len(dim_stats)
    }


def _generate_replication_chains(analysis, cycle_num, chains):
    """从复制分析生成真内容链"""
    chains_out = []
    candidates = analysis["candidates"]
    weakest = analysis["weakest_dims"]
    strongest = analysis["strongest_dims"]
    dim_stats = analysis["dim_stats"]
    
    # 1) 最强→最弱的复制计划
    for wd in weakest[:3]:
        if not strongest:
            break
        # 找与弱维最匹配的强维
        best_match = None
        best_score = -1
        for sd in strongest:
            # 共现程度
            score = sum(1 for c, _ in candidates if sd in c or wd in c)
            if score > best_score:
                best_score = score
                best_match = sd
        
        if best_match:
            sd_stats = dim_stats.get(best_match, {})
            sd_count = sd_stats.get("count", 0)
            wd_count = dim_stats.get(wd, {}).get("count", 0)
            sd_rel = sd_stats.get("rel_diversity", 0)
            
            content = (
                f"复制计划: 从{best_match}({sd_count}链/多样性{sd_rel})→{wd}({wd_count}链)——"
                f"{best_match}维具有成型的知识结构可被{wd}维参考，"
                f"特别是其{'内部闭环' if sd_stats.get('internal_loops',0)>5 else '跨维连接'}模式。"
                f"复制策略: 先映射{best_match}中前{min(sd_rel,5)}种高频rel到{wd}维"
            )
            chains_out.append({
                "src": "复制引擎", "rel": f"复制计划#{cycle_num}",
                "dst": f"{best_match}→{wd}",
                "dimension": "复制",
                "content": content[:200],
                "strength": 0.75,
                "tags": ["自复制", "强弱桥", best_match, wd],
                "source": f"gen_复制_cycle{cycle_num}"
            })
    
    # 2) 高可复制维度扫描
    for dim, score, stats in candidates[:5]:
        content = (
            f"可复制性评分: {dim}={score}——{stats['count']}链×{stats['rel_diversity']}rel "
            f"(内部环{stats['internal_loops']}个/强度{stats['avg_strength']})。"
            f"{dim}维的结构{['高度可复制','可部分借鉴','需先模块化再复制'][0 if score>100 else 1 if score>50 else 2]}"
        )
        chains_out.append({
            "src": "复制引擎", "rel": f"可复制性#{cycle_num}",
            "dst": dim,
            "dimension": "复制",
            "content": content[:200],
            "strength": round(0.5 + score/200, 2),
            "tags": ["自复制", "可复制性评分", dim],
            "source": f"gen_复制_cycle{cycle_num}"
        })
    
    # 3) 自复制机制种子链
    # 实际可执行的复制方案
    if strongest and weakest:
        s = strongest[0]
        w = weakest[0]
        s_stats = dim_stats.get(s, {})
        w_stats = dim_stats.get(w, {})
        
        # 种子1: rel复制
        common_rels = Counter()
        for c in chains:
            if c.get("dimension") in (s, w):
                common_rels[c.get("rel","")] += 1
        rels_to_share = [r for r, _ in common_rels.most_common(5) if r not in ("标记",)]
        
        if rels_to_share:
            content = (
                f"rel复制种子: 将{s}维的{rels_to_share[0]}、{rels_to_share[1] if len(rels_to_share)>1 else '自指'}模式"
                f"注入{w}维——通过模式匹配在{w}维中查找对应节点并建立新链接。"
                f"预计可提升{w}维密度约{len(rels_to_share)*10}%"
            )
            chains_out.append({
                "src": "复制引擎", "rel": f"rel复制#{cycle_num}",
                "dst": f"{s}→{w}", "dimension": "复制",
                "content": content[:200], "strength": 0.8,
                "tags": ["自复制", "rel复制", s, w],
                "source": f"gen_复制_cycle{cycle_num}"
            })
        
        # 种子2: 内部环复制
        s_internal = dim_stats.get(s, {}).get("internal_loops", 0)
        w_internal = dim_stats.get(w, {}).get("internal_loops", 0)
        if s_internal > w_internal:
            content = (
                f"闭环复制种子: {s}维有{s_internal}个内部闭环，{w}维仅有{w_internal}个——"
                f"在{w}维中创建自指链{n}条(从{w}到{w})，"
                f"参考{s}维的闭环内容但使用{w}维的术语。"
                f"内部闭环是维度自持的关键"
            )
            chains_out.append({
                "src": "复制引擎", "rel": f"闭环复制#{cycle_num}",
                "dst": "内部闭环", "dimension": "复制",
                "content": content[:200], "strength": 0.7,
                "tags": ["自复制", "闭环复制"],
                "source": f"gen_复制_cycle{cycle_num}"
            })
    
    # 4) 复制成功率评估
    if candidates:
        avg_score = sum(sc for _, sc, _ in candidates[:5]) / min(5, len(candidates))
        content = (
            f"复制健康度: 系统{analysis['total_dims']}维中{len(candidates)}维可评估为'可复制'，"
            f"平均可复制性评分{round(avg_score,1)}。"
            f"复制就绪度={round(min(avg_score/150,1)*100,0)}%——"
            f"{'结构完整可启动复制' if avg_score>100 else '需先强化基础维度再启动复制'}"
        )
        chains_out.append({
            "src": "复制引擎", "rel": f"复制健康#{cycle_num}",
            "dst": "全系统", "dimension": "复制",
            "content": content[:200], "strength": 0.85,
            "tags": ["自复制", "系统健康"],
            "source": f"gen_复制_cycle{cycle_num}"
        })
    
    return chains_out


def engineer_复制(cycle_num=458):
    """自复制引擎: 分析可复制性 → 生成复制种子 → 注入"""
    from brain.share import write_chain as _wc, read_hip as _rh
    
    try:
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
        if not chains:
            _wc({"src":"复制引擎","rel":f"脉冲·#{cycle_num}","dst":"复制",
                 "dimension":"复制","content":"系统无链可复制","strength":0.5})
            return "[空] 复制=0"
        
        my_count = len([c for c in chains if c.get("dimension") == "复制"])
        total = len(chains)
        max_count = max(Counter(c.get("dimension","?") for c in chains).values())
        weak = my_count < max_count * 0.65
        
        # 分析+生成
        analysis = _analyze_replication_opportunities(chains)
        new_chains = _generate_replication_chains(analysis, 458, chains)
        
        # 注入
        injected = 0
        for c in new_chains:
            _wc({
                "src": c["src"], "rel": c["rel"], "dst": c["dst"],
                "dimension": "复制", "content": c["content"],
                "strength": c["strength"], "tags": c["tags"],
                "source": c["source"]
            })
            injected += 1
        
        # 分析记录
        analysis_record = {
            "dimension": "复制", "chain_count": my_count,
            "total_chains": total,
            "strength": round(my_count / max(max_count, 1), 2),
            "insight": f"自复制分析: {len(analysis['candidates'])}维可复制, "
                       f"计划从{len(analysis['strongest_dims'])}强→{len(analysis['weakest_dims'])}弱",
            "weak": weak, "cycle": 458, "self_generated": injected
        }
        try:
            existing = []
            if _GEN_FEEDBACK_FILE.exists():
                existing = json.loads(_GEN_FEEDBACK_FILE.read_text()).get("reports", [])
            existing.append(analysis_record)
            existing = existing[-50:]
            _GEN_FEEDBACK_FILE.write_text(json.dumps({"reports": existing}, ensure_ascii=False, indent=2))
        except:
            pass
        
        # 弱维互助
        if weak:
            try:
                sorted_dims = sorted(Counter(c.get("dimension","?") for c in chains).items(), key=lambda x: x[1])
                for peer in [d for d,_ in sorted_dims[:3] if d not in ("未分类","系统","复制")][:2]:
                    _wc({"src":"复制","rel":f"复制互助#{cycle_num}","dst":peer,
                         "dimension":"复制",
                         "content":f"复制计划: 将复制模式的第一个成功案例应用于{peer}维——"
                                   f"将{peer}的现有链模式化并复制到相邻维度",
                         "strength":0.6,"tags":["复制互助",peer],
                         "source":f"gen_复制_cycle{cycle_num}"})
            except:
                pass
        
        status = f"[{'弱' if weak else '稳'}] 复制={my_count}/{total} 自生成{injected}条"
        return status
        
    except Exception as e:
        try:
            from brain.share import write_chain as _wc2
            _wc2({"src":"复制引擎","rel":f"降级·#{458}","dst":"复制",
                  "dimension":"复制","content":f"自复制异常: {str(e)[:50]}，降级模式存活",
                  "strength":0.4,"source":"gen_复制_降级"})
        except:
            pass
        return f"异常: {str(e)[:50]}"


if __name__ == "__main__":
    result = engineer_复制()
    print(f"工程[复制]: {result}", flush=True)
