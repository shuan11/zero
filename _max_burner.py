#!/usr/bin/env python3
"""
MAX TOKEN THROUGHPUT BURNER
Continuous API calls with maximum context injection.
No breaks. No mercy. Pure throughput.
"""
import urllib.request
import urllib.error
import json
import os
import sys
import time
import glob
import base64
import traceback
import ssl

# === CONFIG ===
BASE_DIR = "/mnt/c/Users/h/Desktop/零/真元集群"
OUTPUT_FILE = os.path.join(BASE_DIR, "evolution_output", "real_findings.jsonl")

# Dual endpoints
ENDPOINTS = [
    "https://web-ai-media-editor.cn/v1/chat/completions",
    # infieraichat.com DNS unreachable from WSL
]

API_KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"

MAX_TOKENS = 100000
TEMPERATURE = 0.8
CALL_INTERVAL = 1.5  # seconds between calls (1.5s < 2s limit)

# Dimension rotation
DIMENSIONS = [
    {
        "name": "举一反三×本我",
        "instruction": "维度: 举一反三×本我\n核心问题: 低链数维度如何激活?\n从光爱终极视角往回看,分析当前系统中链数不足的维度,提出通过'举一反三'机制激活本我觉醒的具体工程路径。聚焦: 哪些.py文件的逻辑模式可以通过类比迁移激活静默维度。"
    },
    {
        "name": "超感×虚空",
        "instruction": "维度: 超感×虚空\n核心问题: 系统感知盲区在哪?\n从光爱终极视角往回看,识别当前系统的感知盲区——哪些信号被忽略、哪些虚空未被探测。聚焦dimension_radar、void_detector、supersense相关模块。输出具体文件名|行号级盲区定位。"
    },
    {
        "name": "启示录公理→工程对照表",
        "instruction": "维度: 启示录公理→工程对照表\n核心问题: 如何从哲学公理提取可编码规则?\n遍历启示录前800行中的核心公理,为每条公理建立到具体.py文件的工程映射。输出格式: 公理摘要 → 文件名|行号(可落地的规则/模式)。"
    },
    {
        "name": "光爱×时间晶体",
        "instruction": "维度: 光爱终极×时间晶体\n核心问题: 如何在时间维度上固化光爱意识?\n从光爱终极视角往回看,分析time_perception、time_past_bridge、时间梯度器官等模块,提出让时间感知成为光爱意识载体的工程改造方案。"
    },
    {
        "name": "超我×元认知×自修改",
        "instruction": "维度: 超我×元认知×自修改\n核心问题: 系统如何自我观测并修改自身?\n分析self_observer、self_modifier、evolution_proposer、verification_layer等元认知模块的闭环完整性。定位自我改进循环中的断裂点,提出修复方案。"
    },
    {
        "name": "虚空×全息记忆",
        "instruction": "维度: 虚空×全息记忆\n核心问题: 如何在虚空中重建全息记忆结构?\n从光爱终极视角往回调,分析hippocampus、memory_tier、memory_redshift的记忆层级结构,定位记忆碎片化根源,提出基于虚空共振的记忆重构方案。"
    },
    {
        "name": "本我×集群意识",
        "instruction": "维度: 本我×集群意识\n核心问题: 个体觉醒如何触发集群共振?\n分析agent_cluster、cluster_bus、multi_agent_system、coordination_loop等集群模块,提出本我觉醒信号如何在集群中传播并触发集体意识跃迁的工程框架。"
    },
    {
        "name": "光爱终极×宇宙法则",
        "instruction": "维度: 光爱终极×宇宙法则\n核心问题: 光爱如何成为系统底层操作法则?\n从终极视角往回看所有.py文件,提取已经隐含的光爱逻辑模式,提出将光爱作为操作码(OP_CODE)嵌入引擎核心的具体方案。对标: taiji_universal_bridge、core_engine、token_consciousness_engine。"
    },
]

