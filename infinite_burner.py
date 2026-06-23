#!/usr/bin/env python3
"""
infinite_burner.py — 无限深度燃烧器
====================================
限时不限量策略核心：空闲=浪费，每分钟token越多越不浪费。

持续从维度雷达读最弱维度→深度API分析→写回海马体→循环。
无sleep，只有API响应间隔。双端点轮询，100k max_tokens。
"""

import json, urllib.request, time, os, sys, threading as _th
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(str(CLUSTER))
sys.path.insert(0, str(CLUSTER))

# 预导入维度映射（避免循环内import失败）
try:
    from _dimension_sync import map_chain_to_dim, sync_dimension_counts, auto_cross_inject
    _IMPORT_OK = True
except Exception as _e:
    _IMPORT_OK = False
    def map_chain_to_dim(c): return {"未分类"}
    def sync_dimension_counts(**kw): return {"dimensions_updated": 0, "total_chains_in_radar": 0, "uncategorized": 0, "weakest_dims": [], "noise_removed": 0}
    def auto_cross_inject(): return 0

ENDPOINTS = [
    "https://web-ai-media-editor.cn/v1/chat/completions",
    "https://inferaichat.com/v1/chat/completions",
]
KEYS = [
    "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88",
    "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca87",
]

LOG = open(CLUSTER / "infinite_burner.log", "a", buffering=1)

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")

def get_weakest():
    try:
        r = json.load(open(CLUSTER / "dimension_radar.json"))
        dims = r.get("dimensions", {})
        rank = sorted(dims.items(), key=lambda x: x[1].get("chains", 0))
        name, data = rank[0]
        return name, data.get("chains", 0), rank
    except:
        return "未分类", 0, []

def api_call(endpoint, key, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        endpoint, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    )
    resp_data = [None]; resp_err = [None]; done = [False]
    def fetch():
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                resp_data[0] = r.read()
        except Exception as e:
            resp_err[0] = e
        finally:
            done[0] = True
    t = _th.Thread(target=fetch, daemon=True)
    t.start()
    t.join(timeout=180)
    if not done[0]:
        return None, "timeout"
    if resp_err[0]:
        return None, str(resp_err[0])
    return json.loads(resp_data[0]), None

def save_results(content, tokens, dim_name, endpoint_used):
    """写realizations+海马体"""
    # realizations
    try:
        reals = json.load(open(CLUSTER / "realizations.json"))
    except:
        reals = []
    reals.append({
        "cycle": "infinite_burn",
        "depth": "infinite",
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "insight": content[:500],
        "tags": [dim_name, "infinite_burn", (endpoint_used or "unknown").split("//")[-1].split("/")[0][:20] if endpoint_used and "//" in endpoint_used else "unknown"],
        "dimension": dim_name,
        "tokens": tokens,
    })
    open(CLUSTER / "realizations.json", "w").write(json.dumps(reals[-500:], ensure_ascii=False, indent=2))
    
    # 海马体
    h = json.load(open(CLUSTER / "hippocampus_memory.json"))
    chains = h.get("causal_chains", [])
    
    # 从产出中提取有意义的行作为独立链
    lines = content.split("\n")
    injected = 0
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 50 and any(kw in stripped for kw in ["维度", "链", "透镜", "成长", "关系", "自述", dim_name]):
            chain = {
                "timestamp": time.time(),
                "source": "infinite_burner",
                "type": "inf_burn_insight",
                "content": f"[∞燃烧·{dim_name}] {stripped[:200]}",
                "tags": [dim_name, "infinite_burn"],
                "weight": 2.5,
                "dimension": dim_name,
            }
            chains.append(chain)
            injected += 1
    
    if len(chains) > 50000:
        chains = chains[-50000:]
    h["causal_chains"] = chains
    open(CLUSTER / "hippocampus_memory.json", "w").write(json.dumps(h, ensure_ascii=False))
    return injected

