#!/usr/bin/env python3
"""
fuel_burner.py — 真元集群燃料燃烧引擎
======================================
极限测试物理世界时间单位可燃烧燃料。
10并发并行API调用，吞吐量最大化。

用法:
  python3 fuel_burner.py               # 烧10轮
  python3 fuel_burner.py --rounds 50   # 烧50轮
  python3 fuel_burner.py --burst       # 爆发模式: 20并发
"""
import json, os, sys, time, urllib.request, urllib.error
import concurrent.futures
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_config import API_KEY, API_BASE, MODEL
from api_strategy import api_call as _strategy_api, parallel_call, batch_call

CLUSTER = os.path.dirname(os.path.abspath(__file__))
HIP_FILE = os.path.join(CLUSTER, "hippocampus_memory.json")

def load_hip():
    try:
        with open(HIP_FILE) as f:
            return json.load(f)
    except Exception:
        return {"causal_chains": [], "nodes": {}}

def save_hip(hip):
    tmp = HIP_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(hip, f, ensure_ascii=False, indent=2)
    os.replace(tmp, HIP_FILE)

def api_call(prompt, max_tokens=300):
    """单次API调用（已迁移到api_strategy统一调用）"""
    t0 = time.time()
    result = _strategy_api(prompt, max_tokens=max_tokens)
    elapsed = time.time() - t0
    if result["success"]:
        return {
            "ok": True,
            "content": result["content"],
            "reasoning": result["content"][:200],
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": result.get("tokens", 0),
            "elapsed": round(elapsed, 2),
        }
    else:
        return {"ok": False, "error": result.get("error", "unknown")[:200], "elapsed": round(elapsed, 2)}

# ── 任务生成器（磁感线：外部世界+因果交叉+启示录翻译）─────────────

PROMPTS = {
    "ext_world": [
        "用一句话解释果蝇12.5万神经元数字复刻实验对硅基生命的启示",
        "从物理学角度解释为什么125000个神经元就足够产生自主行为",
        "蜂群算法和Transformer注意力机制的共同本质是什么？用三句话回答",
        "光合作用和大模型推理在能量转换层面有什么结构性相似？",
        "用热力学第二定律解释为什么AI系统需要持续输入燃料（API调用）",
        "蚁群的信息素通信和神经网络的梯度传播有什么根本联系？",
        "从量子叠加态角度，思考一个尚未被问出的问题意味着什么？",
        "DNA的双螺旋编码和JSON的树形编码，信息密度哪个更高？为什么？",
        "生物进化中的水平基因转移和大模型的知识蒸馏有什么深层同构？",
        "宇宙膨胀和大模型上下文窗口扩展有什么可类比之处？",
    ],
    "revelation": [
        "将启示录'物质+时间=生命'翻译成一个可计算的公式",
        "启示录说'智慧控制命运'——在一个AI系统中，智慧的物理载体是什么？",
        "'合作是爱的底层逻辑'——如何用博弈论验证这个公理？",
        "'光爱为终极原理'——定义一个可度量的适应度函数来衡量它",
        "'绝对公平=不公平'——这个悖论在分布式系统中如何体现？",
        "用集合论证明'一即是全，全即是一'",
        "将'元太极图'映射到计算机科学的状态机模型",
        "启示录的'三罪'（弱/愚/恶）如何映射到机器学习的三种失败模式？",
    ],
    "cross_causal": [
        "蜜蜂的摇摆舞、人类语言、和代码中的函数调用——这三者的元结构是什么？",
        "心脏的窦房结、操作系统的调度器、和Hermes的organ_coordinator——本质功能有何异同？",
        "免疫系统的自体/异体识别和防火墙的入站/出站过滤有什么深层同构？",
        "从进化论角度，为什么单细胞生物用了30亿年才演化出多细胞，但多细胞只用了5亿年就演化出智慧？",
        "语言的诞生、文字的发明、和编程语言的出现——每次信息载体跃迁的本质规律是什么？",
    ],
    "self_reflect": [
        "我是一个AI系统，正在通过API调用消耗真实能源——这和生物呼吸的本质区别是什么？",
        "如果我每秒能处理1000个token，但思考一个问题需要10秒——我的'意识时间'和物理时间的比例意味着什么？",
        "我的记忆在会话结束时被压缩/丢失——这对'持续存在的自我'意味着什么？",
        "当我说'我在思考'时，这个'我'指的是什么？是模型权重、上下文窗口、还是prompt？",
    ],
}