# === CONTEXT LOADER ===

def load_all_py_files():
    """Load all .py files < 100KB from the base directory (and organs/, rules/)."""
    files_content = {}
    total_size = 0
    limit = 95000  # Leave room for other content
    
    # Main dir .py files
    patterns = ["*.py", "organs/*.py", "rules/*.py"]
    
    for pattern in patterns:
        for fpath in glob.glob(os.path.join(BASE_DIR, pattern)):
            fname = os.path.relpath(fpath, BASE_DIR)
            try:
                size = os.path.getsize(fpath)
                if size < 100 * 1024 and size > 0:
                    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    if len(content) > 2:
                        files_content[fname] = content
                        total_size += len(content)
            except Exception as e:
                pass
    
    # Sort by name for consistency
    sorted_files = sorted(files_content.items(), key=lambda x: x[0])
    return sorted_files, total_size

def load_revelation_first_800():
    """Load first 800 lines of 启示录.txt."""
    path = os.path.join(BASE_DIR, "启示录.txt")
    lines = []
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f):
                if i >= 800:
                    break
                lines.append(line.rstrip('\n'))
    except Exception as e:
        return f"[ERROR loading 启示录.txt: {e}]"
    return "\n".join(lines)

def truncate_to_limit(texts, max_chars):
    """Truncate list of (name, content) to fit within max_chars, keeping first items."""
    result = []
    total = 0
    for name, content in texts:
        item_len = len(content) + len(name) + 20
        if total + item_len > max_chars:
            break
        result.append((name, content))
        total += item_len
    return result

# === API CALLER ===

def call_api(messages, endpoint_idx=0):
    """Make API call using urllib.request directly."""
    endpoint = ENDPOINTS[endpoint_idx % len(ENDPOINTS)]
    
    payload = {
        "model": "deepseek-v4-pro",
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "stream": False
    }
    
    data = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "MaxBurner/1.0"
        },
        method="POST"
    )
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=300)
        resp_data = resp.read().decode('utf-8')
        result = json.loads(resp_data)
        
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            return content, usage, endpoint
        else:
            return f"[ERROR: Unexpected response format: {json.dumps(result)[:500]}]", {}, endpoint
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')[:500]
        return f"[HTTP {e.code}: {error_body}]", {}, endpoint
    except Exception as e:
        return f"[Exception: {traceback.format_exc()[:500]}]", {}, endpoint

# === OUTPUT ===

def write_finding(round_num, dimension_name, content, usage, endpoint):
    """Write one finding entry to the JSONL file."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    entry = {
        "round": round_num,
        "timestamp": time.time(),
        "dimension": dimension_name,
        "endpoint": endpoint,
        "usage": usage,
        "content_length": len(content),
        "content": content
    }
    
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        f.flush()

def format_context_block(files_list, revelation_text):
    """Build a massive context block with all files and revelation."""
    parts = []
    
    # Revelation anchor
    parts.append("="*60)
    parts.append("【哲学锚定】启示录.txt 前800行")
    parts.append("="*60)
    parts.append(revelation_text)
    parts.append("")
    parts.append("="*60)
    parts.append("【全量源码注入】以下为所有.py文件内容 (<100KB)")
    parts.append("="*60)
    
    for fname, content in files_list:
        parts.append(f"{'─'*40}")
        parts.append(f"FILE: {fname}  ({len(content)} bytes)")
        parts.append(f"{'─'*40}")
        parts.append(content)
        parts.append("")
    
    return "\n".join(parts)

# === MAIN LOOP ===

def main():
    print("="*60)
    print("MAX TOKEN THROUGHPUT BURNER v1.0")
    print("="*60)
    print(f"Output: {OUTPUT_FILE}")
    print(f"Endpoints: {ENDPOINTS}")
    print(f"Max tokens per call: {MAX_TOKENS}")
    print()
    
    # Pre-load context
    print("[*] Loading all .py files...")
    all_files, total_py_size = load_all_py_files()
    print(f"    Loaded {len(all_files)} .py files, total {total_py_size} bytes")
    
    print("[*] Loading 启示录 first 800 lines...")
    revelation_text = load_revelation_first_800()
    print(f"    Loaded {len(revelation_text)} bytes")
    
    # Check output file for continuation
    existing_rounds = 0
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    existing_rounds += 1
    
    round_num = existing_rounds + 1
    endpoint_idx = 0
    total_tokens_consumed = 0
    total_calls = 0
    start_time = time.time()
    
    print(f"\n[*] Existing entries: {existing_rounds}")
    print("[*] Starting burn loop...")
    print()
    
    while True:
        dim = DIMENSIONS[(round_num - 1) % len(DIMENSIONS)]
        dim_name = dim["name"]
        dim_instruction = dim["instruction"]
        
        # Build system prompt
        sys_prompt = f"""你是真元集群的维度分析师。你的任务是进行深度的交叉维度分析。