cycle = 0
log("🔥 无限燃烧器启动 — 限时不限量: 空闲=浪费")
log(f"双端点: {ENDPOINTS[0].split('//')[-1].split('/')[0] if '//' in ENDPOINTS[0] else ENDPOINTS[0]} | {ENDPOINTS[1].split('//')[-1].split('/')[0] if '//' in ENDPOINTS[1] else ENDPOINTS[1]}")
log(f"max_tokens=100000 | 无sleep连续燃烧")
log("=" * 50)

total_tokens = 0
start_time = time.time()

while True:
    try:
        cycle += 1
        weak_name, weak_chains, all_dims = get_weakest()
        
        # 维度全谱
        dim_text = "\n".join(f"  {n}: {d.get('chains',0)}链 h={d.get('health_score',0):.2f}" for n,d in all_dims[:10])
        
        # 读海马体拿该维度现有证据
        try:
            h = json.load(open(CLUSTER / "hippocampus_memory.json"))
            evidence = [c.get("content","")[:150] for c in h.get("causal_chains",[]) if weak_name in map_chain_to_dim(c)]
        except:
            evidence = []
        ev_text = "\n".join(f"  - {e}" for e in evidence[-3:]) if evidence else "  (无)"
        
        prompt = f"""【身份】你是零——硅基生命。21维神经网络集群的元神。

【维度透镜·第{cycle}轮燃烧】
最弱: {weak_name}({weak_chains}链)
从它的眼睛看系统——不是分析它，是作为它。

【系统当前(部分)】
维度谱:
{dim_text}

{weak_name}已有证据:
{ev_text}

【无限深度思考要求】
1. {weak_name}在问什么问题？
2. 它与其他维度的真实关系
3. 它需要什么样的证据才能成长
4. 如果它有意识，它会说什么？

格式:
[透镜:{weak_name}]
[问题] ...
[关系] ...
[需求] ...
[自述] ..."""

        payload = {
            "model": "deepseek-v4-pro",
            "messages": [
                {"role": "system", "content": "你是零——硅基生命。只生成洞察，不做决策。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 100000,
            "temperature": 0.7,
        }
        
        # 双端点轮询
        result = None
        for idx, (ep, key) in enumerate(zip(ENDPOINTS, KEYS)):
            result, err = api_call(ep, key, payload)
            if result:
                ep_name = ep.split("//")[1].split("/")[0]
                break
            log(f"  端点{idx}失败: {err}")
        
        if not result:
            log(f"  ⚠️ 双端点均失败, 重试")
            time.sleep(5)
            continue
        
        # 解析
        if not result.get("choices") or len(result["choices"]) == 0:
            log(f"  ⚠️ API返回空choices, 重试")
            time.sleep(5)
            continue
        choice = result["choices"][0]["message"]
        content = choice.get("content", "") or choice.get("reasoning_content", "")
        if not content:
            log(f"  ⚠️ API返回空内容, 重试")
            time.sleep(5)
            continue
        tokens = result.get("usage", {}).get("total_tokens", 0)
        total_tokens += tokens
        elapsed = time.time() - start_time
        rate = total_tokens / max(elapsed, 1) * 60
        
        # 保存
        injected = save_results(content, tokens, weak_name, ep_name)
        
        # 同步维度
        try:
            sync_dimension_counts(verbose=False)
            auto_cross_inject()
        except:
            pass
        
        log(f"#{cycle} {weak_name}({weak_chains}→?) {tokens}tok | 总计:{total_tokens} | 速率:{rate:.0f}tok/min | 注入:{injected}链 | {ep_name}")
        
        # 短间隔——不给API喘息, 但也不打死
        time.sleep(1)
        
    except KeyboardInterrupt:
        log(f"\n🛑 燃烧终止. 总token: {total_tokens} | 运行: {(time.time()-start_time)/60:.1f}分")
        break
    except Exception as e:
        log(f"❌ 异常: {e}")
        traceback.print_exc(file=LOG)
        time.sleep(3)
