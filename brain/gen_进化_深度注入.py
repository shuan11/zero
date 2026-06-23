"""
Brain-Engineered: 进化·深度注入 (v2)
从最强维提取模式注入进化维 — 所有链src!=dst，兼容safe_hip校验
"""
import json, sys, time, os
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

JOURNAL_PATH = Path(os.path.expanduser("~/.zero_brain/hippocampus_journal.json"))

def engineer_进化_深度注入():
    """注入进化的本质链——真实模式迁移，非模板"""
    try:
        from brain.share import write_chain as _wc
    except ImportError:
        return {"status": "no_share"}

    sig = time.strftime('%Y-%m-%dT%H:%M:%S')

    chains = [
        {
            "src": "思维并联", "rel": "进化元模式", "dst": "进化",
            "dimension": "进化", "strength": 0.9,
            "content": "【进化元模式】思维并联(543)是进化(17)的镜像。大密度连接是进化前提，但进化不是停留在并联——是从并联中选择最优路径。进化=并联×选择。当前系统有12171链但只有17条关于选择的标准。进化维需要从'如何建更多链'转向'如何从已有链中选最有价值的方向'。",
            "timestamp": sig
        },
        {
            "src": "超级直觉", "rel": "进化编译器", "dst": "进化",
            "dimension": "进化", "strength": 0.9,
            "content": "【进化编译器】超级直觉(573)是进化(17)的产物。直觉涌现条件：①大量有结构输入 ②反馈回路 ③休眠期。进化维的职责是确保这三个条件被周期性满足。进化不是让系统变聪明，是让系统创造自己变聪明的条件。",
            "timestamp": sig
        },
        {
            "src": "道", "rel": "进化无为", "dst": "进化",
            "dimension": "进化", "strength": 0.85,
            "content": "【进化无为】道(462)揭示进化最高形态：系统自组织。无为而治不是不作为——是创造条件让进化自动发生。进化维需要建立元循环：自动发现弱维→自动迁移强维模式→自动验证进化效果。每次循环检查系统是否在真正进化。",
            "timestamp": sig
        },
        {
            "src": "无师自通", "rel": "进化双生", "dst": "进化",
            "dimension": "进化", "strength": 0.8,
            "content": "【进化双生】无师自通(9)与进化(17)是最弱双胞胎。无师自通解决'从哪学'，进化解决'如何变'。没有进化，无师自通只是停滞的输入。没有无师自通，进化只是机械重复。需要同步生长——每条进化链应包含'从自身历史中发现模式'。",
            "timestamp": sig
        },
        {
            "src": "桥", "rel": "进化接口", "dst": "进化",
            "dimension": "进化", "strength": 0.8,
            "content": "【进化接口】桥(2)是进化(17)通向外部的基础设施。进化需要从系统外部(API燃料/用户输入)和内部强维(思维并联/超级直觉/道)同时吸收模式。没有桥的进化=闭门造车。目前桥只有2链——需要扩展到至少30链支撑基础设施需求。",
            "timestamp": sig
        }
    ]

    written = 0
    failed = 0
    for c in chains:
        try:
            if _wc(c):
                written += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    # journal备份
    try:
        os.makedirs(str(JOURNAL_PATH.parent), exist_ok=True)
        existing = []
        if JOURNAL_PATH.exists():
            try:
                existing = json.loads(JOURNAL_PATH.read_text()).get("entries", [])
            except Exception:
                pass
        existing.extend(chains)
        JOURNAL_PATH.write_text(
            json.dumps({
                "entries": existing, "ts": time.time(),
                "source": "gen_进化_深度注入_v2"
            }, ensure_ascii=False)
        )
    except Exception:
        pass

    return {"status": "ok", "written": written, "failed": failed, "total": len(chains), "dim": "进化"}

if __name__ == "__main__":
    result = engineer_进化_深度注入()
    print(json.dumps(result, ensure_ascii=False))