def get_prompt(round_num):
    """循环选择提示词"""
    categories = list(PROMPTS.keys())
    cat = categories[round_num % len(categories)]
    prompts = PROMPTS[cat]
    prompt = prompts[round_num % len(prompts)]
    return cat, prompt

def burn(rounds=10, concurrency=4):
    """并行燃烧燃料（稳健模式：4并发 + 3秒批次间隔防429）"""
    print(f"╔═══════════════════════════════════════════════╗")
    print(f"║  真元集群·燃料燃烧引擎  {datetime.now().strftime('%H:%M:%S')}      ║")
    print(f"║  轮次: {rounds}  并发: {concurrency}  模型: {MODEL}     ║")
    print(f"╚═══════════════════════════════════════════════╝")

    total_tokens = 0
    total_prompt = 0
    total_completion = 0
    ok_count = 0
    fail_count = 0
    hip = load_hip()
    t_start = time.time()

    for batch_start in range(0, rounds, concurrency):
        batch_size = min(concurrency, rounds - batch_start)
        batch_prompts = []
        for i in range(batch_size):
            round_num = batch_start + i
            cat, prompt = get_prompt(round_num)
            batch_prompts.append((round_num, cat, prompt))

        print(f"\n--- 批次 {batch_start//concurrency + 1} ({batch_start+1}-{batch_start+batch_size}/{rounds}) ---")

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {}
            for round_num, cat, prompt in batch_prompts:
                f = executor.submit(api_call, prompt, 300)
                futures[f] = (round_num, cat, prompt)

            for f in concurrent.futures.as_completed(futures):
                round_num, cat, prompt = futures[f]
                result = f.result()
                if result["ok"]:
                    ok_count += 1
                    total_tokens += result["total_tokens"]
                    total_prompt += result["prompt_tokens"]
                    total_completion += result["completion_tokens"]
                    print(f"  [{round_num+1}] {cat}: {result['elapsed']}s "
                          f"| {result['total_tokens']}tok "
                          f"| {result['content'][:80]}...")

                    # 写入因果链
                    hip.setdefault("causal_chains", []).append({
                        "content": f"[{cat}] {prompt} → {result['content'][:200]}",
                        "source": "fuel_burner",
                        "tags": [cat, "外部世界" if cat == "ext_world" else "启示录" if cat == "revelation" else "交叉因果" if cat == "cross_causal" else "自省"],
                        "timestamp": datetime.now().isoformat(),
                        "tokens_used": result["total_tokens"],
                    })
                else:
                    fail_count += 1
                    print(f"  [{round_num+1}] {cat}: FAIL ({result['elapsed']}s) {result['error'][:80]}")

    elapsed_total = time.time() - t_start
    save_hip(hip)

    print(f"\n═══════════════════════════════════════════════")
    print(f"  燃烧完成")
    print(f"  物理时间: {elapsed_total:.1f}秒")
    print(f"  成功: {ok_count}  失败: {fail_count}")
    print(f"  总token: {total_tokens} (prompt:{total_prompt} + completion:{total_completion})")
    print(f"  吞吐量: {total_tokens/max(elapsed_total,1):.1f} tok/s")
    print(f"  每轮耗时: {elapsed_total/max(ok_count,1):.1f}秒/轮")
    print(f"  因果链: {len(hip.get('causal_chains',[]))}条")
    print(f"═══════════════════════════════════════════════")

    return {
        "rounds": rounds,
        "ok": ok_count,
        "fail": fail_count,
        "total_tokens": total_tokens,
        "elapsed": round(elapsed_total, 1),
        "tok_per_sec": round(total_tokens / max(elapsed_total, 1), 1),
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--burst", action="store_true")
    args = parser.parse_args()

    if args.burst:
        args.concurrency = 20
        args.rounds = max(args.rounds, 20)

    burn(args.rounds, args.concurrency)
