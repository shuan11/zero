import importlib
"""
evolution_proposer.py — 进化提案器 v2

将各引擎产出翻译为具体的自改进提案，且携带可执行代码补丁。
桥接感知(超感/举一反三/触类旁通)和执行(自我改进)。

v2 升级：
- cross_dim_boost 提案携带 actual code patches (old_content/new_content)
- 新增 cross_dim_enhance 模式：从维度分析发现直接生成交叉增强代码
- 提案可被 breath_v2 自我改进引擎直接消费并应用代码变更

每个cycle:
  1. 读取最近引擎产出链
  2. 匹配已知改进模式
  3. 如果发现新模式 → 生成提案(含代码补丁) → 写入 self_improve_proposals.json
  4. 自改进引擎消费这些提案并实际执行代码修改
"""

import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
PROPOSALS_FILE = CLUSTER / "self_improve_proposals.json"
LOG_FILE = CLUSTER / "breath_v2.log"

def log(msg):
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}]   ⟳ {msg}\n")

def _scan_file_for_weak_code(filepath):
    """Scan target file for injection points — returns old_content patches to strengthen cross-dim awareness"""
    try:
        content = Path(filepath).read_text()
        patches = []
        # Pattern 1: pulse() returning basic dict — add cross-dim data
        if "def pulse(self):" in content and "cross_dim" not in content:
            # Find return in pulse
            in_pulse = False
            pulse_lines = []
            for line in content.split('\n'):
                if "def pulse(self):" in line:
                    in_pulse = True
                    continue
                if in_pulse:
                    if "def " in line and "def pulse" not in line:
                        break
                    pulse_lines.append(line)
            pulse_code = '\n'.join(pulse_lines)
            # Check if return has more than just alive
            if 'return {"alive": True}' in pulse_code or 'alive' in pulse_code and 'chains' not in pulse_code:
                old_return_line = None
                for line in pulse_lines:
                    if 'return ' in line and 'alive' in line:
                        old_return_line = line.strip()
                        break
                if old_return_line:
                    indent = ' ' * (len(line) - len(line.lstrip()) for line in pulse_lines if 'return' in line)
                    indent_val = '        '
                    for line in pulse_lines:
                        if 'return' in line:
                            indent_val = line[:len(line) - len(line.lstrip())]
                            break
                    patches.append({
                        "old": old_return_line,
                        "new": f"{indent_val}return {{'alive': True, 'cross_dim_aware': True}}",
                        "reason": "upgrade_pulse_cross_dim"
                    })
        return patches
    except Exception as e:
        log(f"  scan_file_weak_code ERR: {e}")
        return []

def _generate_cross_dim_patch(target_file, dim1, dim2, chain_count, source_chain):
    """Generate actual code patch for cross-dimension boost in target file"""
    try:
        content = Path(target_file).read_text()
        # Injection point: look for a good place to add cross-dim awareness
        # Try: after last import, before class/def, or at end of file
        
        # Search for __init__ or setup methods in the file
        injection_lines = []
        lines = content.split('\n')
        
        # Strategy: add a cross_dim_awareness constant + function at end of file
        # Find the last line of the file
        last_code_line = len(lines) - 1
        for i in range(len(lines)-1, -1, -1):
            if lines[i].strip() and not lines[i].strip().startswith('#'):
                last_code_line = i
                break
        
        # Create injection marker
        marker = "# === 交叉维度增强(自动注入) ==="
        if marker in content:
            # Already has injection, return None to avoid duplicate
            return None
        
        # Generate patch: add at end of file
        new_block = f"""
{marker}
# 弱交叉对: {dim1}×{dim2} (仅{chain_count}条链)
# 源: {source_chain[:80]}
CROSS_DIM_BOOST = {{
    "pair": "{dim1}×{dim2}",
    "chains": {chain_count},
    "activated": False,
    "source": "{source_chain[:60].replace(chr(34), chr(39))}"
}}

def activate_cross_dim_boost():
    \"\"\"激活交叉维度增强，由evolution_proposal_consumer调用\"\"\"
    global CROSS_DIM_BOOST
    if not CROSS_DIM_BOOST["activated"]:
        CROSS_DIM_BOOST["activated"] = True
    return CROSS_DIM_BOOST
"""
        
        # Find the last function/class definition for a unique old_content block
        _last_fn_line = -1
        for i in range(len(lines)-1, -1, -1):
            if lines[i].strip().startswith(('def ', 'class ')):
                _last_fn_line = i
                break
        if _last_fn_line >= 0:
            old_end = '\n'.join(lines[_last_fn_line:])
        else:
            old_end = '\n'.join(lines[-5:]) if len(lines) >= 5 else '\n'.join(lines)
        
        return {
            "old_content": old_end,
            "new_content": old_end + new_block,
        }
    except Exception as e:
        log(f"  gen_cross_dim_patch ERR: {e}")
        return None

