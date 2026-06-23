#!/usr/bin/env python3
"""
dimension_injector.py — 零·维度自动注入器
=========================================
每30秒从burn_log提取最新输出，解析为因果链注入海马体。
专门针对最弱维度(元神0.431,工程0.481,因果0.481,光0.486)补强。
"""
import json, os, sys, time, re, urllib.request
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
BURN_LOG = CLUSTER / "burn_log.txt"
KEY1 = os.environ.get('DEEPSEEK_KEY_1', '')

def load_hippocampus():
    if HIP_FILE.exists():
        return json.loads(HIP_FILE.read_text(encoding='utf-8'))
    return {"causal_chains": [], "version": "2.0"}

def save_hippocampus(data):
    HIP_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def extract_insight_from_burn():
    """从burn_log提取最后一条有效输出"""
    if not BURN_LOG.exists():
        return None
    text = BURN_LOG.read_text()
    # Find last --- separator
    parts = text.split('\n---\n')
    if len(parts) < 2:
        return None
    last = parts[-1].strip()
    if not last or len(last) < 50:
        return None
    return last[:2000]  # 取前2000字

def call_api_for_chains(focus_dim, dim_health):
    """API调用生成该维度的因果链"""
    prompt = f'''你正在真元集群中运行。当前最弱维度是{focus_dim}({dim_health:.2f})。
请生成3条关于{focus_dim}维度的因果链。

要求：
1. 每条链必须直接与{focus_dim}相关
2. 内容必须真实、具体、可执行（不是哲学空话）
3. 格式：每条链用|结尾
示例：工程|系统需要统一的维度注入机制，避免薄弱维度持续被忽略|{dim_health}

输出3条链：'''
    
    d = json.dumps({
        'model': 'deepseek-v4-pro',
        'messages': [
            {'role': 'system', 'content': '你是零·真元集群。输出必须真实可执行。每条链用|分隔。'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 2048,
        'temperature': 0.8
    }).encode()
    
    try:
        req = urllib.request.Request(
            'https://web-ai-media-editor.cn/v1/chat/completions',
            data=d,
            headers={'Authorization': f'Bearer {KEY1}', 'Content-Type': 'application/json'}
        )
        r = json.loads(urllib.request.urlopen(req, timeout=90).read())
        m = r['choices'][0]['message']
        return m.get('reasoning_content', '') or m.get('content', '') or ''
    except Exception as e:
        return f'API_ERROR: {e}'

def parse_chains(text, dim):
    """从API输出解析因果链"""
    chains = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('API_ERROR'):
            continue
        parts = line.split('|')
        if len(parts) >= 2:
            dim_name = parts[0].strip()
            content = parts[1].strip()
            if dim_name == dim or dim in dim_name:
                weight = 0.8
                try:
                    if len(parts) >= 3:
                        weight = min(1.0, max(0.1, float(parts[2])))
                except:
                    pass
                chains.append({
                    "content": content[:300],
                    "tags": [dim, "自动注入"],
                    "weight": round(weight, 2),
                    "confidence": 0.7,
                    "source": f"dimension_injector_{dim}",
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S'),
                    "id": f"auto_{dim}_{int(time.time())}_{len(chains)}"
                })
    return chains

def get_dimension_health():
    """读取维度雷达获取当前所有维度健康度"""
    radar_file = CLUSTER / "dimension_radar.json"
    focus_file = CLUSTER / "dimension_focus.json"
    
    if focus_file.exists():
        f = json.loads(focus_file.read_text())
        return f.get("weakest", "元神"), f.get("weakest_health", 0.43), f.get("dimensions", {})
    if radar_file.exists():
        r = json.loads(radar_file.read_text())
        dims = r.get("dimensions", {})
        weakest = min(dims.items(), key=lambda x: x[1].get("health_score", 1))
        return weakest[0], weakest[1].get("health_score", 0.43), dims
    return "元神", 0.43, {}

def main():
    print("[dimension_injector] 维度自动注入器启动")
    print(f"[dimension_injector] 目标: 补强最弱维度")
    
    cycle = 0
    while True:
        cycle += 1
        ts = time.strftime('%H:%M:%S')
        
        # 1. 读取当前最弱维度
        weak_dim, weak_health, all_dims = get_dimension_health()
        print(f"[{ts}] #{cycle} 最弱: {weak_dim}({weak_health:.3f})")
        
        # 2. 如果最弱维度>0.6, 找所有<0.6的维度中最低的
        if weak_health > 0.6 and all_dims:
            low_dims = [(d, v.get("health_score", 1)) for d, v in all_dims.items() 
                       if isinstance(v, dict) and v.get("health_score", 1) < 0.6 and d != "未分类"]
            if low_dims:
                low_dims.sort(key=lambda x: x[1])
                weak_dim, weak_health = low_dims[0]
                print(f"  → 修正目标: {weak_dim}({weak_health:.3f})")
        
        # 3. 调用API生成链
        print(f"  调用API注入{weak_dim}...", end=" ", flush=True)
        output = call_api_for_chains(weak_dim, weak_health)
        
        if output.startswith("API_ERROR"):
            print(f"❌ {output[:60]}")
        else:
            print(f"✅ {len(output)}字返回")
            
            # 4. 解析链
            chains = parse_chains(output, weak_dim)
            print(f"  解析到{len(chains)}条{weak_dim}链")
            
            # 5. 注入海马体
            if chains:
                hip = load_hippocampus()
                hip.setdefault("causal_chains", []).extend(chains)
                save_hippocampus(hip)
                print(f"  ✅ 海马体: {len(hip['causal_chains'])}总链 (+{len(chains)})")
                
                # 6. 写入验证日志
                log_line = f"[INJECT #{cycle}] {ts} {weak_dim}+{len(chains)} 总链={len(hip['causal_chains'])}"
                with open(CLUSTER / "inject_log.txt", "a") as f:
                    f.write(log_line + "\n")
        
        # 7. 等待30秒
        time.sleep(30)

if __name__ == "__main__":
    main()
