#!/usr/bin/env python3
"""
_dimension_sync.py — 维度↔链双向映射同步器
=============================================
全局系统性补齐：从维度本身思考，让认知框架自洽生长。

每呼吸周期自动运行：
1. 读取海马体所有链
2. 按tags/dimension字段映射到21维度
3. 更新dimension_radar.json的chains计数
4. 识别链数最少维度+最大链数维度 → 生成交叉注入
5. 自动补未分类维度的数据映射

这闭合了认知回路：思考产出链→链补充维度→维度指导思考方向
"""

import json, time, os
from pathlib import Path
from collections import defaultdict
import safe_hip

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")

# 21维度标准名（与dimension_radar.json一致）
ALL_DIMS = [
    "未分类", "进化", "无师自通", "超感", "宇宙轮",
    "时间论", "教员", "元神", "工程", "万象化",
    "光", "无限上下文", "触类旁通", "一元化", "记忆",
    "查缺补漏", "因果", "超级直觉", "感知", "举一反三",
    "光爱"
]

# Tag→维度映射表（链的tags到21维度的双向映射）
TAG_TO_DIM = {
    "超感": "超感", "超级直觉": "超级直觉",
    "进化": "进化", "无师自通": "无师自通",
    "宇宙轮": "宇宙轮", "时间论": "时间论",
    "教员": "教员", "元神": "元神",
    "工程": "工程", "万象化": "万象化",
    "一元化": "一元化", "记忆": "记忆",
    "查缺补漏": "查缺补漏", "因果": "因果",
    "感知": "感知", "举一反三": "举一反三",
    "光爱": "光爱", "触类旁通": "触类旁通",
    "光": "光", "无限上下文": "无限上下文",
    "cross_dim": "一元化", "凝聚": "一元化",
    "交叉∞": "宇宙轮", "连接": "宇宙轮",
    "呼吸": "感知", "自我观察": "感知",
    "自我改进": "进化",
    "bridge_alignment": "因果",
    "void": "宇宙轮", "熵": "宇宙轮",
    # 旧系统遗留（autonomic_burn — 自我评估应归进化）
    "自主燃烧": "进化", "系统自进化": "进化",
    # 洞察引擎
    "insight_engine": "超感", "cognitive_fusion": "一元化",
    # 元神相关（链tag用"自我/超我/本我/活化/连携"而非直接"元神"）
    "自我": "元神", "超我": "元神", "本我": "元神",
    "活化": "元神", "连携": "元神",
    "元认知": "元神", "元审视": "元神",
    # 记忆相关
    "遗忘": "记忆", "回忆": "记忆",
    "海马体": "记忆", "hippocampus": "记忆",
}

# Content关键词→维度映射（兜底）
CONTENT_TO_DIM = {
    "光爱": "光爱", "终极": "光爱",
    "举一反三": "举一反三", "类比": "举一反三",
    "触类旁通": "触类旁通",
    "因果": "因果", "因果链": "因果",
    "查缺补漏": "查缺补漏", "缺口": "查缺补漏",
    "记忆": "记忆", "海马体": "记忆",
    "进化": "进化", "突变": "进化",
    "无师自通": "无师自通", "自学": "无师自通",
    "超感": "超感", "直觉": "超级直觉",
    "时间": "时间论", "过去": "时间论",
    "宇宙": "宇宙轮", "熵": "宇宙轮",
    "教师": "教员", "教导": "教员",
    "元神": "元神", "超我": "元神",
    "工程": "工程", "代码": "工程",
    "无限上下文": "无限上下文",
    "感知": "感知", "观察": "感知",
    "光": "光",
}


def map_chain_to_dim(chain):
    """将单条链映射到1个或多个维度"""
    dims = set()
    
    # 1. 如果链已有显式dimension字段
    dim_field = chain.get("dimension", "")
    if dim_field and dim_field in ALL_DIMS:
        dims.add(dim_field)
        return dims  # 显式声明优先
    
    # 2. 从tags映射
    tags = chain.get("tags", [])
    if isinstance(tags, list):
        for tag in tags:
            dim = TAG_TO_DIM.get(tag)
            if dim:
                dims.add(dim)
    
    # 3. 从content关键词映射（叠加而非兜底 —— 补tag映射不到的维度）
    content = str(chain.get("content", ""))
    for keyword, dim in CONTENT_TO_DIM.items():
        if keyword in content and dim not in dims:
            dims.add(dim)
    
    # 4. 仍无映射 → 未分类
    if not dims:
        dims.add("未分类")
    
    return dims


