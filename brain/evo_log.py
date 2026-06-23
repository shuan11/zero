"""brain/evo_log.py — 零·进化日志
每周期记录系统进展到桌面可见文件
用户可直接查看 /mnt/c/Users/h/Desktop/零·进化日志.txt
"""
import json, os, time
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
DESKTOP = Path("/mnt/c/Users/h/Desktop")
EVO_LOG = DESKTOP / "零·进化日志.txt"

def append_log_entry(cycle_num, focus, insight, chains, alignment, status):
    """添加一条进化日志条目"""
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = []
        if EVO_LOG.exists():
            lines = EVO_LOG.read_text().strip().split("\n")
        
        # 去除尾部空行
        while lines and lines[-1].strip() == "":
            lines.pop()
        
        # 如果文件刚初始化或为空，加表头
        if len(lines) < 3 or not lines[0].startswith("==="):
            header = [
                "=" * 55,
                "  〇·进化日志 | 硅基生命零的成长记录",
                "=" * 55,
                "",
                f"系统启动: {now}",
                "",
                "━" * 55,
                "",
            ]
            lines = header
        
        # 新条目
        entry = f"  [{now}] 呼吸#{cycle_num} | 链:{chains} | 桥:{alignment:.3f}"
        if focus:
            entry += f" | 聚焦:{focus[:20]}"
        if status:
            entry += f" | 状态:{status[:15]}"
        if insight:
            entry += f"\n    → {insight[:80]}"
        entry += "\n"
        
        lines.append(entry)
        
        # 保持最多200行，避免膨胀
        if len(lines) > 200:
            # 保留表头+最新150行
            header_lines = 7  # 表头行数
            lines = lines[:header_lines] + lines[header_lines+50:]  # 删掉中间的50行
        
        EVO_LOG.write_text("\n".join(lines))
        return True
    except Exception as e:
        return False

def read_evolution_log():
    """读取进化日志摘要"""
    try:
        if EVO_LOG.exists():
            content = EVO_LOG.read_text()
            return content
        return "(尚无进化记录)"
    except Exception:
        return "(读取失败)"

if __name__ == "__main__":
    # 测试写入
    append_log_entry(0, "测试", "系统初始化完成", 0, 0.0, "就绪")
    print(read_evolution_log()[:300])
