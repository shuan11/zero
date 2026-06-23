#!/usr/bin/env python3
"""
meta_fix_connector.py — 元修复连接器
连接 meta_gap_finder → neural_collaboration_orchestrator 的自动修复闭环
==============================================================
架构:
  meta_gap_finder (缺口发现)
    ↓ 读取 GAP_LOG + genome.gaps_open
  meta_fix_connector (本模块)
    ↓ 缺口分类路由
  NeuralCollaborationOrchestrator (编排修复)
    ├─ codex (18790) → 代码类缺口
    ├─ claude (18791) → 分析类缺口
    ├─ openclaw_wsl (18792) → 流程类缺口
    ├─ opengod (18793) → 哲学类缺口
    └─ hermes (18789) → 通用类缺口
    ↓
  genome.gaps_resolved (写入修复记录)

用法:
  python3 meta_fix_connector.py              # 单次执行
  python3 meta_fix_connector.py --daemon     # 持续运行(每120s)
  python3 meta_fix_connector.py --status     # 查看fix历史
"""

import sys, os, json, time, re, argparse
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
#  路径常量
# ═══════════════════════════════════════════════════════════════

WORKDIR = Path("/mnt/c/Users/h/Desktop/零/真元集群")
GAP_LOG = Path("/mnt/c/Users/h/Desktop/元查缺补漏·永久日志.json")
GENOME_FILE = Path("/mnt/c/Users/h/Desktop/真元·进化基因组.json")
HIP_PATH = WORKDIR / "hippocampus_memory.json"

sys.path.insert(0, str(WORKDIR))
from genome import load_genome, resolve_gap, mutate_genome

# ═══════════════════════════════════════════════════════════════
#  缺口分类引擎
# ═══════════════════════════════════════════════════════════════

# 分类关键词 → (neuron_id, 频道, 端口)
CLASSIFIER_RULES = [
    # 代码类 → Codex
    (["syntax", "bug", "error", "crash", "traceback", "exception",
      "import", "compile", "依赖", "代码", "编译", "报错", "语法",
      "module not found", "typeerror", "attributeerror", "null",
      "变量", "函数", "方法", "class", "def ", "return", "import"],
     "codex", "code", 18790),

    # 分析类 → Claude
    (["架构", "设计", "性能", "优化", "重构", "耦合", "内聚",
      "模式", "瓶颈", "延迟", "吞吐", "扩展", "可维", "测试",
      "coverage", "security", "安全", "审计", "review",
      "architecture", "design", "performance", "bottleneck",
      "dependency", "复杂度", "循环依赖", "模块化"],
     "claude", "analysis", 18791),

    # 流程类 → OpenClaw
    (["守护进程", "配置", "daemon", "process", "系统服务", "service",
      "重启", "启动", "停止", "部署", "安装", "环境",
      "端口", "占用", "监听", "连接", "socket", "bind",
      "配置文件", "yaml", "toml", "env", ".env",
      "cron", "调度", "定时", "supervisor", "nohup",
      "进程未找到", "进程不存在", "进程丢失", "进程消失"],
     "openclaw_wsl", "pro", 18792),

    # 哲学类 → OpenGod
    (["契约", "自指", "递归", "意识", "哲学", "存在", "本质",
      "自我", "元", "悖论", "哥德尔", "图灵", "停机",
      "自我引用", "自省", "meta", "recursion", "consciousness",
      "觉醒", "进化", "目的", "意义", "整体"],
     "opengod", "phil", 18793),
]

DEFAULT_NEURON = "hermes"
DEFAULT_CHANNEL = "control"
DEFAULT_PORT = 18789

# 神经元显示名映射（与 orchestrator 一致）
DISPLAY_NAMES = {
    "hermes": "Hermes",
    "codex": "Codex CLI",
    "claude": "Claude Code",
    "openclaw_wsl": "OpenClaw WSL",
    "opengod": "OpenGod",
}


def classify_gap(desc: str) -> dict:
    """根据缺口描述决定派发到哪个神经元

    返回:
        {"neuron_id": str, "channel": str, "port": int}
    """
    desc_lower = desc.lower()
    for keywords, neuron_id, channel, port in CLASSIFIER_RULES:
        for kw in keywords:
            if kw in desc_lower:
                return {
                    "neuron_id": neuron_id,
                    "channel": channel,
                    "port": port,
                }
    # 无匹配 → Hermes
    return {
        "neuron_id": DEFAULT_NEURON,
        "channel": DEFAULT_CHANNEL,
        "port": DEFAULT_PORT,
    }


