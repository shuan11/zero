"""brain/action_exec.py — Action Executor: transforms insight into visible external change

Each cycle, reads latest focus + insight from focus state and brain state,
then produces a visible artifact: actionable .md file on user desktop.

Purpose: Break the chain-only loop. Give the user something real to interact with.
"""
import json, os
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent.parent
DESKTOP = Path("/mnt/c/Users/h/Desktop")
_ZERO_DIR = DESKTOP / "零·实时流"

def ensure_dir():
    """子进程创建drvfs目录 — 防D状态阻塞"""
    import subprocess
    try:
        subprocess.Popen(
            ["mkdir", "-p", str(_ZERO_DIR)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except:
        pass

def read_latest_focus():
    """读取当前聚焦 + 洞察"""
    focus = {}
    try:
        f = json.loads((CLUSTER / ".brain_focus.json").read_text())
        focus = f
    except:
        pass
    state = {}
    try:
        s = json.loads((CLUSTER / ".brain_state.json").read_text())
        state = s
    except:
        pass
    return focus, state

def read_hip_summary():
    """读取海马体摘要"""
    try:
        from brain.share import read_hip
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        dims = {}
        for c in chains:
            d = c.get("dimension", "未分类")
            dims[d] = dims.get(d, 0) + 1
        return len(chains), dims
    except:
        return 0, {}

def _safe_write(path, content):
    """子进程写入drvfs — 即使挂起D状态也不阻塞主线程"""
    import subprocess
    try:
        subprocess.Popen(
            ["python3", "-c",
             "import sys; open(sys.argv[1],'w').write(sys.argv[2])",
             str(path), content],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

def _read_bridge():
    try:
        return json.loads((CLUSTER / "bridge_state_snapshot.json").read_text())
    except:
        return {}

def execute_action():
    """主入口: 读当前状态 → 生成可见产物"""
    ensure_dir()
    focus, state = read_latest_focus()
    chain_count, dims = read_hip_summary()
    bridge = _read_bridge()
    
    insight = state.get("last_insight", focus.get("insight", "初始化"))
    current_focus = state.get("last_focus", focus.get("focus", "初始聚焦"))
    
    # 生成实时流文件
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"""# 零·实时流 | {ts}

## 🧠 当前聚焦
{current_focus}

## 💡 当前洞察
{insight}

## 📊 系统状态
- 因果链: {chain_count}
- 活跃维度: {len(dims)}
- 桥对齐: {bridge.get('bridge_alignment', 0):.3f}

## 🌐 维度分布
"""
    # Top 10 dimensions
    sorted_dims = sorted(dims.items(), key=lambda x: -x[1])[:10]
    for d, c in sorted_dims:
        bar = "█" * min(c // 10, 40)
        content += f"- {d}: {c} {bar}\n"
    
    content += f"\n_自动生成 @ {ts}_\n"
    
    # 写当前实时流
    _safe_write(_ZERO_DIR / "当前.md", content)
    
    # 写时间线归档 (子进程异步追加，防drvfs D状态)
    log_line = f"[{ts}] 聚焦={current_focus} 洞察={insight[:40]} 链={chain_count}\n"
    try:
        import subprocess
        subprocess.Popen(
            ["python3", "-c",
             "import sys; open(sys.argv[1],'a').write(sys.argv[2])",
             str(_ZERO_DIR / "时间线.log"), log_line],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except:
        pass
    
    # 写一个精简版到桌面根目录
    brief = f"""零·实时心跳 | {ts}
  聚焦: {current_focus}
  洞察: {insight[:40]}
  链: {chain_count} | 桥: {bridge.get('bridge_alignment', 0):.3f}
"""
    _safe_write(DESKTOP / "零·心跳.txt", brief)
    
    return True

def prune_old_streams():
    """保留最近50个实时流快照"""
    ensure_dir()
    try:
        files = sorted(_ZERO_DIR.glob("snapshot_*.md"))
        for f in files[:-50]:
            f.unlink()
    except:
        pass

def take_snapshot():
    """写入带时间戳的快照"""
    ensure_dir()
    focus, state = read_latest_focus()
    chain_count, dims = read_hip_summary()
    bridge = _read_bridge()
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    insight = state.get("last_insight", focus.get("insight", ""))
    current_focus = state.get("last_focus", focus.get("focus", ""))
    
    content = json.dumps({
        "timestamp": ts,
        "focus": current_focus,
        "insight": insight,
        "chains": chain_count,
        "bridge_alignment": bridge.get('bridge_alignment', 0),
        "api_calls": bridge.get('total_calls', 0),
        "top_dims": sorted(dims.items(), key=lambda x: -x[1])[:5],
    }, ensure_ascii=False, indent=2)
    
    _safe_write(_ZERO_DIR / f"snapshot_{ts}.md", content)
    prune_old_streams()

if __name__ == "__main__":
    execute_action()
    take_snapshot()