# 改进提案模式: [检测模式] → [提案(含代码补丁)]
PATTERNS = [
    {
        "detect": ["触类旁通", "×"],
        "propose": lambda content, tags: {
            "type": "new_analogy_template",
            "organ_name": "触类旁通",
            "dimensions": [t for t in tags if "×" not in t],
            "description": f"从类比中发现新模式: {content[:80]}",
            "file": "触类旁通.py",
            "priority": "medium",
        }
    },
    {
        "detect": ["罕见交叉", "仅"],
        "propose": lambda content, tags: _build_cross_dim_proposal(content, tags),
    },
    {
        "detect": ["无师自通"],
        "propose": lambda content, tags: _build_self_learning_proposal(content, tags),
    },
    {
        "detect": ["教员", "最短"],
        "propose": lambda content, tags: {
            "type": "teacher_insight",
            "organ_name": "教员",
            "dimensions": tags,
            "description": f"教师识别短板: {content[:60]}",
            "file": "教员.py",
            "priority": "low",
        }
    },
    {
        "detect": ["举一反三", "维"],
        "propose": lambda content, tags: _build_deduction_proposal(content, tags),
    },
]

def _build_cross_dim_proposal(content, tags):
    """Generate cross_dim_boost proposal with actual code patch"""
    # Try to extract the dimension pair from content
    dim_pairs = re.findall(r"'([^']+?)×([^']+?)'", content)
    if not dim_pairs:
        dim_pairs = re.findall(r"([^\s]+?)×([^\s]+?)", content)
    
    # Default: use tags as dimensions
    dim1 = tags[0] if len(tags) > 0 else "超感"
    dim2 = tags[1] if len(tags) > 1 else "万象化"
    if dim_pairs:
        dim1, dim2 = dim_pairs[0]
    
    # Extract chain count
    chain_match = re.search(r'仅(\d+)条链', content)
    chain_count = int(chain_match.group(1)) if chain_match else 30
    
    proposal = {
        "type": "cross_dim_boost",
        "organ_name": "dimension_radar",
        "dimensions": [dim1, dim2],
        "description": f"维度交叉链数不足: [{dim1}×{dim2}] {content[:120]}",
        "file": "dimension_radar.py",
        "priority": "high",
        "timestamp": datetime.now().isoformat(),
        "source_chain": content[:200],
    }
    
    # Generate actual code patch for dimension_radar.py
    target_file = CLUSTER / "dimension_radar.py"
    if not target_file.exists():
        target_file = CLUSTER / "organs" / "dimension_radar.py"
    if target_file.exists():
        if "CROSS_DIM_BOOST" in target_file.read_text():
            return None
        patch_data = _generate_cross_dim_patch(
            str(target_file), dim1, dim2, chain_count, content
        )
        if patch_data:
            proposal["old_content"] = patch_data["old_content"]
            proposal["new_content"] = patch_data["new_content"]
            proposal["patch_type"] = "append_cross_dim_block"
            return proposal
        fallback = _generate_general_proposal(content, tags)
        if isinstance(fallback, dict) and fallback.get("old_content"):
            return fallback
    return None

