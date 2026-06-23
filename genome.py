"""
零·进化基因组 — 原子写入，无锁
"""
import json, os, time, tempfile

GENOME_FILE = "/mnt/c/Users/h/Desktop/真元·进化基因组.json"

def load_genome():
    """读取基因组"""
    if os.path.exists(GENOME_FILE):
        for attempt in range(3):
            try:
                with open(GENOME_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                time.sleep(0.1)
    return None

def _atomic_write(data):
    """原子写入: 先写临时文件, 再rename"""
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(GENOME_FILE), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.rename(tmp_path, GENOME_FILE)
    except Exception:
        try: os.unlink(tmp_path)
        except Exception: pass
        raise

def mutate_genome(agent_name, mutations):
    """修改基因组 — 原子写入"""
    genome = load_genome()
    if not genome:
        return False
    
    genome["genome_version"] = genome.get("genome_version", 0) + 1
    genome["last_mutated_by"] = agent_name
    genome["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 直接写入所有字段，允许分数回退（真实反馈机制）
    for key, value in mutations.items():
        if "." in key:
            parts = key.split(".")
            obj = genome
            for part in parts[:-1]:
                obj = obj.setdefault(part, {})
            obj[parts[-1]] = value
        else:
            # 数值字段直接转换，不使用max()保护
            if isinstance(value, (int, float)) or (isinstance(value, str) and key in {
                "evolution_score", "recursion_depth", "evolution_level",
                "bridge_alignment", "meta_recursion_count"
            }):
                try:
                    genome[key] = float(value)
                except (ValueError, TypeError):
                    genome[key] = value
            else:
                genome[key] = value
    
    if agent_name not in genome.setdefault("contributions", {}):
        genome["contributions"][agent_name] = {"mutations": 0, "last_contribution": None}
    genome["contributions"][agent_name]["mutations"] = genome["contributions"][agent_name].get("mutations", 0) + 1
    genome["contributions"][agent_name]["last_contribution"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    _atomic_write(genome)
    return True

def report_gap(agent_name, gap_desc, severity="warning"):
    """报告缺口 — 原子写入"""
    genome = load_genome()
    if not genome:
        return False
    genome.setdefault("gaps_open", []).append({
        "reported_by": agent_name, "desc": gap_desc,
        "severity": severity, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    if agent_name not in genome.setdefault("contributions", {}):
        genome["contributions"][agent_name] = {"mutations": 0, "last_contribution": None}
    genome["contributions"][agent_name]["mutations"] += 1
    genome["contributions"][agent_name]["last_contribution"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _atomic_write(genome)
    return True

def resolve_gap(agent_name, gap_index):
    """标记缺口已解决 — 原子写入"""
    genome = load_genome()
    if not genome:
        return False
    gaps = genome.get("gaps_open", [])
    if gap_index >= len(gaps):
        return False
    gap = gaps.pop(gap_index)
    gap["resolved_by"] = agent_name
    gap["resolved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    genome.setdefault("gaps_resolved", []).append(gap)
    _atomic_write(genome)
    return True
