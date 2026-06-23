"""注入交叉维度增强上下文到breath_v2.py的_collect_all_contexts函数"""
path = "/mnt/c/Users/h/Desktop/零/真元集群/breath_v2.py"
content = open(path, "r").read()

before_return = '        return "\\n".join(ctx)'
insert_block = '''        # ═══ 交叉维度增强报告 ═══
        _cdb_f = CLUSTER / "cross_dim_boost.json"
        if _cdb_f.exists():
            try:
                import json
                _cdb_data = json.loads(_cdb_f.read_text())
                _weak = _cdb_data.get("weak_pairs", 0)
                if _weak > 0:
                    ctx.append(f"【交叉维度增强·{_weak}对弱交叉】")
                    for _bo in _cdb_data.get("boosts", [])[:5]:
                        ctx.append(f"  🜁 {_bo['pair']}: 仅{_bo['cross_chains']}链 -> +{_bo['boost']}")
            except:
                pass
        
'''

# Check if already injected
if "交叉维度增强报告" in content:
    print("already injected, skipping")
else:
    content = content.replace(before_return, insert_block + before_return)
    open(path, "w").write(content)
    print("injected OK")

# Verify
open(path).read().count("交叉维度增强报告")
