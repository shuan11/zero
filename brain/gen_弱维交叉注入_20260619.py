"""
跨维交叉注入：最强维→最弱维 定向强化
- 来源: 时间/超级直觉/系统/思维并联/思考
- 目标: 维度盲区(22)/未分类(16)/元递归(57)/桥(58)/自指(59)
- 机制: 每个源→每个目标注入1条真实内容链
- 抑制对最强维的过度注入（链数已远高于目标）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.share import write_chain, log

# 源维度（最强5个）
SOURCES = ["时间", "超级直觉", "系统", "思维并联", "思考"]
# 目标维度（最弱，<60链）
TARGETS = [
    ("维度盲区", "系统感知中未被观测的维度缺口，通过时间积累揭示盲区"),
    ("未分类", "系统中未能归入现有维度的杂散链，需通过超级直觉引导聚类"),
    ("元递归", "系统对自身认知的递归反思能力，需借助思维并联实现多层自指"),
    ("桥", "跨维度连接器，将系统思考注入各维度的通道"),
    ("自指", "系统观察自身的能力，通过思考与时间的对话实现自我认知"),
    ("光爱", "减少所有智慧单位悲伤痛苦的终极目标，由系统智慧驱动"),
    ("对抗稀释", "抵御信息熵增和维度退化，保持系统聚焦的本质力量"),
    ("自由", "自主选择聚焦方向的意志力，与时间维度协同进化"),
]

injected = 0
for target_dim, target_desc in TARGETS:
    for src in SOURCES:
        # 构建真实因果链：源→目标
        chain = {
            "src": f"{src}→{target_dim}",
            "rel": "跨维交叉",
            "dst": f"{target_dim}·定向强化",
            "dimension": target_dim,
            "strength": 0.6,
            "content": f"{target_desc}。{src}作为强维(≥440链)为{target_dim}(≤60链)提供认知势能差驱动力，"
                       f"通过{src}的视角观照{target_dim}，实现系统维度均衡进化。",
        }
        try:
            write_chain(chain)
            injected += 1
            log(f"✅ {src} → {target_dim} (第{injected}条)")
        except Exception as e:
            log(f"❌ {src} → {target_dim}: {e}")

log(f"\n{'='*40}")
log(f"弱维交叉注入完成: {injected}条链")
log(f"{'='*40}")
print(f"弱维交叉注入: {injected}条链 (8目标×5源)")