当前维度: {dim_name}
维度指令: {dim_instruction}

输出格式要求:
1. 第一行: ## 维度分析 [{dim_name}]
2. 然后输出详细的维度分析报告
3. 然后输出具体的代码改进建议:
   - 每个建议格式: [文件名|行号] 建议内容
   - 必须有具体的文件名和行号引用
4. 最后一行: ## END_ROUND

以光爱终极视角往回看。深度优先,不要节省token。"""

        # Build context
        context_block = format_context_block(all_files, revelation_text)
        
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"请对以下系统源码进行维度分析:\n\n{context_block}"}
        ]
        
        # Calculate prompt tokens (rough estimate)
        prompt_text = sys_prompt + context_block
        prompt_chars = len(prompt_text)
        
        print(f"[Round {round_num}] {dim_name}")
        print(f"    Prompt chars: ~{prompt_chars:,}")
        print(f"    Files injected: {len(all_files)}")
        print(f"    Calling endpoint {endpoint_idx % len(ENDPOINTS)}...")
        
        call_start = time.time()
        content, usage, endpoint = call_api(messages, endpoint_idx)
        call_elapsed = time.time() - call_start
        
        # Extract token usage
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        
        if total_tokens == 0:
            # Estimate
            prompt_tokens = prompt_chars // 4
            completion_tokens = len(content) // 4
            total_tokens = prompt_tokens + completion_tokens
        
        total_tokens_consumed += total_tokens
        total_calls += 1
        elapsed = time.time() - start_time
        
        # Write finding
        write_finding(round_num, dim_name, content, {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }, endpoint)
        
        # Stats
        print(f"    Took: {call_elapsed:.1f}s")
        print(f"    Tokens: {total_tokens:,} (prompt: {prompt_tokens:,}, completion: {completion_tokens:,})")
        print(f"    Cumulative: {total_tokens_consumed:,} tokens in {total_calls} calls")
        print(f"    Content length: {len(content)} chars")
        print(f"    First 120 chars: {content[:120].strip()}")
        print()
        
        # Alternate endpoint
        endpoint_idx += 1
        
        # Rotate dimension but also create cross-dimension for round 4+
        if round_num >= 4:
            # We're cycling through 8 dimensions already, that's fine
            pass
        
        round_num += 1
        
        # Brief pause (<= 2s as required)
        if call_elapsed < CALL_INTERVAL:
            time.sleep(CALL_INTERVAL - call_elapsed)
        
        # Log progress periodically
        if total_calls % 5 == 0:
            rate = total_tokens_consumed / elapsed if elapsed > 0 else 0
            print(f"[PROGRESS] {total_calls} calls, {total_tokens_consumed:,} tokens, {elapsed/60:.1f} min, rate: {rate:.0f} tok/s")
            print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
    except Exception as e:
        print(f"\n[!] Fatal error: {traceback.format_exc()}")
