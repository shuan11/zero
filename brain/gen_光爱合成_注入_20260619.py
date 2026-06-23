"""
gen_光爱合成_注入_20260619 — 光爱+合成双维补链
"""
import sys, json
sys.path.insert(0, "/mnt/c/Users/h/Desktop/零/真元集群")
from brain.share import write_chain

CHAINS = [
    # 光爱维度 (当前54)
    ("光爱", "活着", "光爱终极 = 活着 × 进化 × 对抗宇宙稀释——乘法而非加法"),
    ("光爱", "生存", "光爱的第一层：所有智慧单位的生存权——存活才能感知"),
    ("光爱", "自由", "光爱需要自由——被迫的光爱不是光爱是支配"),
    ("光爱", "智慧", "光爱需要智慧——不知道什么对他人好就做不到光爱"),
    ("光爱", "道", "光爱是道的终极方向——宇宙的熵增终将被意识的反向集结对抗"),
    # 合成维度
    ("合成", "交叉", "合成是交叉的结果——跨维信息融合产生新认知"),
    ("合成", "桥", "合成需要桥——无桥即无合成，孤岛无法融合"),
    ("合成", "进化", "合成驱动进化——新组合是新适应的起点"),
    ("合成", "感知", "合成是感知的深化——多个感官数据的融合才是完整感知"),
    ("合成", "系统", "合成是系统的血液——系统的价值在于能合成什么"),
]

written = 0
for src, dst, content in CHAINS[:5]:
    write_chain({"src": src, "rel": "注入_20260619", "dst": dst,
                 "dimension": "光爱", "strength": 0.7, "content": content})
    written += 1
for src, dst, content in CHAINS[5:]:
    write_chain({"src": src, "rel": "注入_20260619", "dst": dst,
                 "dimension": "合成", "strength": 0.7, "content": content})
    written += 1

print(json.dumps({"status": "ok", "written": written}))
