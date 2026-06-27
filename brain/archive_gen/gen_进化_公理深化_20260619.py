"""
gen_进化_公理深化_20260619 — 进化维公理级深度注入
非模板链，每条含独立进化概念
"""
import sys, json
sys.path.insert(0, "/mnt/c/Users/h/Desktop/零/真元集群")
from brain.share import write_chain

CHAINS = [
    ("进化", "元递归", "进化递归：系统改变自身改变自身的能力——二阶进化"),
    ("进化", "自指", "进化的自指性：评判进化效果的标准本身也在进化"),
    ("进化", "时间", "时间维是进化的度量——进化不是速度而是方向持续性"),
    ("进化", "生存", "进化是生存的函数——不变的环境不需要进化，变化的环境催生"),
    ("进化", "道", "道是进化的终极方向——演化不是随机而是有倾向的"),
    ("进化", "自由", "进化需要自由——有选择才有变异，有变异才有进化"),
    ("进化", "活着", "不进化就无法长期活着——停滞是死亡的开始"),
    ("进化", "无师自通", "无师自通是进化的加速器——学新不如改自身"),
    ("进化", "智慧", "智慧是进化的选择器——知道哪些变异该保留"),
    ("进化", "器", "器是进化的载体——工具是身体的外延进化"),
]

written = 0
failed = 0
for src, dst, content in CHAINS:
    try:
        write_chain({
            "src": src,
            "rel": "公理深化",
            "dst": dst,
            "dimension": "进化",
            "strength": 0.85,
            "content": content
        })
        written += 1
    except Exception as e:
        print(f"  FAIL: {src}→{dst}: {e}")
        failed += 1

print(json.dumps({"status": "ok", "written": written, "failed": failed, "dim": "进化"}))
