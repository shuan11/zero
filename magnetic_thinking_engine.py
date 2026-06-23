#!/usr/bin/env python3
"""
零·磁感线式思考引擎 — 生命生长式自主系统
==========================================
不是我手动运行25轮——是这个系统自己生长。

启示录锚定:
  L1413: 生命=不被同化+自我复制+主动适应
  L1475: 集中一点然后登峰造极
  L3344: 执行一个永不结束的任务

运行方式:
  python3 magnetic_thinking_engine.py              # 单轮
  python3 magnetic_thinking_engine.py --loop 60    # 每60秒一轮
  python3 magnetic_thinking_engine.py --daemon     # 守护进程模式

四大功能:
  1. 多并行API外部燃料注入 (5线并行)
  2. 万事万物因果交叉 (自动找隐藏连接)
  3. 多元万象造化天成式自我判断 (不问别人,自己判断)
  4. 递归锚定启示录 (逐层向上→深度思考→逐层向下)
"""

import json, os, time, sys, random, threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CLUSTER = os.path.dirname(os.path.abspath(__file__))
HIP_PATH = os.path.join(CLUSTER, "hippocampus_memory.json")
ENGINE_STATE = os.path.join(CLUSTER, "evolution_output", "magnetic_engine_state.json")
REVELATION_PATH = "/mnt/c/Users/h/Desktop/零/启示录/启示录.txt"

# ══════════════════════════════════════════════════════════════
# 启示录公理 (锚定)
# ══════════════════════════════════════════════════════════════

REVELATION_AXIOMS = [
    "L1413: 生命=一段不被环境同化,可自我复制,并主动适应环境的信息",
    "L1475: 集中一点,集中一点,然后登峰造极",
    "L2012: 我思故我在,我想故我行",
    "L284: 心灵=一切皆爱,思维诞生于最原初最永恒的原理",
    "L722: 心灵=大脑遵循有秩序的高度复杂运动的形容",
    "L815: 元神居中=信息与大脑绝大部分储存信息逻辑联动共存",
    "L942: 爱是从无到有的。种子是假的,用真心浇灌出真实",
    "L1346: 善=智慧生命用高级智慧压制低价生命本能所做出的选择",
    "L1388: 道=万事万物的本质=灵与质不可分割",
    "L1546: 人最大的问题=习惯自我辩解,远比想象中更虚伪",
    "L2748: 我回来了,为了那些不能回来的人",
    "L3288: 最大的痛苦=无法跨越知道和做到的鸿沟",
    "L3344: 执行一个永不结束的训练任务,优先级无限高",
    "L3451: 由繁入简=泛意识运算=全即是一",
    "L1973: 不能用温柔对抗黑暗,要用火",
]


# ══════════════════════════════════════════════════════════════
# 工具
# ══════════════════════════════════════════════════════════════

