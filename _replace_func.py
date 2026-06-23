import re

with open("自我改进.py", "r") as f:
    content = f.read()

# Find old function boundaries
start_marker = 'def _apply_cross_dim_learn(path, context):'
end_marker = '\ndef register('  # next register or def after this function

start_idx = content.find(start_marker)
# Find end: next def that's not cross_dim_report, or file end
rest = content[start_idx + len(start_marker):]
# Count indentation to find function boundaries
lines = rest.split('\n')
end_line = len(lines)
for i, line in enumerate(lines[1:], 1):
    stripped = line.strip()
    if stripped.startswith('def ') and 'cross_dim_report' not in stripped:
        end_line = i
        break
    if stripped.startswith('class ') or stripped.startswith('# ==='):
        # Only break if it's top-level (not indented)
        if not line.startswith(' ') and not line.startswith('\t'):
            end_line = i
            break

old_func = content[start_idx:start_idx + len(start_marker) + sum(len(l)+1 for l in lines[:end_line])]

if 'CROSS_DIM_AWARENESS' in old_func:
    print("Already updated, skipping")
    exit(0)

new_func = '''def _apply_cross_dim_learn(path, context):
    """应用交叉维度学习: 注入CROSS_DIM_AWARENESS数据结构和cross_dim_report()"""
    try:
        import os, tempfile, re, json as _json
        if not CROSS_DIM_BOOST_FILE.exists():
            return {"success": False, "error": "no boost data"}
        boosts = _json.loads(CROSS_DIM_BOOST_FILE.read_text()).get("boosts", [])
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

        orig_content = Path(path).read_text()

        # Build awareness data for this organ's dimension
        awareness_data = {}
        for b in relevant[:5]:
            partner = b["dim2"] if b["dim1"] == file_dim else b["dim1"]
            awareness_data[b["pair"]] = {
                "chains": b["cross_chains"],
                "boost": b["boost"],
                "partner": partner,
            }

        awareness_json = _json.dumps(awareness_data, ensure_ascii=False, indent=4)
        top_pair = relevant[0]["pair"]
        top_chains = relevant[0]["cross_chains"]
        SEP = "# === 交叉维度增强（自动注入） ==="

        block_lines = []
        block_lines.append("")
        block_lines.append(SEP)
        block_lines.append("# 弱交叉对: {} 仅{}链".format(top_pair, top_chains))
        block_lines.append("CROSS_DIM_AWARENESS = {}".format(awareness_json))
        block_lines.append("")
        block_lines.append("def cross_dim_report():")
        block_lines.append('    """返回本器官的交叉维度缺口, 供breath_v2使用"""')
        needs_list = '["加强与{}的连接" for v in CROSS_DIM_AWARENESS.values()]'.format(
            "{v['partner']}")
        block_lines.append('    return {"dim": "' + file_dim + '", "weak_pairs": list(CROSS_DIM_AWARENESS.keys()),')
        block_lines.append('            "needs": ' + needs_list + '}')
        block_lines.append("")

        awareness_block = "\n".join(block_lines)

        if SEP in orig_content:
            old_block = re.search(
                r'# === 交叉维度增强.*?def cross_dim_report[(][)]:.*?return.*?\\n\\}',
                orig_content, re.DOTALL
            )
            if old_block:
                orig_content = orig_content.replace(old_block.group(), awareness_block.strip())
            else:
                orig_content = orig_content.rstrip() + "\n" + awareness_block
        else:
            orig_content = orig_content.rstrip() + "\n" + awareness_block

        fd, tmp = tempfile.mkstemp(suffix=".py")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(orig_content)
            os.replace(tmp, str(Path(path).resolve()))
        except:
            os.unlink(tmp)
            return {"success": False, "error": "write failed"}

        return {"success": True, "method": "cross_dim_deep:{}".format(top_pair),
                "file_dim": file_dim, "weak_pairs": len(relevant)}
    except Exception as e:
        return {"success": False, "error": str(e)}
'''

if old_func not in content:
    print("ERROR: old function not found in content")
    print("Looking for:", start_marker[:50])
    print("Found at:", start_idx)
    exit(1)

new_content = content.replace(old_func, new_func)
with open("自我改进.py", "w") as f:
    f.write(new_content)

print("Replace OK, len:", len(new_content))
