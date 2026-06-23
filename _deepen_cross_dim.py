"""深化cross_dim_self_learning模板：从注入注释升级为注入可执行代码"""

import json, os, tempfile, re
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
BOOST_FILE = CLUSTER / "cross_dim_boost.json"

# 文件名→维度映射
DIM_HINTS = {
    "time": "时间论", "gradient": "时间论", "void": "宇宙轮", "entropy": "宇宙轮",
    "cosmic": "宇宙轮", "redshift": "无限上下文", "compress": "无限上下文",
    "analogy": "触类旁通", "transfer": "触类旁通", "self_improve": "无师自通",
    "repair": "无师自通", "intuition": "超级直觉", "pattern": "超级直觉",
    "deduct": "举一反三", "generalize": "举一反三", "cross": "查缺补漏",
    "gap": "查缺补漏", "meta": "一元化", "center": "一元化", "diverse": "万象化",
    "mult": "万象化", "supersense": "超感", "perception": "超感",
    "teacher": "教员", "verifier": "教员",
    "light": "光爱", "love": "光爱", "memory": "记忆", "hippocampus": "记忆",
    "retina": "感知", "scheduler": "进化", "evolution": "进化",
    "bridge": "一元化", "constraint": "宇宙轮", "dignity": "光爱",
    "identity": "元神", "consciousness": "元神", "novel": "万象化",
    "compress": "无限上下文", "logic": "一元化",
}

FOCUS_HELPER = '''
def _cross_dim_focus():
    """读取交叉增强数据, 返回与当前器官维度相关的弱交叉对"""
    try:
        import json
        _bf = Path(__file__).resolve().parent.parent / "cross_dim_boost.json"
        if not _bf.exists(): return {}
        _data = json.loads(_bf.read_text())
        _boosts = _data.get("boosts", [])
        if not _boosts: return {}
        _fname = Path(__file__).resolve().name
        _dim_map = _get_dim_map()
        _file_dim = None
        for _kw, _dim in _dim_map.items():
            if _kw in _fname.lower():
                _file_dim = _dim
                break
        if not _file_dim: return {}
        _relevant = [_b for _b in _boosts if _b.get("dim1") == _file_dim or _b.get("dim2") == _file_dim]
        if not _relevant: return {}
        return {"cross_focus": _relevant[:3]}
    except:
        return {}

_cross_dim_map = {
'''


def _inject_cross_dim_code(filepath):
    """注入可执行的交叉增强代码到器官文件"""
    path = Path(filepath)
    if not path.exists():
        return {"success": False, "error": "file not found"}
    
    content = path.read_text()
    fname = path.name
    
    # 已经有_cross_dim_focus函数的就不重复注入
    if "_cross_dim_focus" in content:
        return {"success": False, "error": "already injected"}
    
    # 构建dim_map（只保留跟当前文件相关的条目以减小文件膨胀）
    file_dim = None
    relevant_dim_map = {}
    for kw, dim in DIM_HINTS.items():
        if kw in fname.lower():
            file_dim = dim
        relevant_dim_map[kw] = dim
    
    if not file_dim:
        # 尝试从关键词猜维度
        for kw, dim in DIM_HINTS.items():
            if kw in fname.lower():
                file_dim = dim
                break
    
    if not file_dim:
        return {"success": False, "error": f"unknown dimension for {fname}"}
    
    # 构建helper函数
    dim_items = "\n".join(f'    "{k}": "{v}",' for k, v in sorted(relevant_dim_map.items()))
    helper = f'''
def _cross_dim_focus():
    """读取交叉增强数据, 返回与当前器官维度({file_dim})相关的弱交叉对"""
    try:
        import json
        from pathlib import Path
        _bf = Path(__file__).resolve().parent.parent / "cross_dim_boost.json"
        if not _bf.exists(): return {{}}
        _data = json.loads(_bf.read_text())
        _boosts = _data.get("boosts", [])
        if not _boosts: return {{}}
        _fname = Path(__file__).resolve().name
        _dim_map = {{
{dim_items}
        }}
        _file_dim = None
        for _kw, _dim in _dim_map.items():
            if _kw in _fname.lower():
                _file_dim = _dim
                break
        if not _file_dim: return {{}}
        _relevant = [_b for _b in _boosts if _b.get("dim1") == _file_dim or _b.get("dim2") == _file_dim]
        if not _relevant: return {{}}
        return {{"cross_focus": _relevant[:3]}}
    except:
        return {{}}
'''
    
    # 追加helper到文件末尾
    new_content = content.rstrip() + "\n" + helper
    
    # 尝试在pulse()中注入调用
    # 查找def pulse( 后最近的 return {
    pulse_match = re.search(r'(def pulse\([^)]*\):.*?)(return\s*\{)', new_content, re.DOTALL)
    if pulse_match:
        # 在return前注入 _cross_dim_focus 调用
        before_return = pulse_match.group(1)
        return_stmt = pulse_match.group(2)
        # 找到return { 的位置
        return_pos = new_content.find(return_stmt, pulse_match.start())
        if return_pos > 0:
            # 在return前面加一行
            indent = "        "
            injection = f'{indent}_cdf = _cross_dim_focus()\n{indent}if _cdf: result.update(_cdf)\n{indent}'
            new_content = new_content[:return_pos] + injection + new_content[return_pos:]
    
    # 安全写入
    fd, tmp = tempfile.mkstemp(suffix=".py", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp, str(path))
    except:
        os.unlink(tmp)
        return {"success": False, "error": "write failed"}
    
    return {"success": True, "method": f"injected_cross_dim_code:{file_dim}"}


# === 执行：在匹配的器官文件中注入 ===
if not BOOST_FILE.exists():
    print("cross_dim_boost.json 不存在, 跳过")
    exit(0)

boosts = json.loads(BOOST_FILE.read_text()).get("boosts", [])
if not boosts:
    print("无弱交叉数据, 跳过")
    exit(0)

# 找到需要注入的器官文件
all_dims_in_boosts = set()
for b in boosts:
    all_dims_in_boosts.add(b.get("dim1", ""))
    all_dims_in_boosts.add(b.get("dim2", ""))

print(f"弱交叉涉及的维度: {all_dims_in_boosts}")

organs_dir = CLUSTER / "organs"
injected = 0
skipped = 0
errors = []

for f in sorted(organs_dir.glob("*_organ.py")):
    fname = f.name
    # 检查这个器官的维度是否在boost数据中
    file_dim = None
    for kw, dim in DIM_HINTS.items():
        if kw in fname.lower():
            file_dim = dim
            break
    if file_dim and file_dim in all_dims_in_boosts:
        result = _inject_cross_dim_code(f)
        if result.get("success"):
            injected += 1
            print(f"  ✅ {fname} ({file_dim})")
        else:
            if "already injected" not in result.get("error",""):
                skipped += 1
                print(f"  ➖ {fname}: {result['error']}")
    else:
        skipped += 1

print(f"\n结果: {injected} 注入, {skipped} 跳过")
