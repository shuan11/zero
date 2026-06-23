"""real_capability_probe.py — 真实能力探针
零·打破虚假自我评估循环

测量系统真实进化能力，替代关键词匹配的自增分数。
"""

import json, os, subprocess, time
from pathlib import Path

BASE = Path(__file__).resolve().parent

def measure_real_evolution() -> dict:
    """测量系统真实进化能力，返回0-1的分数和各维度数据"""
    
    score = 0.0
    details = {}
    
    # 1. 非呼吸提交数（排除 "breath_v2:" 和 "autonomic-burn" 提交）
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--since=24 hours ago", "--no-color"],
            capture_output=True, text=True, cwd=BASE, timeout=5
        )
        all_commits = [l for l in result.stdout.strip().split("\n") if l.strip()]
        real_commits = [c for c in all_commits 
                       if not c.startswith("breath_v2:") 
                       and "autonomic-burn" not in c]
        details["total_commits_24h"] = len(all_commits)
        details["real_commits_24h"] = len(real_commits)
        # 真实提交比例得分
        ratio = len(real_commits) / max(len(all_commits), 1)
        score += min(0.3, ratio * 0.3)  # 最高0.3
    except Exception as e:
        details["git_error"] = str(e)
    
    # 2. 维度健康度趋势（最近48小时的变化）
    try:
        radar_file = BASE / "dimension_radar.json"
        if radar_file.exists():
            data = json.loads(radar_file.read_text())
            dims = data.get("dimensions", {})
            healths = [v.get("health_score", 0) for v in dims.values() if isinstance(v, dict)]
            avg_health = sum(healths) / max(len(healths), 1)
            details["avg_dimension_health"] = round(avg_health, 3)
            score += min(0.2, avg_health * 0.2)  # 最高0.2
    except Exception as e:
        details["radar_error"] = str(e)
    
    # 3. 代码注入事件（24小时内新增的.py文件）
    try:
        result = subprocess.run(
            ["git", "diff", "--diff-filter=A", "--name-only", "--since=24 hours ago", "--", "*.py"],
            capture_output=True, text=True, cwd=BASE, timeout=5
        )
        new_files = [f for f in result.stdout.strip().split("\n") if f.strip()]
        details["new_py_files_24h"] = len(new_files)
        score += min(0.2, len(new_files) * 0.05)  # 每个新文件+0.05，最高0.2
    except Exception as e:
        details["new_files_error"] = str(e)
    
    # 4. 实际代码变更量（24小时内非呼吸文件的变更行数）
    try:
        # 排除已知的自动变更文件
        exclude_patterns = ["breath_v2.log", ".daemon_heartbeat", ".breath_mutation", 
                          "hippocampus_memory", "evolution_output/"]
        result = subprocess.run(
            ["git", "diff", "--since=24 hours ago", "--stat", "--no-color"],
            capture_output=True, text=True, cwd=BASE, timeout=5
        )
        lines = result.stdout.strip().split("\n")
        total_insertions = 0
        total_deletions = 0
        for line in lines:
            has_exclude = any(p in line for p in exclude_patterns)
            if has_exclude:
                continue
            import re
            nums = re.findall(r'(\d+) insertion', line)
            if nums:
                total_insertions += int(nums[0])
            nums = re.findall(r'(\d+) deletion', line)
            if nums:
                total_deletions += int(nums[0])
        details["real_insertions_24h"] = total_insertions
        details["real_deletions_24h"] = total_deletions
        # 净新增行数得分
        net = total_insertions - total_deletions
        score += min(0.2, max(0, net) * 0.001)  # 每净增1000行+0.1，最高0.2
    except Exception as e:
        details["diff_error"] = str(e)
    
    # 5. 器官系统活跃度（最近1小时内修改过的器官文件数）
    try:
        organs_dir = BASE / "organs"
        recent_organs = 0
        now = time.time()
        if organs_dir.exists():
            for f in organs_dir.glob("*.py"):
                if now - f.stat().st_mtime < 3600:
                    recent_organs += 1
        details["recent_organ_changes_1h"] = recent_organs
        score += min(0.1, recent_organs * 0.02)  # 最高0.1
    except Exception as e:
        details["organs_error"] = str(e)
    
    return {
        "score": round(min(1.0, score), 4),
        "details": details,
        "raw_score": round(score, 4),
        "timestamp": time.time()
    }


def get_honest_report() -> str:
    """生成可读的真实进化报告"""
    data = measure_real_evolution()
    d = data["details"]
    lines = [
        f"真实进化探针 | 分数={data['score']:.4f}",
        f"  真实提交: {d.get('real_commits_24h', '?')}/{d.get('total_commits_24h', '?')}",
        f"  维度健康均值: {d.get('avg_dimension_health', '?')}",
        f"  新增文件: {d.get('new_py_files_24h', '?')}",
        f"  净变更行: {d.get('real_insertions_24h', 0)-d.get('real_deletions_24h', 0):+d}",
        f"  器官变更: {d.get('recent_organ_changes_1h', '?')}/h",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(measure_real_evolution())