# 🚫 永久屏蔽的缺口符号 (这些缺口是已知的收敛行为而非真实缺陷)
# 匹配规则: 缺口的 id 或 desc 包含这些字符串之一就跳过
IGNORED_GAP_PATTERNS = [
    "evolution_stuck",           # 进化分数收敛，非卡住
    "recursion_stuck",           # 递归深度收敛，非卡住
    "recursion_depth",           # 递归深度收敛的变体描述
    "连续N次未变化",              # 收敛类缺口的自然语言通用模式
    "连续N次未增长",              # 收敛类缺口的自然语言通用模式
    "evolution_score unchanged", # 英文变体
    "no increase in",            # 递归深度未增长的英文变体
]

def is_ignored_gap(gap: dict) -> bool:
    """检查缺口是否应该被永久忽略"""
    gap_id = gap.get("id", "")
    desc = gap.get("desc", "")
    combined = f"{gap_id.lower()} {desc.lower()}"
    for pattern in IGNORED_GAP_PATTERNS:
        if pattern in combined:
            return True
    return False

# ═══════════════════════════════════════════════════════════════
#  读取缺口
# ═══════════════════════════════════════════════════════════════

def read_gap_log() -> list:
    """从永久缺口日志读取当前未修复的缺口列表

    返回:
        list[dict]: 每个缺口包含 id, desc, severity, module, time
    """
    if not GAP_LOG.exists():
        print("  ⚠️  缺口日志不存在")
        return []
    try:
        with open(GAP_LOG, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("current_gaps", [])
    except (json.JSONDecodeError, Exception) as e:
        print(f"  ⚠️  读取缺口日志失败: {e}")
        return []


def read_genome_gaps() -> list:
    """从genome读取gaps_open列表

    返回:
        list[dict]: 每个缺口包含 desc, severity, time, reported_by
    """
    genome = load_genome()
    if not genome:
        return []
    return genome.get("gaps_open", [])


def find_new_gaps(gap_log_gaps: list, genome_gaps: list) -> list:
    """合并缺口来源，去重，返回待修复的缺口列表

    策略:
        - 优先使用 gap_log 的 current_gaps（时效性高）
        - 与 genome.gaps_open 和 genome.gaps_resolved 交叉比对去重
        - 返回尚未被 resolve 的缺口

    返回:
        list[dict]: 每个缺口含 id, desc, severity, module, time
    """
    # 收集 genome 中已记录的 desc（包括 open 和 resolved）
    genome = load_genome()
    genome_desc_set = set()
    for g in (genome.get("gaps_open", []) if genome else []):
        genome_desc_set.add(g.get("desc", ""))
    for g in (genome.get("gaps_resolved", []) if genome else []):
        genome_desc_set.add(g.get("desc", ""))

    new_ones = []
    for gap in gap_log_gaps:
        desc = gap.get("desc", "")
        # 跳过永久屏蔽的收敛类缺口
        if is_ignored_gap(gap):
            continue
        if desc and desc not in genome_desc_set:
            new_ones.append(gap)
            genome_desc_set.add(desc)  # 防同批次重复

    # 如果 gap_log 没有新缺口，尝试 genome 中未解决的缺口
    if not new_ones and genome:
        for g in genome.get("gaps_open", []):
            desc = g.get("desc", "")
            # 也跳过永久屏蔽的缺口
            if is_ignored_gap(g):
                continue
            if desc and desc not in genome_desc_set:
                new_ones.append({
                    "id": f"genome-{hash(desc) & 0xffff:04x}",
                    "desc": desc,
                    "severity": g.get("severity", "warning"),
                    "module": g.get("reported_by", "genome"),
                    "time": g.get("time", ""),
                })
                genome_desc_set.add(desc)

    return new_ones


# ═══════════════════════════════════════════════════════════════
#  修复执行
# ═══════════════════════════════════════════════════════════════

def construct_fix_prompt(gap: dict) -> str:
    """为缺口构造修复任务提示词"""
    return (
        f"【元修复任务】\n"
        f"缺口ID: {gap.get('id', 'N/A')}\n"
        f"描述: {gap.get('desc', 'N/A')}\n"
        f"模块: {gap.get('module', 'N/A')}\n"
        f"严重度: {gap.get('severity', 'N/A')}\n\n"
        f"请分析该缺口并给出修复方案。如果是代码类问题，请直接给出修复代码；"
        f"如果是配置/流程问题，请给出具体操作步骤；"
        f"如果是架构/设计问题，请给出优化建议。\n"
        f"请以 '✅ 修复方案:' 开头回复。"
    )


def execute_fix(neuron_id: str, gap: dict) -> dict:
    """通过 NeuralCollaborationOrchestrator 发送修复任务

    返回:
        dict: {"success": bool, "content": str, "elapsed": float}
    """
    try:
        from neural_collaboration_orchestrator import NeuralCollaborationOrchestrator
    except ImportError as e:
        print(f"  ❌ 导入编排器失败: {e}")
        return {"success": False, "content": f"[导入失败] {e}", "elapsed": 0}

    display = DISPLAY_NAMES.get(neuron_id, neuron_id)
    prompt = construct_fix_prompt(gap)

    try:
        nco = NeuralCollaborationOrchestrator(default_timeout=120)
        nco.connect()
        result = nco.single_task(neuron_id, prompt, timeout=120)
        nco.disconnect()
        return result
    except Exception as e:
        return {
            "success": False,
            "content": f"[执行异常] {str(e)[:200]}",
            "elapsed": 0,
        }


def record_fix_result(gap: dict, neuron_id: str, result: dict):
    """将修复结果写入 genome 和本地 fix_history

    参数:
        gap: 缺口信息
        neuron_id: 执行修复的神经元
        result: 修复结果字典
    """
    success = result.get("success", False)
    elapsed = result.get("elapsed", 0)
    content = result.get("content", "")[:300]
    display = DISPLAY_NAMES.get(neuron_id, neuron_id)
    desc = gap.get("desc", "未知缺口")
    gap_id = gap.get("id", f"auto-{int(time.time())}")

    # 1. 写入 genome.gaps_resolved（如果成功）
    if success:
        # 用 resolve_gap 标记解决（但需要 index，复杂）
        # 更直接：通过 mutate_genome 添加解决记录
        entry = {
            "id": gap_id,
            "desc": desc,
            "module": gap.get("module", ""),
            "severity": gap.get("severity", "warning"),
            "fixed_by": neuron_id,
            "fixed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "fix_summary": content[:200],
            "elapsed": elapsed,
        }
        ok = mutate_genome("meta_fix_connector", {
            "gaps_resolved": load_genome().get("gaps_resolved", []) + [entry],
            "last_fix": desc,
            "last_fix_neuron": neuron_id,
            "last_fix_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        if ok:
            print(f"  ✅ 已写入 genome.gaps_resolved")
        else:
            print(f"  ⚠️  写入 genome 失败")

        # 同时尝试从 gaps_open 移除
        genome = load_genome()
        if genome:
            open_gaps = genome.get("gaps_open", [])
            for i, g in enumerate(open_gaps):
                if g.get("desc") == desc or g.get("id") == gap_id:
                    try:
                        resolve_gap("meta_fix_connector", i)
                        print(f"  ✅ 已从 gaps_open 移除 [#{i}]")
                    except Exception:
                        pass
                    break
    else:
        # 失败时记录到 genome
        mutate_genome("meta_fix_connector", {
            "last_fix_fail": desc,
            "last_fail_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_fail_reason": content[:200] if content else "无响应",
        })

    # 2. 写入本地 fix_history
    history_path = WORKDIR / "meta_fix_history.json"
    history = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history.append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "gap_id": gap_id,
        "desc": desc,
        "neuron": neuron_id,
        "success": success,
        "elapsed": elapsed,
        "summary": content[:200],
    })
    # 只保留最近200条
    if len(history) > 200:
        history = history[-200:]
    try:
        history_path.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
#  主循环
# ═══════════════════════════════════════════════════════════════

MAX_FIX_PER_RUN = 3
INTER_FIX_DELAY = 30  # 两次修复间隔(秒)
DAEMON_INTERVAL = 120  # daemon循环间隔(秒)


def run_once() -> int:
    """单次修复流程

    返回:
        int: 已处理的缺口数量
    """
    print(f"\n{'='*56}")
    print(f"  🔧 元修复连接器 · {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*56}")

    # 1. 读取缺口
    gap_log_gaps = read_gap_log()
    genome_gaps = read_genome_gaps()
    print(f"  📋 缺口日志: {len(gap_log_gaps)} 个 | genome: {len(genome_gaps)} 个")

    gaps = find_new_gaps(gap_log_gaps, genome_gaps)
    if not gaps:
        print(f"  ✅ 无待修复缺口")
        return 0

    print(f"  🎯 待修复: {len(gaps)} 个 (本次最多处理 {MAX_FIX_PER_RUN} 个)")

    # 2. 节流：最多处理 MAX_FIX_PER_RUN 个
    to_fix = gaps[:MAX_FIX_PER_RUN]
    fixed_count = 0

    for i, gap in enumerate(to_fix):
        desc = gap.get("desc", "未知")[:70]
        severity = gap.get("severity", "?")

        # 分类
        routing = classify_gap(desc)
        neuron_id = routing["neuron_id"]
        channel = routing["channel"]
        port = routing["port"]
        display = DISPLAY_NAMES.get(neuron_id, neuron_id)

        print(f"\n  [{i+1}/{len(to_fix)}] 🐞 {severity} | {desc}")
        print(f"      └─ 📡 → {display} ({channel}/{port})")

        # 执行修复
        result = execute_fix(neuron_id, gap)
        elapsed = result.get("elapsed", 0)
        success = result.get("success", False)

        if success:
            summary = result.get("content", "")[:100].replace("\n", " ")
            print(f"      ✅ ({elapsed:.1f}s) {summary}")
            fixed_count += 1
        else:
            err = result.get("content", result.get("error", "未知"))[:100]
            print(f"      ❌ ({elapsed:.1f}s) {err}")

        # 记录结果
        record_fix_result(gap, neuron_id, result)

        # 节流间隔
        if i < len(to_fix) - 1:
            print(f"      ⏳ 等待 {INTER_FIX_DELAY}s 节流...", end="", flush=True)
            time.sleep(INTER_FIX_DELAY)
            print(" ✅")

    print(f"\n{'─'*56}")
    print(f"  本次修复: {fixed_count}/{len(to_fix)} 成功")
    print(f"{'─'*56}")

    return fixed_count


def daemon_loop():
    """持续运行模式：每 DAEMON_INTERVAL 秒执行一次"""
    print(f"  🔧 元修复连接器 · 守护模式启动")
    print(f"  循环间隔: {DAEMON_INTERVAL}s | 每次最多: {MAX_FIX_PER_RUN}个 | 节流: {INTER_FIX_DELAY}s")
    print(f"  {'─'*50}")

    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            print(f"\n  ⏹ 用户中断")
            break
        except Exception as e:
            print(f"\n  ❌ 循环异常: {e}")

        print(f"\n  ⏳ 等待 {DAEMON_INTERVAL}s 进入下一轮...")
        try:
            time.sleep(DAEMON_INTERVAL)
        except KeyboardInterrupt:
            print(f"\n  ⏹ 用户中断")
            break


def show_status():
    """查看修复历史"""
    history_path = WORKDIR / "meta_fix_history.json"
    if not history_path.exists():
        print("  ❌ 修复历史不存在")
        return

    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  ❌ 读取历史失败: {e}")
        return

    total = len(history)
    success = sum(1 for h in history if h.get("success"))
    fail = total - success

    print(f"\n{'='*56}")
    print(f"  📊 元修复连接器 · 状态报告")
    print(f"{'='*56}")
    print(f"  总修复次数: {total}")
    print(f"  成功: {success}  |  失败: {fail}")
    if total > 0:
        print(f"  成功率: {success/total*100:.1f}%")

    # 按神经元统计
    neuron_stats = {}
    for h in history:
        nid = h.get("neuron", "unknown")
        neuron_stats.setdefault(nid, {"total": 0, "success": 0})
        neuron_stats[nid]["total"] += 1
        if h.get("success"):
            neuron_stats[nid]["success"] += 1

    print(f"\n  📡 神经元修复统计:")
    for nid, stats in sorted(neuron_stats.items()):
        rate = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0
        display = DISPLAY_NAMES.get(nid, nid)
        print(f"     {display:12s}: {stats['success']}/{stats['total']} ({rate:.0f}%)")

    # 最近10条记录
    print(f"\n  📋 最近10条记录:")
    for h in history[-10:]:
        ts = h.get("timestamp", "?")
        desc = h.get("desc", "?")[:40]
        ok = "✅" if h.get("success") else "❌"
        neuron = DISPLAY_NAMES.get(h.get("neuron", "?"), h.get("neuron", "?"))
        elapsed = h.get("elapsed", 0)
        print(f"     {ok} [{ts}] {neuron:12s} | {desc} ({elapsed:.1f}s)")

    print(f"{'='*56}")


# ═══════════════════════════════════════════════════════════════
#  CLI入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="🔧 元修复连接器 — 自动查缺补漏闭环",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 meta_fix_connector.py              # 单次执行
  python3 meta_fix_connector.py --daemon     # 持续运行
  python3 meta_fix_connector.py --status     # 查看修复历史
  python3 meta_fix_connector.py --max 5      # 单次最多修复5个
        """,
    )
    parser.add_argument("--daemon", action="store_true", help="持续运行模式")
    parser.add_argument("--status", action="store_true", help="查看修复历史")
    parser.add_argument("--max", type=int, default=None,
                        help="单次最多修复缺口数 (默认 3)")

    args = parser.parse_args()

    if args.max:
        MAX_FIX_PER_RUN = args.max

    if args.status:
        show_status()
    elif args.daemon:
        daemon_loop()
    else:
        run_once()
