"""brain/dim_seed.py — 零链维度连续种子注入
每周期为6个零链维度(观察/状态/检查/修复/复制/对话)各写入一条因果链。
与system.py的pulse()模式相同，确保各维度持续增长。
"""
import os, time

CLUSTER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from .share import write_chain, read_hip
except ImportError:
    import sys
    sys.path.insert(0, CLUSTER)
    from brain.share import write_chain, read_hip


def pulse_all(cycle_num, obs=None, state=None, inspection=None, heal=None, thought=None, mirror=None):
    """每周期写入6维度种子链各一条
    
    Args:
        cycle_num: 周期号
        obs: self_observe()输出（可选）
        state: save_state()输出（可选）
        inspection: inspect_and_report()输出（可选）
        heal: heal_from_inspection()输出（可选）
        thought: think()输出（可选）
        mirror: full_mirror()输出（可选）
    
    Returns:
        写入的维度列表
    """
    chains = _build_chains(cycle_num, obs, state, inspection, heal, thought, mirror)
    for ch in chains:
        write_chain(ch)
    
    return [ch["dimension"] for ch in chains]


def _build_chains(cycle_num, obs, state, inspection, heal, thought=None, mirror=None):
    """构建6维度链
    注意: rel里含cycle_num确保每周期(🔴,rel,dst)唯一，防dedup合并
    content以"#C "开头避免被_extract_edge正则捕获
    """
    # 观察 — 来自self_observe输出
    obs_text = ""
    if obs and isinstance(obs, list) and len(obs) > 0:
        obs_text = obs[0][:60] if isinstance(obs[0], str) else str(obs[0])[:60]
    else:
        obs_text = f"观察周期#{cycle_num}"
    
    # 状态 — 当前系统状态摘要
    state_text = ""
    if state and isinstance(state, dict):
        state_text = f"cycle={state.get('cycle','?')} state={state.get('status','?')}"
    else:
        state_text = f"状态#{cycle_num}"
    
    # 检查 — 检查结果
    insp_text = ""
    if inspection and isinstance(inspection, dict):
        summary = inspection.get("summary", {})
        overall = summary.get("overall", "UNKNOWN")
        failed = summary.get("failed", 0)
        passed = summary.get("passed", 0)
        insp_text = f"总计={passed+failed} PASS={passed} FAIL={failed} 结论={overall}"
    else:
        insp_text = f"检查周期#{cycle_num}"
    
    # 修复 — 修复结果
    heal_text = ""
    if heal and isinstance(heal, dict):
        healed = heal.get("healed", 0)
        failed_h = heal.get("failed", 0)
        heal_text = f"已修复={healed} 修复失败={failed_h}"
    else:
        heal_text = f"修复周期#{cycle_num}"
    
    # 复制 — 来自镜像结果
    rep_text = ""
    if mirror and isinstance(mirror, dict):
        hip = mirror.get("hippocampus", {})
        hb = mirror.get("health", {}).get("heartbeat", {})
        rep_text = f"hip={hip.get('status','?')} cycle={hb.get('cycle','?')}"
    else:
        rep_text = f"镜像周期#{cycle_num}"
    
    # 对话 — 来自思考洞察
    dia_text = ""
    if thought and isinstance(thought, dict):
        insight = thought.get("insight", "")[:60]
        focus = thought.get("focus", "")
        dia_text = f"insight={insight} focus={focus}"
    else:
        dia_text = f"自我对话周期#{cycle_num}"
    
    chains = [
        {
            "src": "self_observe",
            "rel": f"观测#{cycle_num}",
            "dst": "系统状态",
            "dimension": "观察",
            "strength": 0.35,
            "content": f"#C{cycle_num} {obs_text}"
        },
        {
            "src": "state_manager",
            "rel": f"存档#{cycle_num}",
            "dst": "当前状态",
            "dimension": "状态",
            "strength": 0.3,
            "content": f"#C{cycle_num} {state_text}"
        },
        {
            "src": "inspect_organ",
            "rel": f"审查#{cycle_num}",
            "dst": "系统健康",
            "dimension": "检查",
            "strength": 0.35,
            "content": f"#C{cycle_num} {insp_text}"
        },
        {
            "src": "heal_organ",
            "rel": f"修复#{cycle_num}",
            "dst": "系统缺陷",
            "dimension": "修复",
            "strength": 0.35,
            "content": f"#C{cycle_num} {heal_text}"
        },
        {
            "src": "replica_organ",
            "rel": f"备份#{cycle_num}",
            "dst": "系统镜像",
            "dimension": "复制",
            "strength": 0.25,
            "content": f"#C{cycle_num} {rep_text}"
        },
        {
            "src": "dialogue_organ",
            "rel": f"交流#{cycle_num}",
            "dst": "自我对话",
            "dimension": "对话",
            "strength": 0.3,
            "content": f"#C{cycle_num} {dia_text}"
        },
    ]
    return chains


def status():
    """返回6维度当前链数"""
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    dims = {"观察": 0, "状态": 0, "检查": 0, "修复": 0, "复制": 0, "对话": 0}
    for c in chains:
        d = c.get("dimension", "")
        if d in dims:
            dims[d] += 1
    return dims


if __name__ == "__main__":
    dims_before = status()
    written = pulse_all(1)
    dims_after = status()
    print(f"写入前: {dims_before}")
    print(f"写入维度: {written}")
    print(f"写入后: {dims_after}")
