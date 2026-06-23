"""
gen_焦点维护.py — 焦点模块生命周期管理

扫描focus_*/gen_*模块, 标记实现状态, 清理过期stub.
"""

from pathlib import Path
from datetime import datetime, timedelta
from brain.share import write_chain, log

CLUSTER = Path(__file__).resolve().parent.parent
BRAIN = CLUSTER / "brain"
MAX_STUB_AGE_HOURS = 48

def pulse(cycle_num=0):
    msgs = []
    try:
        now = datetime.now()
        stubs = []
        implemented = 0
        for f in BRAIN.glob("focus_*.py"):
            if f.name == "focus_template.py":
                continue
            content = f.read_text(encoding="utf-8", errors="ignore")
            is_stub = 'TODO: 实现' in content or '待实现' in content or '#' not in content[100:]
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            age_hours = (now - mtime).total_seconds() / 3600
            if is_stub:
                stubs.append(f"{f.name}({age_hours:.0f}h)")
            else:
                implemented += 1
        total = implemented + len(stubs)
        if total:
            msgs.append(f"焦点维护: {implemented}/{total}已实现, {len(stubs)}待处理")
    except Exception as e:
        msgs.append(f"焦点维护: ! {e}")
    return msgs
