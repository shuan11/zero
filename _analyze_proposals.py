"""分析提案内容"""
import json

p = json.load(open("self_improve_proposals.bak.1780501985"))
print(f"总提案: {len(p)}")

cross_dim = [x for x in p if x["type"] == "cross_dim_boost"]
new_tmpl = [x for x in p if x["type"] == "new_self_learning_template"]

print(f"\n=== cross_dim_boost ({len(cross_dim)}条) ===")
print("第一条完整描述:")
print(cross_dim[0].get("description","")[:500])
print("\n所有字段:")
for k, v in cross_dim[0].items():
    print(f"  {k}: {str(v)[:200]}")

print(f"\n=== new_self_learning_template ({len(new_tmpl)}条) ===")
print("第一条完整描述:")
print(new_tmpl[0].get("description","")[:500])
print("\n所有字段:")
for k, v in new_tmpl[0].items():
    print(f"  {k}: {str(v)[:200]}")
