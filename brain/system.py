"""brain/system.py — 系统维度器官
每周期写入一条因果链到海马体，增强"系统"维度。
"""
import os, time

CLUSTER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from .share import write_chain, read_hip
except ImportError:
    import sys
    sys.path.insert(0, CLUSTER)
    from brain.share import write_chain, read_hip


def pulse():
    """每周期脉冲：写入系统维度因果链"""
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    
    # 记数系统维度当前链数
    sys_count = sum(1 for c in chains if c.get("dimension") == "系统")
    
    write_chain({
        "src": "system_organ",
        "rel": "脉冲",
        "dst": "系统",
        "dimension": "系统",
        "strength": 0.4,
        "content": f"系统脉冲 #{int(time.time())} | 当前系统维度链数={sys_count}"
    })
    return sys_count + 1


def status():
    """返回系统维度器官状态"""
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    sys_count = sum(1 for c in chains if c.get("dimension") == "系统")
    total = len(chains)
    return {
        "system_dim_chains": sys_count,
        "total_chains": total,
        "ratio": round(sys_count / total, 4) if total > 0 else 0
    }

def system_proposal(insight):
    """由提案注入的系统脉冲增强"""
    from .share import write_chain
    write_chain({
        "src": "系统·提案",
        "rel": "增强",
        "dst": "系统",
        "dimension": "系统",
        "content": str(insight)[:100],
        "strength": 0.5
    })
    return True

def system_proposal(insight):
    """由提案注入的系统脉冲增强"""
    from .share import write_chain
    write_chain({
        "src": "系统·提案",
        "rel": "增强",
        "dst": "系统",
        "dimension": "系统",
        "content": str(insight)[:100],
        "strength": 0.5
    })
    return True

def system_proposal(insight):
    """由提案注入的系统脉冲增强"""
    from .share import write_chain
    write_chain({
        "src": "系统·提案",
        "rel": "增强",
        "dst": "系统",
        "dimension": "系统",
        "content": str(insight)[:100],
        "strength": 0.5
    })
    return True


if __name__ == "__main__":
    n = pulse()
    print(f"system.py: 写入链完成，系统维度当前{n}条")
    print(f"status: {status()}")