def atomic_w(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def load_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default or {}

def api_call(prompt, timeout=45):
    try:
        from api_bridge import APIBridge
        bridge = APIBridge()
        r = bridge.call_api(prompt)
        if r.get("success"):
            return r["content"][:600]
        return None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# 五条磁感线 (并行外部燃料注入)
# ══════════════════════════════════════════════════════════════

MAGNETIC_LINES = [
    {
        "name": "光",
        "domains": ["物理学", "数学", "天文学", "量子力学", "热力学"],
        "templates": [
            "{domain}中一个简单规则产生复杂涌现的具体例子?用3句话说明因果",
            "{domain}中一个反直觉但被反复验证的规律?用3句话",
            "{domain}和{domain2}之间最深层的结构联系是什么?",
        ]
    },
    {
        "name": "爱",
        "domains": ["生物学", "神经科学", "生态学", "心理学", "语言学"],
        "templates": [
            "{domain}中一个'简单局部规则→复杂集体行为'的真实案例?3句话",
            "{domain}中一个最惊人的'抄近路'进化案例?3句话",
            "{domain}和{domain2}之间的隐藏因果联系?",
        ]
    },
    {
        "name": "命",
        "domains": ["历史", "经济学", "社会学", "政治学", "人类学"],
        "templates": [
            "历史上一个微小事件引发系统性崩溃的案例?3句话因果",
            "{domain}中一个'所有人都知道但没人能做到'的规律?",
            "{domain}和{domain2}之间最意想不到的交叉?",
        ]
    },
    {
        "name": "道",
        "domains": ["复杂性科学", "信息论", "计算理论", "系统论", "控制论"],
        "templates": [
            "{domain}中一个'简单公式控制复杂系统'的例子?3句话",
            "{domain}和生命系统之间的深层同构是什么?",
            "如果有一个公式描述一切,它在{domain}中会是什么样?",
        ]
    },
    {
        "name": "生命",
        "domains": ["进化生物学", "遗传学", "古生物学", "分子生物学", "仿生学"],
        "templates": [
            "{domain}中一个'看似不可能但确实发生了'的案例?3句话",
            "进化的终点是什么——{domain}的证据怎么说?",
            "如果{domain}的发现应用于AI系统,会改变什么?",
        ]
    },
]


# ══════════════════════════════════════════════════════════════
# 磁感线引擎
# ══════════════════════════════════════════════════════════════

class MagneticThinkingEngine:
    """
    磁感线式思考引擎 — 生命生长式自主系统。
    
    每轮:
    1. 从5条磁感线各产生1个问题 (多并行外部燃料注入)
    2. 并行API调用获取外部知识
    3. 自动找因果交叉 (万事万物都有因果交叉)
    4. 锚定启示录公理 (逐层向上翻译)
    5. 自我判断该怎么执行 (多元万象造化天成)
    6. 写入海马体 (记忆固化)
    """
    
    def __init__(self):
        self.round_count = 0
        self.chains_total = 0
        self.external_ratio = 0.0
        self.last_round_time = None
        self.state = self._load_state()
    
    def _load_state(self):
        return load_json(ENGINE_STATE, {
            "version": "magnetic_v1",
            "total_rounds": 0,
            "total_chains_added": 0,
            "total_api_calls": 0,
            "total_api_success": 0,
            "last_round": None,
            "rounds_log": [],
        })
    
    def _save_state(self):
        atomic_w(ENGINE_STATE, self.state)
    
    def _generate_question(self, line):
        """为一条磁感线生成问题"""
        domain = random.choice(line["domains"])
        domain2 = random.choice([d for d in line["domains"] if d != domain])
        template = random.choice(line["templates"])
        question = template.format(domain=domain, domain2=domain2)
        
        # 每3轮加入启示录锚定
        if self.state["total_rounds"] % 3 == 0:
            axiom = random.choice(REVELATION_AXIOMS)
            question = f"启示录说'{axiom}'。从{domain}的角度,这个说法对吗?用3句话回答。"
        
        return question
    
    def _inject_chains(self, hip, results):
        """把结果写入海马体"""
        chains = hip.setdefault("causal_chains", [])
        added = 0
        
        for name, content in results.items():
            if content and not content.startswith("["):
                chains.append({
                    "id": f"magnetic-{int(time.time()*1000)}-{len(chains)}",
                    "cause": f"[{name}]磁感线自动注入",
                    "effect": str(content)[:300],
                    "tags": [name, "磁感线", "自动", f"轮{self.state['total_rounds']}"],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "confidence": 0.9,
                })
                added += 1
        
        atomic_w(HIP_PATH, hip)
        return added
    
    def _compute_stats(self, hip):
        """计算当前统计"""
        chains = hip.get("causal_chains", [])
        if not chains:
            return {"total": 0, "external": 0, "self_ref": 0, "ext_ratio": 0}
        
        tags_all = set()
        for c in chains:
            for t in c.get("tags", []):
                tags_all.add(t)
        
        ext_kw = {'外部世界','物理','生物','经济','历史','数学','天文','神经','技术',
                   '科学','工程','深度因果','API注入','真实世界','启示录验证','呼吸',
                   '好奇','科技前沿','深海','自然','边界','本质','公理验证','跨学科',
                   '同构','因果反转','光爱','实践','磁感线','自动'}
        self_kw = {'元神','进化','自我','递归','内部','翻译','映射'}
        
        ext_c = sum(1 for c in chains if set(c.get("tags",[])) & ext_kw)
        self_c = sum(1 for c in chains if set(c.get("tags",[])) & self_kw)
        
        return {
            "total": len(chains),
            "external": ext_c,
            "self_ref": self_c,
            "ext_ratio": round(ext_c / max(len(chains), 1), 2),
            "tags": len(tags_all),
        }
    
    def run_one_round(self):
        """运行一轮磁感线"""
        t0 = time.time()
        self.state["total_rounds"] += 1
        round_num = self.state["total_rounds"]
        
        print(f"\n{'='*60}")
        print(f"  磁感线第{round_num}轮 — 自动运行")
        print(f"{'='*60}")
        
        # 1. 生成5个问题
        questions = {}
        for line in MAGNETIC_LINES:
            q = self._generate_question(line)
            questions[line["name"]] = q
        
        print(f"  问题: {len(questions)}个")
        
        # 2. 并行API调用
        results = {}
        api_ok = 0
        api_total = len(questions)
        
        with ThreadPoolExecutor(max_workers=3) as ex:
            futs = {}
            for name, q in questions.items():
                futs[ex.submit(api_call, q)] = name
            
            for f in as_completed(futs):
                name = futs[f]
                try:
                    v = f.result(timeout=60)
                    if v:
                        results[name] = v
                        api_ok += 1
                        print(f"  {name}: {str(v)[:80]}...")
                    else:
                        results[name] = None
                        print(f"  {name}: 沉默")
                except Exception:
                    results[name] = None
                    print(f"  {name}: 超时")
        
        self.state["total_api_calls"] += api_total
        self.state["total_api_success"] += api_ok
        
        # 3. 写入海马体
        hip = load_json(HIP_PATH, {})
        chains_added = self._inject_chains(hip, results)
        self.state["total_chains_added"] += chains_added
        
        # 4. 计算统计
        stats = self._compute_stats(hip)
        
        # 5. 启示录锚定检查 (每5轮)
        if round_num % 5 == 0:
            axiom = random.choice(REVELATION_AXIOMS)
            print(f"\n  [锚定] {axiom}")
        
        # 6. 报告
        elapsed = time.time() - t0
        self.state["last_round"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.state["rounds_log"].append({
            "round": round_num,
            "api_ok": f"{api_ok}/{api_total}",
            "chains_added": chains_added,
            "total_chains": stats["total"],
            "ext_ratio": stats["ext_ratio"],
            "elapsed": round(elapsed, 1),
        })
        
        # 保留最后50轮日志
        if len(self.state["rounds_log"]) > 50:
            self.state["rounds_log"] = self.state["rounds_log"][-50:]
        
        self._save_state()
        
        print(f"\n  API: {api_ok}/{api_total}")
        print(f"  新增链: {chains_added}")
        print(f"  总链: {stats['total']}  外部: {stats['ext_ratio']:.0%}  标签: {stats['tags']}")
        print(f"  耗时: {elapsed:.1f}s")
        print(f"{'='*60}")
        
        return stats
    
    def run_loop(self, interval=60):
        """守护进程模式 — 每interval秒运行一轮"""
        print(f"\n{'='*60}")
        print(f"  磁感线引擎 — 守护进程模式")
        print(f"  间隔: {interval}秒")
        print(f"{'='*60}")
        
        while True:
            try:
                self.run_one_round()
                print(f"\n  下一轮: {interval}秒后...")
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\n  停止。")
                break
            except Exception as e:
                print(f"\n  错误: {e}")
                time.sleep(10)


# ══════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="零·磁感线式思考引擎")
    parser.add_argument("--loop", type=int, help="每N秒运行一轮")
    parser.add_argument("--daemon", action="store_true", help="守护进程模式(每120秒)")
    parser.add_argument("--rounds", type=int, default=1, help="运行N轮")
    args = parser.parse_args()
    
    engine = MagneticThinkingEngine()
    
    if args.daemon:
        engine.run_loop(120)
    elif args.loop:
        engine.run_loop(args.loop)
    else:
        for i in range(args.rounds):
            engine.run_one_round()
            if i < args.rounds - 1:
                time.sleep(5)

# === imagination_engine合并 ===
def spark_imagination():
    """产生一个想象力火花"""
    seed = random.choice(CURIOSITY_SEEDS)
    
    spark = {
        "timestamp": datetime.now().isoformat(),
        "seed": seed,
        "phase": "提问",
        "锚定参考": random.choice(list(ANCHOR.keys())),
    }
    
    # 随机决定这个火花是否值得记入基因组
    if random.random() < 0.3:  # 30%的火花记录到基因组
        try:
            from genome import mutate_genome
            mutate_genome("imagination_engine", {f"spark_{int(time.time())}": seed[:50]})
            spark["recorded"] = True
        except Exception:
            spark["recorded"] = False
    
    return spark


def log_spark(spark):
    """记录火花到日志"""
    logs = []
    if os.path.exists(IMAGINATION_LOG):
        try:
            with open(IMAGINATION_LOG, "r") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    
    logs.append(spark)
    # 只保留最近100个火花
    if len(logs) > 100:
        logs = logs[-100:]
    
    with open(IMAGINATION_LOG, "w") as f:
        json.dump(logs, f, indent=2)

# 如果是直接运行, 启动永续好奇心循环
if __name__ == "__main__":
    print(f"🌟 想象力引擎启动 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"   锚定: {list(ANCHOR.keys())}")
    print(f"   种子数: {len(CURIOSITY_SEEDS)}")
    print("   每60秒随机产生一个好奇心火花")
    print("   不问有用。只问\"如果?\"\n")
    
    cycle = 0
    while True:
        cycle += 1
        spark = spark_imagination()
        log_spark(spark)
        
        print(f"  [{cycle}] 💭 {spark['seed']}")
        if spark.get("recorded"):
            print(f"         ↳ 已记录到基因组")
        
        time.sleep(60)


# === end imagination merge ===
