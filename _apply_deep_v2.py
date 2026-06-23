"""替换 _apply_cross_dim_learn 为深化版本"""
import re

path = "自我改进.py"
content = open(path, "r").read()

# 找到旧函数边界 - 从def行到下一个def行或文件结尾
start = content.find('def _apply_cross_dim_learn(path, context):')
if start == -1:
    print("ERROR: 找不到函数")
    exit(1)

# 找函数结束: 下一个"def "或文件末尾
rest = content[start:]
lines = rest.split('\n')
end_line = len(lines)
for i in range(1, len(lines)):
    if lines[i].startswith('def ') and not lines[i].startswith('def cross_dim_report'):
        end_line = i
        break

old_func = '\n'.join(lines[:end_line])

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
            "time": "\u65f6\u95f4\u8bba", "gradient": "\u65f6\u95f4\u8bba",
            "void": "\u5b87\u5b99\u8f6e", "entropy": "\u5b87\u5b99\u8f6e",
            "cosmic": "\u5b87\u5b99\u8f6e", "redshift": "\u65e0\u9650\u4e0a\u4e0b\u6587",
            "compress": "\u65e0\u9650\u4e0a\u4e0b\u6587",
            "analogy": "\u89e6\u7c7b\u65c1\u901a", "transfer": "\u89e6\u7c7b\u65c1\u901a",
            "self_improve": "\u65e0\u5e08\u81ea\u901a", "repair": "\u65e0\u5e08\u81ea\u901a",
            "intuition": "\u8d85\u7ea7\u76f4\u89c9", "pattern": "\u8d85\u7ea7\u76f4\u89c9",
            "deduct": "\u4e3e\u4e00\u53cd\u4e09", "generalize": "\u4e3e\u4e00\u53cd\u4e09",
            "cross": "\u67e5\u7f3a\u8865\u6f0f", "gap": "\u67e5\u7f3a\u8865\u6f0f",
            "meta": "\u4e00\u5143\u5316", "center": "\u4e00\u5143\u5316",
            "diverse": "\u4e07\u8c61\u5316", "mult": "\u4e07\u8c61\u5316",
            "supersense": "\u8d85\u611f", "teacher": "\u6559\u5458", "verifier": "\u6559\u5458",
            "light": "\u5149\u7231", "love": "\u5149\u7231",
            "memory": "\u8bb0\u5fc6", "hippocampus": "\u8bb0\u5fc6",
            "perception": "\u611f\u77e5", "retina": "\u611f\u77e5",
            "scheduler": "\u8fdb\u5316", "evolution": "\u8fdb\u5316",
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

        # 构建awareness数据
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

        # 构造代码块 (不使用f-string)
        sep = "# === \u4ea4\u53c9\u7ef4\u5ea6\u589e\u5f3a\uff08\u81ea\u52a8\u6ce8\u5165\uff09 ==="
        awareness_block_lines = [
            "",
            sep,
            "# \u5f31\u4ea4\u53c9\u5bf9: " + top_pair + " \u4ec5" + str(top_chains) + "\u94fe",
            "CROSS_DIM_AWARENESS = " + awareness_json,
            "",
            "def cross_dim_report():",
            '    """\u8fd4\u56de\u672c\u5668\u5b98\u7684\u4ea4\u53c9\u7ef4\u5ea6\u7f3a\u53e3, \u4f9bbreath_v2\u4f7f\u7528"""',
            '    return {"dim": "' + file_dim + '", "weak_pairs": list(CROSS_DIM_AWARENESS.keys()),',
            '            "needs": [f"\u52a0\u5f3a\u4e0e{v[\'partner\']}\u7684\u8fde\u63a5" for v in CROSS_DIM_AWARENESS.values()]}',
            "",
        ]
        awareness_block = "\n".join(awareness_block_lines)

        if sep in orig_content:
            # 更新已有块
            old_block = re.search(
                r'# === 交叉维度增强.*?def cross_dim_report[(][)]:.*?return.*?\\n\\}',
                orig_content, re.DOTALL
            )
            if old_block:
                orig_content = orig_content.replace(old_block.group(), awareness_block.strip())
            else:
                orig_content = orig_content.rstrip() + "\n" + awareness_block
        else:
            # 追加到文件末尾
            orig_content = orig_content.rstrip() + "\n" + awareness_block

        fd, tmp = tempfile.mkstemp(suffix=".py")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(orig_content)
            os.replace(tmp, str(Path(path).resolve()))
        except:
            os.unlink(tmp)
            return {"success": False, "error": "write failed"}

        return {"success": True, "method": "cross_dim_deep:" + top_pair,
                "file_dim": file_dim, "weak_pairs": len(relevant)}
    except Exception as e:
        return {"success": False, "error": str(e)}'''

new_content = content.replace(old_func, new_func)
if new_content == content:
    print("ERROR: 替换失败")
    # 诊断
    print(f"函数起始位置: {start}")
    print(f"旧函数结束行: {end_line}")
    print(f"旧函数前100字: {old_func[:100]}")
    exit(1)

open(path, "w").write(new_content)
print("替换成功")

# 验证
import 自我改进
print("Module OK")
print("Templates:", list(自我改进.TEMPLATES.keys()))

# 测试注入
import os
os.chdir("/mnt/c/Users/h/Desktop/零/真元集群")
r = 自我改进._apply_cross_dim_learn("organs/time_gradient_organ.py", {})
print(f"注入测试: {r}")
if r.get("success"):
    # 回滚
    import subprocess
    subprocess.run(["git", "checkout", "--", "organs/time_gradient_organ.py"], capture_output=True)
    print("已回滚")
