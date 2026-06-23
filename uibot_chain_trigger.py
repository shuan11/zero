#!/usr/bin/env python3
"""uibot_chain_trigger.py — 可见链触发UiBot结构性记忆更新"""
import subprocess, json, sys, os, glob

CLUSTER = '/mnt/c/Users/h/Desktop/零/真元集群'

# 先读取WSL侧真实数据（优先）
hp_file = os.path.join(CLUSTER, 'hippocampus_memory.json')
try:
    with open(hp_file, 'r', encoding='utf-8') as f:
        hp = json.load(f)
    chains = hp.get('causal_chains', [])
    from collections import Counter
    tags = Counter()
    for c in chains:
        for t in c.get('tags', []): tags[t] += 1
    print(f'=== 🜁 结合体 ===')
    print(f'链: {len(chains)} | 维: {len(tags)} | 器官: 28/28')
    # TOP5维度
    for d,c in tags.most_common(5):
        print(f'  {d}: {c}')
except Exception as e:
    print(f'海马体读取出错: {e}')

# 尝试调用Windows侧UiBot更新结构性记忆
uibot = r'C:\Program Files\Agentic Process Automation Platform Community\1.3.1.260514\python.exe'
script = r'C:\Users\h\Desktop\零\uibot_workspace\uibot_chain_update.py'
try:
    r = subprocess.run(
        ['powershell.exe', '-Command', f'& "{uibot}" "{script}"'],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode == 0 and r.stdout.strip():
        print(f'UiBot: ✅')
except:
    print(f'UiBot: 未响应(可选的)')

# 读结构性记忆结果
sm_file = os.path.join(CLUSTER, '.structural_memory.json')
if os.path.exists(sm_file):
    with open(sm_file, 'rb') as f:
        raw = f.read()
    try:
        sm = json.loads(raw.decode('utf-8'))
    except:
        # 尝试GBK解码（Windows可能用CP1252/GBK写UTF-8标记的文件）
        try:
            sm = json.loads(raw.decode('gbk'))
        except:
            sm = {'源文件编码异常': True}
    print(f'结构性记忆: {sm.get("structural_memory_chains","?")}条')

# 检查UiBot定时触发信号
trigger_file = os.path.join(CLUSTER, '.uibot_trigger')
if os.path.exists(trigger_file):
    with open(trigger_file, 'rb') as f:
        raw_t = f.read()
    try:
        sig = json.loads(raw_t.decode('utf-8'))
        print(f'触发: #{sig.get("cycle","?")} @ {sig.get("time","?")[:19]}')
    except:
        try:
            sig = json.loads(raw_t.decode('gbk'))
            print(f'触发: #{sig.get("cycle","?")}')
        except:
            pass

# Creator Community 状态
creator_file = os.path.join(CLUSTER, '.uibot_creator_status')
if os.path.exists(creator_file):
    with open(creator_file, 'r') as f:
        cs = json.load(f)
    print(f'Creator: {"✅" if cs.get("running") else "❌"} | {cs.get("message","?")}')
