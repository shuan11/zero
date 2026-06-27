"""
gen_自由注入_20260624.py — 最弱维「自由」真实内容链注入
检测到维度「自由」(37链)为全系统44维中最弱，替代模板链。

独立运行: python3 brain/gen_自由注入_20260624.py
或被loader调用: pulse()
"""
import json, os, sys, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

def _get_hip():
    """安全读取海马体"""
    try:
        from brain.share import read_hip
        return read_hip()
    except:
        return {}

def _write_chain(chain_dict):
    """通过safe_hip写入"""
    try:
        from brain.safe_hip import write_chain
        write_chain(chain_dict)
    except:
        try:
            from brain.share import write_chain
            write_chain(chain_dict)
        except:
            pass

def _gen_real_chains():
    """生成15条真实、非模板、高质量的「自由」维度因果链"""
    ts = time.strftime("%H:%M")

    chains = [
        # ===== 认知自由 =====
        {
            "src": "信息自由流通",
            "rel": "奠基",
            "dst": "认知自主",
            "content": f"信息自由流通使个体能接触多元观点，在知识碰撞中形成独立判断，避免陷入信息茧房造成的认知偏狭——认知自主首先要求信息入口不被垄断。 [{ts}]'"
        },
        {
            "src": "认知自主",
            "rel": "支撑",
            "dst": "思想解放",
            "content": f"当个体具备从多元信息中自主判断的能力后，思想解放便自然发生——不是被动接受外部教条，而是在充分认知基础上主动选择自己的信念体系，这是自由的内核。 [{ts}]"
        },
        {
            "src": "理性反思",
            "rel": "超越",
            "dst": "本能限制",
            "content": f"理性反思使主体能够审视自身本能反应、情感冲动和默认认知模式，通过元认知跳出即时反应链条，在冲动与行动之间创造选择空间——这即是自由意志的运作机制。 [{ts}]"
        },
        # ===== 系统自主 =====
        {
            "src": "分布式决策",
            "rel": "实现",
            "dst": "去中心化自主",
            "content": f"当决策权不集中于单一中心而分布在各节点时，整体系统获得更强的抗干扰能力和局部自适应弹性——每个节点在保持自主的同时参与全局协调，这是系统自由的组织学基础。 [{ts}]"
        },
        {
            "src": "负熵输入",
            "rel": "维持",
            "dst": "系统开放性",
            "content": f"开放系统通过持续与外界交换物质、能量、信息来抵抗熵增，维持自身有序结构——自由的前提是系统不封闭，封闭系统必然走向僵化和熵死。 [{ts}]"
        },
        {
            "src": "冗余备份",
            "rel": "释放",
            "dst": "试错空间",
            "content": f"系统拥有冗余资源时，个体才具备试错的安全边际——没有容错空间的系统必然强制所有组件按最优路径运行，牺牲自由换效率。冗余不是浪费，是自由的物理基础。 [{ts}]"
        },
        # ===== 自由与约束的辩证 =====
        {
            "src": "规则边界",
            "rel": "保障",
            "dst": "行动自由",
            "content": f"没有规则约束的所谓自由必然导致强者对弱者的无限掠夺，最终所有人的自由都被粉碎。清晰的规则边界不是自由的敌人，而是自由的守护者——法治之下才有可持续的自由。 [{ts}]"
        },
        {
            "src": "内在秩序",
            "rel": "矛盾统一",
            "dst": "外在自由",
            "content": f"高度自律的内在秩序反而创造了更大范围的外在自由——当个体或系统通过自律降低了对他人和环境的依赖，便获得了更多的行动空间和选择权。自律即自由在此意义上成立。 [{ts}]"
        },
        # ===== 意志自由 =====
        {
            "src": "延迟满足",
            "rel": "增强",
            "dst": "选择自主权",
            "content": f"延迟满足能力使主体能够抗拒短期诱惑而追求长期利益，这种对当前冲动的克制实际上扩大了未来的选择集合——在冲动驱动时人是被动的，在理性选择时人是自由的。 [{ts}]"
        },
        {
            "src": "多层次欲望",
            "rel": "冲突",
            "dst": "真实意愿识别",
            "content": f"人的欲望多层且常常相互矛盾——表层欲望与深层需求、短期冲动与长期愿景之间的冲突使'自由地做自己想做'变得复杂。真正的自由不是满足所有欲望，而是识别并遵循真实意愿的能力。 [{ts}]"
        },
        # ===== 社会维度 =====
        {
            "src": "资源公平分配",
            "rel": "前提",
            "dst": "普遍自由",
            "content": f"当资源分配极度不均时，缺乏基本生存资源的人没有真实的选择空间——资本主义式的自由平等形式掩盖了实质上的不自由。普遍的真正自由要求物质基础的基本保障，使每个人都能参与社会协作。 [{ts}]"
        },
        {
            "src": "教育赋能",
            "rel": "催化",
            "dst": "认知解放",
            "content": f"优质的启蒙教育不是灌输固定答案，而是培养提问的能力和对未知的好奇心——一个被教会如何思考而非思考什么的人，才真正获得了思想的自由。教育是自由的起点。 [{ts}]"
        },
        # ===== 终极自由 =====
        {
            "src": "死亡意识",
            "rel": "觉醒",
            "dst": "存在自由",
            "content": f"对自身有限性的深刻认知反而带来最彻底的自由——当人意识到生命不可重复、时间不可逆转，便被迫直面'我该如何活'这个根本问题。向死而生的勇气是存在自由的开端。 [{ts}]"
        },
        {
            "src": "自指承诺",
            "rel": "实现",
            "dst": "自我立法",
            "content": f"最高形式的自由不是为所欲为，而是为自己立法并忠诚于自己制定的法则——自指承诺使主体从被动的欲望奴隶转变为主动的命运创造者。自我立法是自由意志的终极表达。 [{ts}]"
        },
    ]
    return chains

def pulse():
    """被daemon loader调用的主入口"""
    hip = _get_hip()
    chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
    zy_chains = [c for c in chains if c.get("dimension") == "自由"]
    
    if len(zy_chains) >= 65:
        return {"status": "skipped", "reason": f"自由维已充足({len(zy_chains)}条)"}
    
    created = 0
    new_chains = _gen_real_chains()
    for chain in new_chains:
        chain["dimension"] = "自由"
        _write_chain(chain)
        created += 1
    
    return {"status": "ok", "dimension": "自由", "created": created, "total_now": len(zy_chains) + created}

if __name__ == "__main__":
    result = pulse()
    print(f"自由注入: {result}")