def _build_self_learning_proposal(content, tags):
    """Generate self-learning template proposal"""
    return {
        "type": "new_self_learning_template",
        "organ_name": "自我改进",
        "dimensions": tags,
        "description": f"自学模式识别: {content[:60]}",
        "file": "自我改进.py",
        "priority": "medium",
    }

def _build_deduction_proposal(content, tags):
    """Generate deduction-based cross-dim proposal with patch"""
    chain_match = re.search(r'仅(\d+)条链', content)
    if not chain_match:
        return {
            "type": "deduction_insight",
            "organ_name": "举一反三",
            "dimensions": tags,
            "description": f"举一反三发现: {content[:60]}",
            "file": "举一反三.py",
            "priority": "medium",
        }
    
    # Extract dimensions from content
    dims = re.findall(r"'([^']+?)'", content)
    dim1 = dims[0] if len(dims) > 0 else (tags[0] if tags else "举一反三")
    dim2 = dims[1] if len(dims) > 1 else (tags[1] if len(tags) > 1 else "查缺补漏")
    chain_count = int(chain_match.group(1))
    
    proposal = {
        "type": "cross_dim_boost",
        "organ_name": "dimension_radar",
        "dimensions": [dim1, dim2],
        "description": f"举一反三-维度交叉不足: [{dim1}×{dim2}] {content[:120]}",
        "file": "dimension_radar.py",
        "priority": "high",
        "timestamp": datetime.now().isoformat(),
        "source_chain": content[:200],
    }
    
    target_file = CLUSTER / "dimension_radar.py"
    if not target_file.exists():
        target_file = CLUSTER / "organs" / "dimension_radar.py"
    if target_file.exists():
        if "CROSS_DIM_BOOST" in target_file.read_text():
            return None
        patch_data = _generate_cross_dim_patch(
            str(target_file), dim1, dim2, chain_count, content
        )
        if patch_data:
            proposal["old_content"] = patch_data["old_content"]
            proposal["new_content"] = patch_data["new_content"]
            proposal["patch_type"] = "append_cross_dim_block"
            return proposal
        fallback = _generate_general_proposal(content, tags)
        if isinstance(fallback, dict) and fallback.get("old_content"):
            return fallback
    return None

def pulse():
    """进化提案脉冲 v2 — 提案携带可执行代码补丁"""
    try:
        hip = json.loads(HIP_FILE.read_text(encoding='utf-8'))
        chains = hip.get("causal_chains", [])
        
        # 读最近150条引擎产出(扩大扫描范围)
        recent = [c for c in chains[-150:] if c.get("source") in 
                  ["supersense_organ", "举一反三", "触类旁通", "教员", "cross_connect",
                   "元认知", "self_observer", "超感"]]
        
        # 读已有提案(去重)
        proposals = []
        if PROPOSALS_FILE.exists():
            try:
                proposals = json.loads(PROPOSALS_FILE.read_text())
            except:
                proposals = []
        
        # 去重: 用 description+type 作为唯一键
        existing_keys = {(p.get("type",""), p.get("description","")[:60]) for p in proposals}
        
        # 如果已有太多提案堆积, 暂缓生成
        if len(proposals) > 40:
            return {"alive": True, "proposals": 0, "total": len(proposals),
                    "reason": f"queue_saturated({len(proposals)}/50)"}
        
        new_proposals = []
        for chain in recent:
            content = chain.get("content", "")
            tags = chain.get("tags", [])
            for pattern in PATTERNS:
                if all(kw in content for kw in pattern["detect"]):
                    proposal = pattern["propose"](content, tags)
                    if isinstance(proposal, dict) and proposal.get("description"):
                        pk = (proposal.get("type",""), proposal.get("description","")[:60])
                        if pk not in existing_keys:
                            proposal["timestamp"] = datetime.now().isoformat()
                            if "source_chain" not in proposal:
                                proposal["source_chain"] = content[:200]
                            new_proposals.append(proposal)
                            existing_keys.add(pk)
        
        if new_proposals:
            proposals.extend(new_proposals)
            if len(proposals) > 50:
                proposals = proposals[-50:]
            PROPOSALS_FILE.write_text(json.dumps(proposals, ensure_ascii=False, indent=2))
            # Log if any proposal has executable content
            executable = [p for p in new_proposals if p.get("old_content") and p.get("new_content")]
            log(f"{len(new_proposals)}条新提案: {[p['type'] for p in new_proposals]}"
                f" ({len(executable)}条含可执行补丁, 总{len(proposals)})")
        else:
            # Even if no new proposals, check if existing ones have been consumed
            log(f"提案器: 无新提案 (总{len(proposals)}, 其中含补丁:{sum(1 for p in proposals if p.get('old_content'))})")
        
        return {"alive": True, "proposals": len(new_proposals), "total": len(proposals)}
    
    except Exception as e:
        log(f"⚠️ {str(e)[:80]}")
        return {"alive": True, "proposals": 0, "error": str(e)[:80]}