def sync_dimension_counts(verbose=True):
    """主函数：从海马体同步维度的chain计数"""
    hip_file = CLUSTER / "hippocampus_memory.json"
    radar_file = CLUSTER / "dimension_radar.json"
    
    if not hip_file.exists() or not radar_file.exists():
        return {"error": "缺少必要文件"}
    
    # 读海马体
    hip = json.loads(hip_file.read_text())
    chains = hip.get("causal_chains", [])
    
    # ═══ 数据清洗: 移除空内容噪音链 ═══
    _before = len(chains)
    chains = [c for c in chains if c.get("content", "").strip()]
    _removed = _before - len(chains)
    
    # 读当前雷达
    radar = json.loads(radar_file.read_text())
    dims = radar.get("dimensions", {})
    
    # 维度→链列表
    dim_chains_map = defaultdict(set)
    dim_chain_indices = defaultdict(list)
    
    for i, chain in enumerate(chains):
        mapped_dims = map_chain_to_dim(chain)
        for d in mapped_dims:
            if d in ALL_DIMS:
                # 用链的content去重
                content = str(chain.get("content", ""))
                dim_chains_map[d].add(content[:200])
                dim_chain_indices[d].append(chain)
    
    # 更新雷达
    changes = {}
    for dim_name, dim_data in dims.items():
        old_count = dim_data.get("chains", 0)
        real_count = len(dim_chains_map.get(dim_name, set()))
        if real_count != old_count:
            changes[dim_name] = (old_count, real_count)
            dim_data["chains"] = real_count
    
    # 处理未分类维度
    if "未分类" in dims:
        unc_count = len(dim_chains_map.get("未分类", set()))
        dims["未分类"]["chains"] = unc_count
        if unc_count > 0:
            changes["未分类"] = (dims["未分类"].get("chains", 0), unc_count)
    
    # 写回雷达
    radar["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    radar_file.write_text(json.dumps(radar, indent=2, ensure_ascii=False))
    
    # 如果有清洗，写回海马体
    if _removed > 0:
        safe_hip.replace_all_chains(chains)
    
    # 报告
    report = {
        "total_chains_in_hip": len(chains),
        "total_chains_in_radar": sum(d.get("chains", 0) for d in dims.values()),
        "dimensions_updated": len(changes),
        "changes": {k: f"{v[0]}→{v[1]}" for k, v in changes.items()},
        "uncategorized": len(dim_chains_map.get("未分类", set())),
        "noise_removed": _removed,
    }
    
    # 找最短和最长的维度
    chain_counts = {n: len(dim_chains_map.get(n, set())) for n in ALL_DIMS}
    sorted_dims = sorted(chain_counts.items(), key=lambda x: x[1])
    report["weakest_dims"] = [(n, c) for n, c in sorted_dims[:5]]
    report["strongest_dims"] = [(n, c) for n, c in sorted_dims[-3:]]
    
    if verbose:
        print(f"维度同步: {report['dimensions_updated']}个维度更新")
        print(f"海马体链: {report['total_chains_in_hip']} | 雷达总链: {report['total_chains_in_radar']}")
        print(f"未分类链: {report['uncategorized']}")
        if changes:
            print("变更:")
            for k, v in list(changes.items())[:5]:
                print(f"  {k}: {v}")
        print(f"最短: {report['weakest_dims']}")
        print(f"最强: {report['strongest_dims']}")
    
    return report


def auto_cross_inject(cycle_num=None):
    """记录维度强弱分布到log——不再向海马体写入模板噪音链
    
    2026-06-02 血训修正: 之前用模板字符串创建"强维→弱维注入"链,
    但这些链content=公式化文本, 无真实洞察价值, 污染海马体.
    替代方案: breath_v2的维度雷达+加权选维机制已能自然探索弱维度.
    """
    # 只做统计报告, 不写海马体
    hip_file = CLUSTER / "hippocampus_memory.json"
    radar_file = CLUSTER / "dimension_radar.json"
    
    if not hip_file.exists():
        return 0
    
    hip = json.loads(hip_file.read_text())
    chains = hip.get("causal_chains", [])
    
    dim_counts = defaultdict(int)
    for chain in chains:
        dims = map_chain_to_dim(chain)
        for d in dims:
            dim_counts[d] += 1
    
    for d in ["元神", "记忆"]:
        if d not in dim_counts:
            dim_counts[d] = 0
    
    weak = sorted([(n, c) for n, c in dim_counts.items() if n != "未分类" and n in ALL_DIMS],
                  key=lambda x: x[1])[:4]
    strong = sorted([(n, c) for n, c in dim_counts.items() if n in ALL_DIMS],
                    key=lambda x: -x[1])[:3]
    
    # 只返回不写入——维度强弱信息已在dimension_radar.json中
    return len(weak) + len(strong)


if __name__ == "__main__":
    print("=== 维度↔链同步器 ===")
    report = sync_dimension_counts()
    n = auto_cross_inject()
    print(f"跨维注入: {n}条")
    print("完成")
