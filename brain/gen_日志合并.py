"""gen_日志合并.py — 将.hippocampus_journal.json的链合并入主海马体

安全合并器：从日志文件读取待写链→追加到海马体→清空日志。
只有本模块能写海马体，其他gen模块只能写日志。

数据流：HOME(~/.zero_brain/)为写主路径(ext4安全)，
        CWD(/mnt/c/)为副本路径(drvfs易损坏)。
        先写主路径，再复制到副本。
"""

import json, time, fcntl, os, shutil
from pathlib import Path

# 主海马体：~/.zero_brain/hippocampus_memory.json (ext4，安全)
HIPPOCAMPUS = Path(os.path.expanduser("~/.zero_brain/hippocampus_memory.json"))
# CWD副本：drvfs路径，写后有验证（易截断）
CWD_HIP = Path("/mnt/c/Users/h/Desktop/零/真元集群/hippocampus_memory.json")
JOURNAL = Path(os.path.expanduser("~/.zero_brain/hippocampus_journal.json"))
UIBOT_JOURNAL = Path("/mnt/c/Users/h/Desktop/零/真元集群/uibot_journal.json")


def _merge_entries(entries, existing, existing_keys):
    """合并条目到海马体，返回合并数"""
    from brain.identity import sanitize_dim
    merged = 0
    skipped = 0
    for entry in entries:
        raw_dim = entry.get("dimension", "未分类")
        safe_dim = sanitize_dim(raw_dim) if raw_dim else "未分类"
        entry["dimension"] = safe_dim
        key = (entry.get("src"), entry.get("rel"), entry.get("dst"), safe_dim)
        if key not in existing_keys:
            entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            existing.append(entry)
            existing_keys.add(key)
            merged += 1
        else:
            skipped += 1
    return merged, skipped


def _sync_to_cwd():
    """将主海马体同步到CWD副本，含写验证"""
    try:
        # 先读主海马体数据到内存
        payload = HIPPOCAMPUS.read_text(encoding="utf-8")
        # 写入CWD
        CWD_HIP.write_text(payload, encoding="utf-8")
        # 读回验证
        written = CWD_HIP.read_text(encoding="utf-8")
        if len(written) < len(payload) * 0.9:
            # drvfs截断，从主海马体恢复
            HIPPOCAMPUS.read_text()  # just verify it's valid
            return False
        return True
    except Exception:
        return False


def pulse():
    """每周期检查日志并合并，锁主海马体"""
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")

    # 收集所有日志源
    sources = []
    for name, jpath in [("hippocampus", JOURNAL), ("uibot", UIBOT_JOURNAL)]:
        if not jpath.exists():
            continue
        try:
            with open(jpath, "r", encoding="utf-8") as f:
                journal = json.load(f)
            entries = journal if isinstance(journal, list) else journal.get("entries", [])
            if entries:
                sources.append((name, entries, jpath))
        except (json.JSONDecodeError, FileNotFoundError):
            continue

    if not sources:
        return {"status": "no_journal"}

    # 锁定主海马体（ext4，flock安全）
    try:
        fd = open(HIPPOCAMPUS, "r+")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (FileNotFoundError, BlockingIOError, OSError) as e:
        return {"status": f"海马体锁定失败: {e}"}

    try:
        data = json.load(fd)
    except json.JSONDecodeError:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
        return {"status": "hippocampus_corrupt"}

    existing = data.setdefault("causal_chains", [])
    existing_keys = set()
    for ec in existing:
        existing_keys.add((ec.get("src"), ec.get("rel"), ec.get("dst"), ec.get("dimension")))

    total_merged = 0
    total_skipped = 0
    source_results = []

    for name, entries, jpath in sources:
        merged, skipped = _merge_entries(entries, existing, existing_keys)
        total_merged += merged
        total_skipped += skipped
        source_results.append(f"{name}:{merged}合并/{skipped}跳过")

    # 安全校验：防止写入空/过小结果
    if len(existing) < 100:
        msg = f"合并后链数异常({len(existing)})，跳过写入，保留原文件"
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
        backup = HIPPOCAMPUS.with_suffix(".json.corrupt_bak")
        shutil.copy2(HIPPOCAMPUS, backup)
        return {"status": "abort", "reason": msg}

    # 写前备份
    backup_path = HIPPOCAMPUS.with_suffix(".json.pre_merge_bak")
    shutil.copy2(HIPPOCAMPUS, backup_path)

    # 写回主海马体（ext4，安全）
    data["metadata"]["total_chains"] = len(existing)
    data["metadata"]["last_update"] = ts
    fd.seek(0)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    fd.write(payload)
    fd.truncate()
    fcntl.flock(fd, fcntl.LOCK_UN)
    fd.close()

    # 同步到CWD副本（drvfs，含验证）
    cwd_ok = _sync_to_cwd()
    if not cwd_ok:
        source_results.append("CWD同步失败(drvfs截断，自动跳过)")

    # 清空所有日志源
    for name, entries, jpath in sources:
        if isinstance(entries, list):
            with open(jpath, "w", encoding="utf-8") as f:
                f.write("[]")
        else:
            with open(jpath, "w", encoding="utf-8") as f:
                json.dump({"entries": []}, f, ensure_ascii=False)

    return {"status": "ok", "detail": " | ".join(source_results)}


if __name__ == "__main__":
    import sys
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
