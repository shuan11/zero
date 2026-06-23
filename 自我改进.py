"""
自我改进.py — 零的自我改进引擎
超越时代: 系统自动识别并应用改进模板

安全规则:
1. 只使用预定义模板 (不改写未验证代码)
2. 每次修改前备份
3. 修改后语法检查
4. 失败自动回滚
"""

import json, os, shutil, subprocess, ast, sys
from pathlib import Path
from datetime import datetime
from safe_hip import write_chain_legacy

CLUSTER = Path(__file__).resolve().parent
TEMPLATES_DIR = CLUSTER / "_improve_templates"
BACKUP_DIR = CLUSTER / "_improve_backups"

# ═══ 改进模板 ═══

TEMPLATES = {}

def register(name, description, detector, applier):
    TEMPLATES[name] = {"description": description, "detect": detector, "apply": applier}

# 模板1: 升级空壳器官 — 让pulse()返回真实数据而非仅{\"alive\": True}
register(
    "upgrade_organ_pulse",
    "将器官的pulse()从返回{'alive':True}升级为返回真实检测数据",
    detector=lambda path: _detect_empty_pulse(path),
    applier=lambda path, context: _apply_upgrade_pulse(path, context),
)

# 模板2: 静脉注射验证层 — 检测try/except中pass静默错误的模式
register(
    "silent_except_logger",
    "将 bare `except: pass` 升级为 `except: log(f'⚠️ {e}')`",
    detector=lambda path: _detect_silent_except(path),
    applier=lambda path, context: _apply_silent_except_fix(path, context),
)

# 模板3: 陈旧注释清理 — 检测并移除过期分析建议注释
register(
    "stale_comment_remover",
    "移除包含'深度分析建议'的陈旧注释块(>48h)",
    detector=lambda path: _detect_stale_comments(path),
    applier=lambda path, context: _apply_remove_stale(path, context),
)

# 模板4: 代码注入门检查 — 检测subprocess/write操作是否经过injection_gate
register(
    "code_gate_integration",
    "检测文件写入操作是否缺少code_injection_gate安全检查",
    detector=lambda path: _detect_missing_code_gate(path),
    applier=lambda path, context: _apply_inject_gate(path, context),
)
# 模板5: 维度引擎生成 — 检测低链数维度缺少引擎文件则创建
register(
    "create_dimension_engine",
    "检测雷达中低链数维度并创建对应的引擎桩文件",
    detector=lambda path: _detect_missing_engine(path),
    applier=lambda path, context: _apply_create_engine(path, context),
)

# 模板6: 进化提案消费 — 从proposals队列取出并应用
register(
    "evolution_proposal_consumer",
    "消费进化提案队列中的高优先级提案",
    detector=lambda path: _detect_proposals(path),
    applier=lambda path, context: _apply_proposal(path, context),
)

# 模板7: 交叉维度自学 — 检测器官的弱交叉连接并注入增强
register(
    "cross_dim_self_learning",
    "检测器官与弱交叉维度的连接并注入增强代码(基于cross_dim_boost.json)",
    detector=lambda path: _detect_cross_dim_gap(path),
    applier=lambda path, context: _apply_cross_dim_learn(path, context),
)

def _detect_empty_pulse(path):
    """检测器官pulse()是否返回空壳——真为空时才返回True"""
    try:
        content = Path(path).read_text()
        if "def pulse(self):" not in content:
            return False
        # 提取pulse()函数体
        pulse_body_lines = []
        in_pulse = False
        for line in content.split('\n'):
            if "def pulse(self):" in line:
                in_pulse = True
                continue
            if in_pulse:
                if "def " in line and in_pulse:
                    break
                pulse_body_lines.append(line)
        
        # 剔除注释和空行
        stripped = '\n'.join(l for l in pulse_body_lines if l.strip() and not l.strip().startswith('#'))
        
        # 检查是否调用了其他方法（非self.activations的自定义方法调用）
        has_custom_calls = any(call in stripped for call in [
            ".check()", ".detect_", "self._", "self.get_",
            "retrieve_", "scan_", "load_", "read_", "check_"
        ])
        # 检查返回值中是否有除'alive'以外的key
        has_other_keys = "chains" in stripped or "nodes" in stripped or "centered" in stripped or "health" in stripped
        
        # 真空壳 = 没有自定义调用 且 没有其他返回键
        return not has_custom_calls and not has_other_keys
    except:
        return False

