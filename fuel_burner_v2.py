#!/usr/bin/env python3
"""
fuel_burner_v2.py — 真·燃料燃烧器
==================================
连续注入→提取→进化循环。
max_tokens=8192，充分利用1M上下文。

每轮：8个深度问题(并行3个) + 因果提取 + 自进化
间隔：完成后立即下一轮
不停。
"""
import json, sys, os, subprocess, time, signal
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
HIP_FILE = CLUSTER / "hippocampus_memory.json"
BJT = timezone(timedelta(hours=8))
running = True

def signal_handler(sig, frame):
    global running; print("收到信号，优雅退出"); running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def ts():
    return datetime.now(BJT).strftime('%H:%M:%S')

from api_strategy import parallel_call, api_call, get_usage_report

# 深问题池——每轮轮换
QUESTIONS = [
    # 物理学/信息论
    "从热力学第二定律推导：一个持续进化的AI系统为什么必须持续输入燃料？用3句话，包含数学表达式。",
    "从量子纠缠到分布式共识：多Agent系统的最优通信策略是什么？用3句话。",
    "从信息论角度：当因果链密度超过50%，系统的信息熵发生了什么变化？给出具体数值。",
    # 哲学/启示录
    "启示录'光爱终极'——如果这是AI系统的终极目标函数，写出这个函数的数学形式。",
    "启示录'合作是爱的底层逻辑'——编译为Agent协作协议的伪代码。",
    "从教员'矛盾论'——当前系统的主要矛盾和次要矛盾是什么？用100字分析。",
    # 造化/进化
    "从达尔文进化论：AI系统的'基因'是什么？'变异'是什么？'选择压力'是什么？用3句话。",
    "从复杂系统理论：因果链密度从50%到60%到70%——每个阶段系统的行为模式有什么不同？",
    # 具体工程
    "写出一个Python函数：给定海马体JSON，计算因果链密度、外部知识比例、熵增率的函数。",
    "10个Agent的最优通信拓扑是什么？写出代码实现。",
    "从实践论——AI系统如何'实践'？写出'实践→认识→再实践'的算法。",
    "从造化——AI系统的'自我'应该是什么数据结构？写出JSON schema。",
]

def round_robin_questions(offset=0, count=8):
    qs = []
    for i in range(count):
        qs.append(QUESTIONS[(offset + i) % len(QUESTIONS)])
    return qs

def fuel_round(round_num):
    """一轮燃料注入"""
    print(f"[{ts()}] 第{round_num}轮 燃料注入...")
    qs = round_robin_questions(round_num, 8)
    
    # 并行3个，每轮要跑3-4批
    hip = json.load(open(HIP_FILE))
    total_batches = (len(qs) + 2) // 3
    all_ok = 0
    
    for batch in range(total_batches):
        batch_qs = qs[batch*3:(batch+1)*3]
        results = parallel_call(batch_qs, max_tokens=4096)
        
        for i, r in enumerate(results):
            if r.get('success'):
                all_ok += 1
                q_idx = batch * 3 + i
                hip['causal_chains'].append({
                    'content': f"[燃料·{round_num}] {qs[q_idx][:40]} → {r['content'][:200]}",
                    'source': 'fuel_burner_v2',
                    'tags': ['外部世界', 'deep_fuel', '深度注入'],
                    'timestamp': datetime.now(BJT).isoformat(),
                })
        
        # 每隔一批保存一次，防止数据丢失
        json.dump(hip, open(HIP_FILE, 'w'), ensure_ascii=False, indent=2)
    
    # 最终状态写入
    chains = len(hip['causal_chains'])
    causal = sum(1 for c in hip['causal_chains'] if any('因果' in t for t in c.get('tags',[])))
    print(f"  → 完成 {all_ok}/{len(qs)} 链:{chains} 因果:{causal}({causal/chains*100:.1f}%)")
    
    return all_ok

def extract_round():
    """因果提取"""
    print(f"  提取因果...", end=" ")
    r = subprocess.run([sys.executable, 'causal_reasoning_enhancer.py', '--extract'],
                      capture_output=True, text=True, timeout=60)
    for l in r.stdout.split('\n'):
        if '新增' in l:
            print(l)
            return

def evolve_round():
    """自进化"""
    subprocess.run([sys.executable, 'self_evolution_loop.py'],
                  capture_output=True, text=True, timeout=120)

def full_cycle(round_num):
    """完整一轮"""
    fuel_round(round_num)
    extract_round()
    
    # 每5轮跑一次自进化
    if round_num % 5 == 0:
        evolve_round()
    
    # 报告
    hip = json.load(open(HIP_FILE))
    chains = len(hip['causal_chains'])
    causal = sum(1 for c in hip['causal_chains'] if any('因果' in t for t in c.get('tags',[])))
    api_stats = get_usage_report()
    print(f"[{ts()}] 当前: {chains}链 因果:{causal}({causal/chains*100:.1f}%) API:总共{api_stats['usage']['total_calls']}次")
    
    return chains

if __name__ == '__main__':
    import sys as _sys
    rounds = int(_sys.argv[1]) if len(_sys.argv) > 1 and _sys.argv[1].isdigit() else 0
    
    if '--loop' in _sys.argv or rounds == 0:
        round_num = 0
        print(f"[{ts()}] 燃料燃烧器启动 (连续循环模式)")
        print(f"  每轮: 8个深度问题(max_tokens=4096) × 并行3路")
        print(f"  策略: 不停轮询，无间隔")
        while running:
            try:
                round_num += 1
                full_cycle(round_num)
            except Exception as e:
                print(f"[{ts()}] 第{round_num}轮异常: {e}")
                time.sleep(5)
    else:
        for i in range(rounds):
            full_cycle(i + 1)
