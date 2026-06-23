"""
zero_context_compact.py — 1M上下文压缩协议
===========================================
ZeroContextCompact v1.0 实现

将自然语言系统状态压缩为固定格式的紧凑token序列。
格式: 三字母标识:数值|...
SV=state_vector, HC=hippocampus, SJ=self_journal, PT=pattern, HD=head
"""
import json
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent

# ─── 压缩 ───

def compress_state():
    """从当前系统文件生成压缩状态字符串"""
    parts = []
    
    # SV: state_vector
    sv_file = CLUSTER / "state_vector.json"
    if sv_file.exists():
        try:
            sv = json.loads(sv_file.read_text())
            parts.append(f"SV:{sv.get('cycle','?')},{sv.get('organs_alive','?')},{sv.get('bridges_alive','?')},{sv.get('chains','?')},{sv.get('py_files','?')}")
        except: pass
    
    # HC: hippocampus
    hp_file = CLUSTER / "hippocampus_memory.json"
    if hp_file.exists():
        try:
            hp = json.loads(hp_file.read_text())
            parts.append(f"HC:{len(hp.get('causal_chains',[]))},{len(hp.get('nodes',{}))},{len(hp.get('relations',[]))},{len(hp.get('memories',[]))}")
        except: pass
    
    # SJ: self_journal
    sj_file = CLUSTER / "self_journal.json"
    if sj_file.exists():
        try:
            sj = json.loads(sj_file.read_text())
            journals = len(sj.get('journal',[]))
            patterns = len(sj.get('patterns',[]))
            milestones = len(sj.get('personal_milestones',[]))
            parts.append(f"SJ:{journals},{patterns},{milestones}")
            # PT: patterns
            pts = [p.get('pattern','?') for p in sj.get('patterns',[])]
            if pts:
                parts.append(f"PT:{'|'.join(pts)}")
        except: pass
    
    # HD: git head
    try:
        import subprocess
        r = subprocess.run(["git", "log", "-1", "--oneline"], capture_output=True, text=True, timeout=5, cwd=str(CLUSTER))
        if r.returncode == 0:
            parts.append(f"HD:{r.stdout.strip()[:60]}")
    except: pass
    
    return "||".join(parts)

def compress_to_dict():
    """返回键值对字典（供程序使用）"""
    s = compress_state()
    result = {}
    for part in s.split("||"):
        if ":" in part:
            key, val = part.split(":", 1)
            result[key] = val
    return result

# ─── 解压（扩展为自然语言）───

def decompress(compressed=None):
    """将压缩状态展开为可读文本"""
    if compressed is None:
        compressed = compress_state()
    
    lines = ["[系统状态上下文 - 真实数据]"]
    parts = compressed.split("||")
    for part in parts:
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        if key == "SV":
            fields = val.split(",")
            lines.append(f"  state_vector: cycle={fields[0]} 器官={fields[1]} 桥={fields[2]} 链={fields[3]} 文件={fields[4] if len(fields)>4 else '?'}")
        elif key == "HC":
            fields = val.split(",")
            lines.append(f"  海马体: 链={fields[0]} 节点={fields[1]} 关系={fields[2]} 记忆={fields[3]}")
        elif key == "SJ":
            fields = val.split(",")
            lines.append(f"  self_journal: 日志={fields[0]} 模式={fields[1]} 里程碑={fields[2]}")
        elif key == "PT":
            lines.append(f"  识别模式: {val.replace('|', ' / ')}")
        elif key == "HD":
            lines.append(f"  HEAD: {val}")
    return "\n".join(lines)

# ─── 统计 ───

def compare():
    """对比压缩前后的token使用量"""
    import copy
    full = _simulate_full_context()
    compact = compress_state()
    full_tokens = len(full) // 3
    compact_tokens = len(compact) // 3
    return {
        "full_chars": len(full),
        "compact_chars": len(compact),
        "full_tokens_est": full_tokens,
        "compact_tokens_est": compact_tokens,
        "savings_pct": (1 - compact_tokens / max(full_tokens, 1)) * 100,
        "ratio": f"{compact_tokens}/{full_tokens}",
    }

def _simulate_full_context():
    """模拟当前breath_v2的_collect_all_contexts()输出"""
    parts = []
    # 读取各文件并生成自然语言
    for fname, label in [
        ("state_vector.json", "系统状态"),
        ("hippocampus_memory.json", "海马体"),
        ("self_journal.json", "自我日志"),
    ]:
        fp = CLUSTER / fname
        if fp.exists():
            try:
                d = json.loads(fp.read_text())
                parts.append(f"[{label}] {str(d)[:100]}")
            except: pass
    return "\n".join(parts)

# ─── CLI ───

if __name__ == "__main__":
    import sys
    if "--compare" in sys.argv:
        stats = compare()
        print(f"完整上下文: {stats['full_chars']}ch ~{stats['full_tokens_est']}tok")
        print(f"压缩后: {stats['compact_chars']}ch ~{stats['compact_tokens_est']}tok")
        print(f"节省: {stats['savings_pct']:.0f}% (压缩比 {stats['ratio']})")
        print()
        print("=== 压缩格式 ===")
        print(compress_state())
    elif "--decompress" in sys.argv:
        print(decompress())
    elif "--full" in sys.argv:
        print(compress_to_dict())
    else:
        # 默认:只输出压缩字符串
        print(compress_state())