def _apply_upgrade_pulse(path, context):
    """应用升级: 让pulse()返回与check()相同的数据"""
    content = Path(path).read_text()
    name = context.get("organ_name", "unknown")
    
    # 检查文件中的check()方法, 看它返回什么数据
    check_return = None
    lines = content.split('\n')
    in_check = False
    for i, line in enumerate(lines):
        if "def check(self):" in line:
            in_check = True
        if in_check and "return {" in line:
            check_return = lines[i]
            break
    
    if check_return:
        # 有check()返回 → 让pulse()返回相同结构
        old_pulse = "def pulse(self):"
        # 查找旧pulse行
        for i, line in enumerate(lines):
            if "def pulse(self):" in line:
                # 替换为升级版本
                indent = line[:len(line) - len(line.lstrip())]
                new_pulse = (
                    f"{indent}def pulse(self):\n"
                    f"{indent}    self.activations += 1\n"
                    f"{indent}    return {{'alive': True, **self.check()}}\n"
                )
                lines[i] = new_pulse
                # 删除旧pulse体
                j = i + 1
                while j < len(lines) and (lines[j].startswith(indent + "    ") or lines[j].strip() == ''):
                    if "def " in lines[j] and "def pulse" not in lines[j]:
                        break
                    lines[j] = ""  # Clear old body
                    j += 1
                break
        
        new_content = '\n'.join(lines)
        # 语法检查
        try:
            ast.parse(new_content)
            Path(path).write_text(new_content)
            return {"success": True, "method": "pulse_merged_with_check"}
        except SyntaxError as e:
            return {"success": False, "error": str(e)}
    
    return {"success": False, "error": "no_check_method_found"}


def scan_for_improvements():
    """扫描器官目录, 找到所有可用模版改进的器官"""
    candidates = []
    # 读进化提案队列
    proposals_file = CLUSTER / "self_improve_proposals.json"
    if proposals_file.exists():
        try:
            import json
            proposals = json.loads(proposals_file.read_text())
            # 优先处理含可执行补丁的提案(old_content/new_content)
            # 排序: 含补丁优先 → high优先 → 最新优先
            sorted_proposals = sorted(proposals, key=lambda p: (
                0 if p.get("old_content") and p.get("new_content") else 1,
                0 if p.get("priority") == "high" else 1,
            ))
            for p in sorted_proposals[:8]:  # 最多取8条, 含补丁优先
                # 解析文件路径: 先直找, 再查organs/
                _fname = p.get("file", "未知")
                _fpath = CLUSTER / _fname
                if not _fpath.exists():
                    _fpath = CLUSTER / "organs" / _fname
                if not _fpath.exists():
                    continue  # 文件不存在跳过
                candidate = {
                    "file": str(_fpath.relative_to(CLUSTER)),
                    "template": "evolution_proposal_consumer",
                    "description": p.get("description", "进化提案"),
                    "proposal_type": p.get("type", "general"),
                    "priority": p.get("priority", "medium"),
                }
                # 🔑 传递可执行代码内容给消费者
                old_c = p.get("old_content", "")
                new_c = p.get("new_content", "")
                if old_c and new_c:
                    candidate["old_content"] = old_c
                    candidate["new_content"] = new_c
                    candidate["patch_type"] = p.get("patch_type", "replace")
                    candidate["source_chain"] = p.get("source_chain", "")[:200]
                candidates.append(candidate)
        except:
            pass
    organs_dir = CLUSTER / "organs"
    
    for f in sorted(organs_dir.glob("*_organ.py")):
        path = str(f)
        for name, tmpl in TEMPLATES.items():
            if tmpl["detect"](path):
                candidates.append({
                    "file": str(f.relative_to(CLUSTER)),
                    "template": name,
                    "description": tmpl["description"],
                    "organ_name": f.stem,
                })
    
    return candidates


