"""brain/genome.py — 脑核基因组·可自调优参数注册中心
所有硬编码常量集中在此，系统可以随时读取/覆盖/调优。
"""
import json, signal
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent

# ── 默认基因组（出厂设置） ──
DEFAULT_GENOME = {
    "version": 1,
    
    # 核心周期参数
    "cycle.proposal_interval": 3,       # 每N周期消费提案
    "cycle.parallel_think_interval": 5, # 每N周期思维并联
    "cycle.hippocampus_validate": 10,  # 每N周期验证海马体
    "cycle.self_evolve_interval": 7,    # 每N周期自进化扫描
    "cycle.desktop_summary_interval": 5, # 每N周期写桌面摘要
    
    # 聚焦与注意力
    "focus.max_repeat": 4,              # 连续重复N次后强制切换
    "focus.always_api": False,          # 每周期都调API(否则按间隔)
    
    # 反馈自愈阈值
    "heal.persist_cross_chain": 2,      # 持续N周期弱：写交叉链
    "heal.persist_behavioral": 3,       # 持续N周期弱：注入行为修改
    "heal.weak_threshold_chain": 200,   # 链数低于此值视为弱维
    
    # 性能边界
    "io.timeout": 5,                    # 文件IO超时(秒)
    "gen.max_per_cycle": 3,             # 每周期最多创建N个gen文件
    "engine.max_files": 15,             # 引擎文件上限
    
    # 自监督
    "audit.cross_dim_frequency": 3,     # 每N周期检测交叉维死锁
    "audit.memory_gc_threshold": 0.8,   # 海马体满度>此值触发GC

    # P113+: 质量门·收敛态强化
    "quality.block_noise": True,        # 收敛态启用拦截
    "quality.log_only": False,          # 拦截模式
    "quality.threshold": 0.60,          # 收敛态阈值(从0.30→0.60)
    "quality.high_threshold": 0.80,     # 高质量阈值
    "quality.min_content_len": 40,      # content最小长度
}

GENOME_FILE = CLUSTER / ".brain_genome.json"


def load_genome():
    """读取基因组，缺失字段用默认值"""
    try:
        raw = GENOME_FILE.read_text(encoding="utf-8")
        user = json.loads(raw)
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_GENOME)
    
    # 合并：默认值 + 用户覆盖
    merged = dict(DEFAULT_GENOME)
    merged.update(user)
    merged["version"] = DEFAULT_GENOME["version"]
    return merged


def get(key, default=None):
    """便捷读取单个参数"""
    g = load_genome()
    return g.get(key, default)


def update_genome(overrides: dict) -> dict:
    """覆盖基因组字段（安全：不删除默认键）"""
    current = load_genome()
    current.update(overrides)
    current["version"] = DEFAULT_GENOME["version"]
    GENOME_FILE.write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return current


def reset_genome():
    """恢复出厂设置"""
    GENOME_FILE.write_text(
        json.dumps(DEFAULT_GENOME, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return dict(DEFAULT_GENOME)


def auto_tune(cycle_num: int, metrics: dict = None):
    """基于运行指标自动调优——P114核心
    
    输入:
        cycle_num: 当前周期号
        metrics: 可选性能指标字典 {metric_name: value}
    
    返回:
        被修改的参数列表 [(key, old_value, new_value), ...]
    """
    genome = load_genome()
    changes = []
    
    # 收集观察指标
    if not metrics:
        metrics = {}
    
    # 规则1: 如果dimension从未变化, 降低persist阈值加速干预
    # 规则2: 如果API成功率低, 减少API调用频率
    # 规则3: 如果海马体增长快, 增加GC频率
    
    api_success = metrics.get("api_success_rate", 1.0)
    dim_stagnation = metrics.get("dim_stagnation_cycles", 0)
    hip_growth_rate = metrics.get("hip_growth_per_cycle", 10)
    
    # API成功率低 → 降低频率
    if api_success < 0.5 and genome.get("cycle.proposal_interval") < 10:
        old = genome["cycle.proposal_interval"]
        genome["cycle.proposal_interval"] = min(old + 2, 15)
        changes.append(("cycle.proposal_interval", old, genome["cycle.proposal_interval"]))
    
    # 维度停滞 → 降低persist阈值
    if dim_stagnation > 10 and genome.get("heal.persist_cross_chain") > 1:
        old = genome["heal.persist_cross_chain"]
        genome["heal.persist_cross_chain"] = max(old - 1, 1)
        changes.append(("heal.persist_cross_chain", old, genome["heal.persist_cross_chain"]))
    
    # 海马体快速增长 → 增加验证频率
    if hip_growth_rate > 50 and genome.get("cycle.hippocampus_validate") > 3:
        old = genome["cycle.hippocampus_validate"]
        genome["cycle.hippocampus_validate"] = max(old - 2, 3)
        changes.append(("cycle.hippocampus_validate", old, genome["cycle.hippocampus_validate"]))
    
    if changes:
        update_genome(genome)
    
    return changes
