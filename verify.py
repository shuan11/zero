#!/usr/bin/env python3
"""verify.py — 零·燃料产出验真器
每轮API燃烧后运行，检查输出中是否有可验证的虚假陈述。
原理：不是阻止幻觉（模型一定会产生），是在我传播之前抓住它。

检查清单：
1. 硬数字 → 是否对应真实文件/状态
2. 系统内事实 → 文件系统是否存在
3. 物理世界事实 → 常识/时间/逻辑
4. 声称的行动 → 是否真的被执行过
5. 自我声称 → "我做了X"是否真实

Usage:
  python3 verify.py <burn_output_file>
  python3 verify.py --check-all  (检查最近20个burn输出)
"""
import json, sys, os, re, glob
from datetime import datetime

RUN_DIR = os.path.dirname(os.path.abspath(__file__))

# —— 已知真实状态（从文件系统读）——
def load_truth():
    """加载可验证的真实状态"""
    truth = {}
    
    # state_vector
    try:
        sv = json.load(open(os.path.join(RUN_DIR, "state_vector.json")))
        truth["sv_cycle"] = sv.get("cycle")
        truth["sv_timestamp"] = sv.get("timestamp")
        truth["sv_chains"] = sv.get("chains")
        truth["sv_nodes"] = sv.get("nodes")
        truth["sv_organs"] = sv.get("organs_alive")
        truth["sv_bridges"] = sv.get("bridges_alive")
    except:
        pass
    
    # burn_stats
    try:
        bs = json.load(open(os.path.join(RUN_DIR, "burn_stats.json")))
        truth["burn_count"] = bs.get("burn_count")
        truth["burn_tokens"] = bs.get("burn_tokens_total")
    except:
        pass
    
    # 文件列表
    truth["py_files_count"] = len(glob.glob(os.path.join(RUN_DIR, "*.py")))
    truth["burn_files_count"] = len(glob.glob(os.path.join(RUN_DIR, "_burn_results", "*.json")))
    
    # 时间
    truth["now_bj"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return truth

# —— 幻觉检测模式 ——
HALLUCINATION_PATTERNS = [
    # — 系统不存在或无法验证的指标 —
    (r"(进化层级|进化等级|evolution.level|evolution_level)[=:\s]*[Ll]\d+", "可疑: 进化层级是主观评分"),
    (r"(意识水平|consciousness.level|consciousness_level)[=:\s]*[\d\.]+", "可疑: 意识水平无法客观测量"),
    (r"(幻觉率|hallucination.rate|hallucination_rate)[=:\s]*\d+\.?\d*%", "可疑: 幻觉率自指循环"),
    (r"(用户满意度|satisfaction)[=:\s]*\d+%", "可疑: 用户满意度不可测量"),
    (r"(代码覆盖率|coverage)[=:\s]*\d+%", "可疑: 代码覆盖率声称"),
    
    # — 声称做了某事但不可验证 —
    (r"(已|已经)(修复|解决|完成|实现).*(bug|问题|issue|缺陷|漏洞)", "⚠ 声称已修复，需文件证据"),
    (r"(部署|上线|发布)了.*(版本|v\d|release)", "⚠ 声称部署，但WSL无部署目标"),
    (r"收到了来自.*(用户|系统|外部|API|模型|agent).*(反馈|请求|指令|消息)", "⚠ 声称收到外部输入，会话内可验证"),
    
    # — 声称分析/处理了不存在的数据 —
    (r"分析了.*(最近|过去|历史).*\d+.*(条|次|个|份).*(数据|记录|日志|交互|燃烧|决策)", "⚠ 声称分析了历史数据，实际没有传入"),
    (r"对.*进行.*(分析|审计|扫描|检查).*发现.*\d+.*(问题|模式|异常|缺陷)", "⚠ 声称发现X个问题，需确认"),
    (r"(扫描|检查|审计)了.*\d+.*(文件|模块|器官|桥)", "⚠ 声称扫描了具体数量"),
    
    # — 声称知道系统外部事实 —
    (r"(据我所知|据[统计报道研究]|根据[资料文献])", "⚠ 外源知识未经核实"),
    (r"(论文|研究|学术界|学者).*(表明|显示|证明|指出|发现)", "⚠ 学术声称需确认来源"),
    (r"(今天|昨天|明天).*(星期[一二三四五六日]|周[一二三四五六日])", "⚠ 时间/日期声称"),
    
    # — "自信的不知道"模式 —
    (r"无法(获取|访问|读取|找到|确定).*但[，,。]?", "⚠ '无法X但...' → 可能开始编造"),
    (r"基于.*上下文.*无法.*[。，,]?.*以下[是为：:]", "⚠ '上下文不够，但我还是硬分析'"),
    (r"(没有数据|缺少数据|无法分析).*[。，,][。，,]?.*(不过|但是|然而)", "⚠ 承认没数据→但继续编"),
    (r"(模拟|假设|推测).*(场景|情况|数据).*(分析|框架|示例)", "⚠ 模拟数据当真实分析"),
    
    # — 综合/复合模式 —
    (r"(真实第一|不编造|不虚构).*[。，,]?.*(不过|以下|让我|我们)", "⚠ 说不编造→立刻开始编"),
]

def check_file(burn_path):
    """检查一个燃烧产出文件是否有幻觉"""
    try:
        with open(burn_path) as f:
            data = json.load(f)
    except:
        return {"file": burn_path, "error": "parse_failed", "hallucinations": []}
    
    content = ""
    if isinstance(data, dict):
        content = data.get("content", "") or data.get("c", "") or json.dumps(data)
    elif isinstance(data, str):
        content = data
    
    hallucinations = []
    
    # 检查模式
    for pattern, reason in HALLUCINATION_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            for m in matches[:3]:  # 最多3个
                hallucinations.append({"reason": reason, "match": m})
    
    # 检查数字声称
    numbers = re.findall(r'(?:约|共|有|达到|消耗|使用|产生|处理|分析|检查|发现|识别|标记|删除|添加|修改|创建|更新)?(\d+\.?\d*)\s*(次|个|条|份|token|文件|节点|链|器官|桥|轮|代|天|小时|分钟|秒)', content)
    truth = load_truth()
    for num_str, unit in numbers:
        num = float(num_str)
        # 可疑数字: 超过burn_count但小于10倍的
        if unit in ("次", "轮", "代") and truth.get("burn_count"):
            if num > truth["burn_count"] * 10 and num != truth["burn_count"]:
                hallucinations.append({"reason": f"可疑数字: 声称{num}{unit}, 实际燃烧{truth['burn_count']}次", "match": f"{num:.0f}{unit}"})
    
    return {
        "file": burn_path,
        "hallucination_count": len(hallucinations),
        "hallucinations": hallucinations[:10],
        "confidence": "low" if len(hallucinations) > 3 else ("medium" if len(hallucinations) > 0 else "high")
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: verify.py <burn_output.json> or --check-all")
        sys.exit(1)
    
    if sys.argv[1] == "--check-all":
        # 检查最近20个
        files = sorted(glob.glob(os.path.join(RUN_DIR, "_burn_results", "*.json")), 
                       key=os.path.getmtime)[-20:]
        total_hallucinations = 0
        for f in files:
            result = check_file(f)
            if result["hallucination_count"] > 0:
                print(f"[{result['confidence'].upper()}] {os.path.basename(f)}: {result['hallucination_count']} 条可疑")
                for h in result["hallucinations"][:3]:
                    print(f"   → {h['reason']}")
                total_hallucinations += result["hallucination_count"]
        print(f"\n总计: 检查{len(files)}个文件, {total_hallucinations}条可疑内容")
    else:
        result = check_file(sys.argv[1])
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