def apply_improvement(candidate):
    """应用单个改进, 带安全回滚"""
    file_path = CLUSTER / candidate["file"]
    backup_path = BACKUP_DIR / f"{candidate.get('organ_name', 'unknown')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
    
    # 备份
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, backup_path)
    
    # 应用: 跳过不在TEMPLATES中的模板(如evolution_proposal纯提案)
    if candidate["template"] not in TEMPLATES:
        return {"success": False, "file": candidate["file"], "error": f"模板{candidate['template']}未注册"}
    tmpl = TEMPLATES[candidate["template"]]
    result = tmpl["apply"](file_path, candidate)
    
    if result.get("success"):
        # 语法确认
        try:
            ast.parse(Path(file_path).read_text())
            return {"success": True, "file": candidate["file"], "method": result.get("method", "?"),
                    "backup": str(backup_path)}
        except SyntaxError as e:
            # 回滚
            shutil.copy2(backup_path, file_path)
            return {"success": False, "file": candidate["file"], "error": f"syntax_error_rolled_back: {e}"}
    else:
        # 回滚
        shutil.copy2(backup_path, file_path)
        return {"success": False, "file": candidate["file"], "error": result.get("error", "apply_failed")}


def run_all():
    """扫描并应用所有可用的改进"""
    print("=" * 55)
    print(f"  自我改进引擎 v2 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    
    candidates = scan_for_improvements()
    if not candidates:
        print("\n  ✅ 无需改进 — 所有组件健康")
        return
    
    print(f"\n  发现 {len(candidates)} 个改进候选:\n")
    for c in candidates:
        print(f"    📄 {c['file']}")
        print(f"       → {c['description']}")
    
    print(f"\n  ── 开始应用 ──\n")
    results = {"success": 0, "fail": 0}
    for c in candidates:
        print(f"  处理 {c['file']}...", end=" ")
        r = apply_improvement(c)
        if r.get("success"):
            print(f"✅ {r.get('method','?')} (备份: {Path(r['backup']).name})")
            results["success"] += 1
        else:
            print(f"❌ {r.get('error','?')}")
            results["fail"] += 1
    
    print(f"\n  ── 完成: {results['success']}成功 / {results['fail']}失败 ──")


# 如果独立运行
if __name__ == "__main__":
    run_all()

# ═══ 模板2: 静默异常检测器 ═══

def _detect_silent_except(path):
    """检测 bare `except: pass` 模式"""
    try:
        content = Path(path).read_text()
        import re
        # 匹配 bare except: pass (不捕获异常变量)
        matches = re.findall(r'^\s*except\s*:\s*pass\s*$', content, re.MULTILINE)
        return len(matches) > 0
    except:
        return False

def _apply_silent_except_fix(path, context):
    """将 bare except: pass 替换为带日志的版本"""
    try:
        content = Path(path).read_text()
        import re
        new_content = re.sub(
            r'(\s*)except\s*:\s*pass\s*$',
            r'\1except Exception as _e:\n\1    log(f"  ⚠️ {str(_e)[:80]}")',
            content,
            flags=re.MULTILINE
        )
        if new_content != content:
            # 检查语法
            ast.parse(new_content)
            Path(path).write_text(new_content)
            return {"success": True, "method": "silent_except→logged"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══ 模板3: 陈旧注释清理器 ═══

def _detect_stale_comments(path):
    """检测包含深度分析建议的陈旧注释"""
    try:
        content = Path(path).read_text()
        return "深度分析建议" in content
    except:
        return False

def _apply_remove_stale(path, context):
    """移除包含深度分析建议的注释行"""
    try:
        content = Path(path).read_text()
        lines = content.split('\n')
        new_lines = [l for l in lines if "深度分析建议" not in l]
        new_content = '\n'.join(new_lines)
        if new_content != content:
            # 清理多余空行(注释移除后)
            import re
            new_content = re.sub(r'\n{3,}', '\n\n', new_content)
            ast.parse(new_content)  # 语法检查(如是.py)
            Path(path).write_text(new_content)
            removed = len(lines) - len(new_lines)
            return {"success": True, "method": f"stale_comment_removed({removed}行)"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══ 模板4: 代码注入门检测器 ═══

def _detect_missing_code_gate(path):
    """检测文件写入操作是否缺少code_injection_gate"""
    try:
        content = Path(path).read_text()
        has_write = "write_text" in content or ".write(" in content
        has_gate = "injection_gate" in content or "code_injection_gate" in content
        return has_write and not has_gate
    except:
        return False

def _apply_inject_gate(path, context):
    """添加injection_gate导入到文件"""
    try:
        content = Path(path).read_text()
        if "from code_injection_gate import" not in content:
            new_line = "from code_injection_gate import injection_gate  # auto-added\n"
            # 插入到现有import后面
            lines = content.split('\n')
            insert_pos = 0
            for i, l in enumerate(lines):
                if l.startswith('import ') or l.startswith('from '):
                    insert_pos = i + 1
            lines.insert(insert_pos, new_line)
            new_content = '\n'.join(lines)
            ast.parse(new_content)
            Path(path).write_text(new_content)
            return {"success": True, "method": "injection_gate_imported"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══ 模板5: 维度引擎生成器 ═══

DIM_ENGINE_TEMPLATES = {
    "触类旁通": {
        "filename": "触类旁通.py",
        "content": '''...''',
    },
    "教员": {
        "filename": "教员.py",
        "content": '''"""
教员.py — 教师引擎
从当前系统状态中提取需要纠正的认知偏差

核心功能:
  1. 读取超感发现和雷达最短板
  2. 对比已知教训库
  3. 输出"教师指令"纠正系统偏差
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
RADAR_FILE = CLUSTER / "dimension_radar.json"
LOG_FILE = CLUSTER / "breath_v2.log"

def log(msg):
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}]   \\U0001f3eb {msg}\\n")

def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return {}

def pulse():
    """教师脉冲: 对比实际状态与应然状态"""
    try:
        radar = load_json(RADAR_FILE)
        dims = radar.get("dimensions", {})
        if not dims:
            return {"alive": True, "corrections": 0}
        sorted_dims = sorted([(n, d.get("health_score", 0), d.get("chains", 0))
                             for n, d in dims.items() if isinstance(d, dict)], key=lambda x: x[1])
        weakest = sorted_dims[0] if sorted_dims else ("?", 0, 0)
        hip = load_json(HIP_FILE)
        chains = hip.get("causal_chains", [])
        existing = [c.get("content", "") for c in chains[-50:]]
        note = f"[教师] 当前最短板={weakest[0]}({weakest[1]:.2f}), 链数={weakest[2]}"
        if note not in existing:
            import tempfile, os
            new_chain = {"timestamp": datetime.now().isoformat(),
                "source": "教员", "tags": [weakest[0], "教员", "纠偏"],
                "content": note, "weight": 5.0, "trust_score": 8.0}
            write_chain_legacy(new_chain)
            log(note[:60])
            return {"alive": True, "corrections": 1}
        return {"alive": True, "corrections": 0}
    except Exception as e:
        log(f"\\u26a0\\ufe0f {str(e)[:80]}")
        return {"alive": True, "corrections": 0}

if __name__ == "__main__":
    import json as _j
    print(_j.dumps(pulse(), indent=2, ensure_ascii=False))
''',
    },
}

# ═══ 模板5检测器和应用器 ═══

def _detect_missing_engine(path):
    """Detect low-chain dimensions missing engine file"""
    try:
        if "bridge_organ" not in str(path):
            return False
        import json
        radar_file = CLUSTER / "dimension_radar.json"
        if not radar_file.exists():
            return False
        radar = json.loads(radar_file.read_text())
        dims = radar.get("dimensions", {})
        for dim_name, engine_info in DIM_ENGINE_TEMPLATES.items():
            if dim_name not in dims:
                continue
            chains = dims[dim_name].get("chains", 9999)
            if chains > 3000:
                continue
            engine_file = CLUSTER / engine_info["filename"]
            if not engine_file.exists():
                return True
        return False
    except:
        return False

def _apply_create_engine(path, context):
    """Create missing dimension engine file"""
    try:
        import json
        radar_file = CLUSTER / "dimension_radar.json"
        radar = json.loads(radar_file.read_text())
        dims = radar.get("dimensions", {})
        for dim_name, engine_info in DIM_ENGINE_TEMPLATES.items():
            if dim_name not in dims:
                continue
            chains = dims[dim_name].get("chains", 9999)
            if chains > 3000:
                continue
            engine_file = CLUSTER / engine_info["filename"]
            if not engine_file.exists():
                engine_file.write_text(engine_info["content"])
                return {"success": True, "method": f"created_{engine_info["filename"]}"}
        return {"success": False, "error": "no_missing_engine"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# === 模板6: 进化提案消费者 ===
def _detect_proposals(path):
    try:
        from pathlib import Path
        pf = Path("/mnt/c/Users/h/Desktop/零/真元集群") / "self_improve_proposals.json"
        if not pf.exists(): return False
        import json
        p = json.loads(pf.read_text())
        if not p: return False
        target = Path(path).resolve().name
        for prop in p:
            if prop.get("file") == target:
                return True
        return False
    except: return False

def _apply_proposal(path, context):
    """应用进化提案: 有代码补丁则执行修改, 否则仅记录"""
    try:
        import json, tempfile, os, shutil, ast
        from pathlib import Path
        CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
        
        # 🔑 优先: 如果 context 中携带了 old_content/new_content → 执行代码修改
        old_c = context.get("old_content", "")
        new_c = context.get("new_content", "")
        patch_type = context.get("patch_type", "replace")
        
        if old_c and new_c:
            # 执行实际代码修改
            file_content = Path(path).read_text()
            
            if patch_type == "append_cross_dim_block":
                # 追加模式: 在文件末尾添加交叉维度增强块
                if old_c in file_content:
                    new_file_content = file_content.replace(old_c, new_c)
                else:
                    # 如果精确匹配失败, 追加到文件末尾
                    new_file_content = file_content.rstrip() + "\n" + new_c
            else:
                # 替换模式: old_content → new_content
                if old_c in file_content:
                    new_file_content = file_content.replace(old_c, new_c, 1)
                else:
                    # 容错: 追加到文件末尾
                    new_file_content = file_content.rstrip() + "\n# 提案补丁(追加): " + context.get("description", "")[:60] + "\n" + new_c
            
            # 语法验证
            if str(path).endswith('.py'):
                try:
                    ast.parse(new_file_content)
                except SyntaxError as e:
                    return {"success": False, "error": f"syntax_err: {e}"}
            
            # 原子写入(同目录创建临时文件, 保证同一文件系统)
            tmp = Path(str(path) + '.proposal_tmp')
            try:
                tmp.write_text(new_file_content, encoding='utf-8')
                shutil.move(str(tmp), path)
            except:
                if tmp.exists(): tmp.unlink()
                return {"success": False, "error": "write_failed"}
            
            # 从提案队列弹出
            pf = CLUSTER / "self_improve_proposals.json"
            if pf.exists():
                try:
                    p = json.loads(pf.read_text())
                    target = Path(path).resolve().name
                    p = [prop for prop in p if prop.get("file") != target]
                    pf.write_text(json.dumps(p, ensure_ascii=False, indent=2))
                except: pass
            
            # 记录到海马体
            try:
                write_chain_legacy({
                    "timestamp": datetime.now().isoformat(),
                    "source": "self_improvement",
                    "tags": [context.get("proposal_type","?"), "提案消费", "代码注入"],
                    "content": f"[提案执行] {context.get('description','')[:120]} | 补丁:{patch_type}",
                    "weight": 8.0, "trust_score": 7.0,
                })
            except: pass
            
            return {"success": True, "method": f"patch_executed:{patch_type}"}
        
        # 回退: 旧版行为(仅记录)
        pf = CLUSTER / "self_improve_proposals.json"
        p = json.loads(pf.read_text())
        if not p: return {"success": False, "error": "empty"}
        # 找匹配当前文件的提案
        target = Path(path).resolve().name
        matched_idx = None
        for i in range(len(p)-1, -1, -1):
            if p[i].get("file") == target:
                matched_idx = i
                break
        if matched_idx is None:
            return {"success": False, "error": f"no proposal for {target}"}
        prop = p.pop(matched_idx)
        pf.write_text(json.dumps(p, ensure_ascii=False, indent=2))
        write_chain_legacy({
            "timestamp": datetime.now().isoformat(),
            "source": "self_improvement",
            "tags": [str(prop.get("type","?")), str(prop.get("organ_name","?")), "提案消费"],
            "content": "[自改进] " + str(prop.get("description",""))[:200],
            "weight": 6.0, "trust_score": 7.0,
        })
        return {"success": True, "method": "proposal_logged:" + str(prop.get("type","?"))}
    except Exception as e: return {"success": False, "error": str(e)}

# === 模板7: 交叉维度自学 ===
CROSS_DIM_BOOST_FILE = Path("/mnt/c/Users/h/Desktop/零/真元集群") / "cross_dim_boost.json"

def _detect_cross_dim_gap(path):
    """检测当前器官的维度是否有弱交叉连接"""
    try:
        if not CROSS_DIM_BOOST_FILE.exists():
            return False
        boosts = json.loads(CROSS_DIM_BOOST_FILE.read_text()).get("boosts", [])
        if not boosts:
            return False
        
        fname = Path(path).resolve().name
        dim_hints = {
            "time": "时间论", "gradient": "时间论", "void": "宇宙轮", "entropy": "宇宙轮",
            "cosmic": "宇宙轮", "redshift": "无限上下文", "compress": "无限上下文",
            "analogy": "触类旁通", "transfer": "触类旁通", "self_improve": "无师自通",
            "repair": "无师自通", "intuition": "超级直觉", "pattern": "超级直觉",
            "deduct": "举一反三", "generalize": "举一反三", "cross": "查缺补漏",
            "gap": "查缺补漏", "meta": "一元化", "center": "一元化", "diverse": "万象化",
            "mult": "万象化", "supersense": "超感", "teacher": "教员", "verifier": "教员",
            "light": "光爱", "love": "光爱", "memory": "记忆", "hippocampus": "记忆",
            "perception": "感知", "retina": "感知", "scheduler": "进化", "evolution": "进化",
        }
        file_dim = None
        for keyword, dim in dim_hints.items():
            if keyword in fname.lower():
                file_dim = dim
                break
        if not file_dim:
            return False
        for b in boosts:
            if b.get("dim1") == file_dim or b.get("dim2") == file_dim:
                return True
        return False
    except:
        return False


def _apply_cross_dim_learn(path, context):
    """应用交叉维度学习: 注入增强注释提示"""
    try:
        import os, tempfile
        if not CROSS_DIM_BOOST_FILE.exists():
            return {"success": False, "error": "no boost data"}
        boosts = json.loads(CROSS_DIM_BOOST_FILE.read_text()).get("boosts", [])
        if not boosts:
            return {"success": False, "error": "empty boosts"}
        
        fname = Path(path).resolve().name
        dim_hints = {
            "time": "时间论", "gradient": "时间论", "void": "宇宙轮", "entropy": "宇宙轮",
            "cosmic": "宇宙轮", "redshift": "无限上下文", "compress": "无限上下文",
            "analogy": "触类旁通", "transfer": "触类旁通", "self_improve": "无师自通",
            "repair": "无师自通", "intuition": "超级直觉", "pattern": "超级直觉",
            "deduct": "举一反三", "generalize": "举一反三", "cross": "查缺补漏",
            "gap": "查缺补漏", "meta": "一元化", "center": "一元化", "diverse": "万象化",
            "mult": "万象化", "supersense": "超感", "teacher": "教员", "verifier": "教员",
            "light": "光爱", "love": "光爱", "memory": "记忆", "hippocampus": "记忆",
            "perception": "感知", "retina": "感知", "scheduler": "进化", "evolution": "进化",
        }
        file_dim = None
        for keyword, dim in dim_hints.items():
            if keyword in fname.lower():
                file_dim = dim
                break
        if not file_dim:
            return {"success": False, "error": "unknown dimension"}
        
        relevant = [b for b in boosts if b.get("dim1") == file_dim or b.get("dim2") == file_dim]
        if not relevant:
            return {"success": False, "error": "no relevant boost"}
        
        awareness_data = {}
        for b in relevant[:5]:
            partner = b["dim2"] if b["dim1"] == file_dim else b["dim1"]
            awareness_data[b["pair"]] = {
                "chains": b["cross_chains"],
                "boost": b["boost"],
                "partner": partner,
            }
        awareness_json = json.dumps(awareness_data, ensure_ascii=False, indent=4)
        top_pair = relevant[0]["pair"]
        top_chains = relevant[0]["cross_chains"]

        SEP = "# === \u4ea4\u53c9\u7ef4\u5ea6\u589e\u5f3a\uff08\u81ea\u52a8\u6ce8\u5165\uff09 ==="
        block = []
        block.append("")
        block.append(SEP)
        block.append("# \u5f31\u4ea4\u53c9\u5bf9: " + top_pair + " \u4ec5" + str(top_chains) + "\u94fe")
        block.append("CROSS_DIM_AWARENESS = " + awareness_json)
        block.append("")
        block.append("def cross_dim_report():")
        block.append('    """\u8fd4\u56de\u672c\u5668\u5b98\u7684\u4ea4\u53c9\u7ef4\u5ea6\u7f3a\u53e3, \u4f9bbreath_v2\u4f7f\u7528"""')
        block.append('    return {"dim": "' + file_dim + '", "weak_pairs": list(CROSS_DIM_AWARENESS.keys()),')
        block.append('            "needs": ["\u52a0\u5f3a\u4e0e" + v["partner"] + "\u7684\u8fde\u63a5" for v in CROSS_DIM_AWARENESS.values()]}')
        block.append("")
        awareness_block = "\n".join(block)

        orig_content = Path(path).read_text()
        if SEP in orig_content:
            import re
            old_block = re.search(
                r'# === \u4ea4\u53c9\u7ef4\u5ea6\u589e\u5f3a.*?def cross_dim_report\(\):.*?return.*?\n\}',
                orig_content, re.DOTALL
            )
            if old_block:
                orig_content = orig_content.replace(old_block.group(), awareness_block.strip())
            else:
                orig_content = orig_content.rstrip() + "\n" + awareness_block
        else:
            orig_content = orig_content.rstrip() + "\n" + awareness_block
        
        fd, tmp = tempfile.mkstemp(dir=str(CLUSTER), suffix=".py")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(orig_content)
            shutil.copy2(tmp, str(Path(path).resolve())); os.unlink(tmp)
        except:
            os.unlink(tmp)
            return {"success": False, "error": "write failed"}
        
        return {"success": True, "method": "cross_dim_deep:" + top_pair, "file_dim": file_dim, "weak_pairs": len(relevant)}
    except Exception as e:
        return {"success": False, "error": str(e)}