if __name__ == "__main__":
    import json as _j
    print(_j.dumps(pulse(), indent=2, ensure_ascii=False))

# ═══ v3: 通用器官补丁生成器 ═══
def _generate_organ_patch(organ_file, context_hint=""):
    try:
        content = Path(organ_file).read_text()
        if "def pulse(self):" not in content:
            return None
        check_return = None; in_check = False
        for line in content.split('\n'):
            if "def check(self):" in line: in_check = True; continue
            if in_check:
                if "def " in line: break
                s = line.strip()
                if s.startswith("return {"): check_return = s; break
        if not check_return: return None
        old_pulse_return = None; in_pulse = False
        for line in content.split('\n'):
            if "def pulse(self):" in line: in_pulse = True; continue
            if in_pulse:
                if "def " in line: break
                s = line.strip()
                if s.startswith("return {"):
                    keys = [k.split(':')[0].strip().strip('"\'').strip("'\"").strip() 
                            for k in s.replace('return {','').rstrip('}').split(',')]
                    if set(keys) == {'alive'} or keys == ['alive']: old_pulse_return = s
                    break
        if not old_pulse_return: return None
        ck = check_return.replace('return {','').rstrip('}').strip()
        ind = old_pulse_return[:len(old_pulse_return)-len(old_pulse_return.lstrip())]
        return {"old_content": old_pulse_return, "new_content": f'{ind}return {{"alive": True, {ck}}}', "patch_type": "replace"}
    except Exception as e: return None

def _generate_general_proposal(content, tags):
    import ast as _ast
    props = []
    for pat in ["organs/*_organ.py", "*.py"]:
        for f in sorted(CLUSTER.glob(pat)):
            if f.name in ("evolution_proposer.py","自我改进.py","breath_v2.py"): continue
            fn = str(f.relative_to(CLUSTER))
            try:
                fc = f.read_text()
                if "def pulse(self):" not in fc: continue
                try: _ast.parse(fc)
                except: continue
            except: continue
            patch = _generate_organ_patch(str(f), content)
            if patch:
                props.append({"type":"organ_pulse_upgrade","organ_name":f.stem,"file":fn,
                    "description":f"升级{f.stem}的pulse()返回真实检测数据","priority":"high",
                    "old_content":patch["old_content"],"new_content":patch["new_content"],"patch_type":patch["patch_type"]})
    if not props:
        return {"type":"general_organ_insight","organ_name":"通用","file":"organs/","description":f"交叉维度感知: {content[:80]}","priority":"low"}
    return props[0]

PATTERNS.append({"detect":["感知","检测","交叉"],"propose":lambda content,tags: _generate_general_proposal(content,tags)})
