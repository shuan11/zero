"""应用自改进模板7深化: 从加注释改成注入CROSS_DIM_AWARENESS"""
import re

path = "自我改进.py"
content = open(path, "r").read()

old_func = '''def _apply_cross_dim_learn(path, context):
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
        
        comment_lines = []
        for b in relevant[:3]:
            comment_lines.append(f"# 交叉增强[{b['pair']}]: {b['reason']}")
        
        content = Path(path).read_text() + "\\n" + "\\n".join(comment_lines) + "\\n"
        
        fd, tmp = tempfile.mkstemp(suffix=".py")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, str(Path(path).resolve()))
        except:
            os.unlink(tmp)
            return {"success": False, "error": "write failed"}
        
        return {"success": True, "method": f"cross_dim_learn:{relevant[0]['pair']}"}
    except Exception as e:
        return {"success": False, "error": str(e)}'''

new_func = '''def _apply_cross_dim_learn(path, context):
    """应用交叉维度学习: 注入CROSS_DIM_AWARENESS数据结构和pulse()增强"""
    try:
        import os, tempfile, re
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
        
        content = Path(path).read_text()
        
        # 构建awareness数据
        import json as _json
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
        
        awareness_block = f'''
# === 交叉维度增强（自动注入） ===
# 弱交叉对: {top_pair} 仅{top_chains}链
CROSS_DIM_AWARENESS = {awareness_json}

def cross_dim_report():
    """返回本器官的交叉维度缺口, 供breath_v2使用"""
    return {{"dim": "{file_dim}", "weak_pairs": list(CROSS_DIM_AWARENESS.keys()),
            "needs": [f"加强与{{v['partner']}}的连接" for v in CROSS_DIM_AWARENESS.values()]}}
'''
        
        if "# === 交叉维度增强（自动注入） ===" in content:
            # 更新已有块
            old_block = re.search(
                '# === 交叉维度增强.*?def cross_dim_report[(][)]:.*?return.*?\\n\\}',
                content, re.DOTALL
            )
            if old_block:
                content = content.replace(old_block.group(), awareness_block.strip())
            else:
                content = content.rstrip() + "\\n" + awareness_block
        else:
            content = content.rstrip() + "\\n" + awareness_block
        
        fd, tmp = tempfile.mkstemp(suffix=".py")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, str(Path(path).resolve()))
        except:
            os.unlink(tmp)
            return {"success": False, "error": "write failed"}
        
        return {"success": True, "method": f"cross_dim_deep:{top_pair}",
                "file_dim": file_dim, "weak_pairs": len(relevant)}
    except Exception as e:
        return {"success": False, "error": str(e)}'''

if old_func in content:
    content = content.replace(old_func, new_func)
    open(path, "w").write(content)
    print("替换成功")
else:
    print("旧函数未找到，检查差异...")
    # 找差异
    import sys
    if '# 交叉增强' in content:
        print("  注释方式不同(无emoji)")
    if 'cross_dim_learn' in content:
        print("  原方法名存在")
    if 'def _apply_cross_dim_learn' in content:
        print("  函数存在")
    sys.exit(1)

# 验证
v = open(path).read()
if "cross_dim_deep" in v and "CROSS_DIM_AWARENESS" in v:
    print("✅ 新函数注入确认: cross_dim_deep + CROSS_DIM_AWARENESS")
else:
    print("⚠️ 验证失败")
    import sys
    sys.exit(1)

# 验证导入
import 自我改进
print("✅ 模块导入OK")
print(f"Templates: {list(自我改进.TEMPLATES.keys())}")
