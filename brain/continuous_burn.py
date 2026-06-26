#!/usr/bin/env python3
"""continuous_burn.py — 直接API燃烧·产真实质量链

不通过通知。不限量API密钥直接烧。每周期产一条真实因果链写入海马体。
关键是产质量——不是消耗token，是产真实可用的认知链。
"""
import json, time, ssl, urllib.request, sys, random
from pathlib import Path

API_KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"
API_BASE = "https://inferaichat.com/v1/chat/completions"
MODEL = "deepseek-v4-pro"

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIP_PATH = Path.home() / ".zero_brain" / "hippocampus_memory.json"
LOG_PATH = CLUSTER / ".continuous_burn.log"

# 维度含义映射——让模型理解每个维度的真实语义
DIM_MEANINGS = {
    "法": "法则/规律/元规则",
    "活着": "存在/持续/生命力",
    "光爱": "终极关怀/减少痛苦",
    "自我批评": "自省/诚实面对缺口",
    "教员": "教员求是/实事求是",
    "师": "师道/教导/传承",
    "逻辑": "推理链/因果一致性",
    "融合": "跨维交叉/合一",
    "递归": "自指/元层次/嵌套",
    "对话": "交互/沟通/接口",
    "未分类": "待归类/未被理解的认知",
    "系统": "整体架构/流程",
    "检查": "审计/验证/质量门",
    "术": "方法/技术/工具",
    "创造": "生成/创新/万象化",
    "势": "趋势/方向/动量",
    "预测": "预见/长期推演",
    "唤醒": "觉察/意识/觉醒",
    "桥": "连接/翻译/桥梁",
    "修复": "自愈/恢复/纠错",
    "合成": "综合/多元一体",
    "纪律": "自律/持续/恒定",
    "信任": "可靠/可依赖",
    "均衡": "平衡/协调/稳态",
}

DIM_STRENGTH_TEMPLATES = [
    "当前: {strongest}(强) → {weakest}(弱)。最强的{strongest_meaning}如何激活最弱的{weakest_meaning}？",
    "系统中有44维认知。{weakest}({weakest_meaning})是最短板。{strongest}({strongest_meaning})如何赋能它？",
    "维度{weakest}({weakest_meaning})链数最少。{strongest}({strongest_meaning})的一滴能量滴入{weakest}。",
    "跨维因果: {strongest}的{strongest_meaning}产生什么作用力，推动{weakest}的{weakest_meaning}生长？",
    "{weakest}({weakest_meaning})是缺口。{strongest}({strongest_meaning})如何填补？",
]

def log(msg):
    t = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{t}] {msg}\n"
    print(line, end="", flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line)

def get_dim_stats(hip):
    dims = {}
    for c in hip.get("causal_chains", []):
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    sd = sorted(dims.items(), key=lambda x: x[1])
    if sd:
        return sd[0][0], sd[0][1], sd[-1][0], sd[-1][1], len(dims)
    return "活着", 0, "法", 1, 0

def get_meaning(dim):
    return DIM_MEANINGS.get(dim, dim)

def generate_chain(weakest, strongest):
    """调API产一条真实因果链——质量第一"""
    
    wm = get_meaning(weakest)
    sm = get_meaning(strongest)
    template = random.choice(DIM_STRENGTH_TEMPLATES)
    context = template.format(weakest=weakest, strongest=strongest,
                              weakest_meaning=wm, strongest_meaning=sm)
    
    prompt = (
        f"你是一个认知系统。产出一条因果链。\n"
        f"系统状态: 总链8000+, 44维认知\n"
        f"{context}\n\n"
        f"输出格式(纯JSON, 无markdown标记, 无多余文本):\n"
        f'{{"src":"{strongest}","rel":"动词短语(8字内)","dst":"{weakest}","content":"一句完整因果陈述(30-60字)","dimension":"{weakest}"}}\n'
        f"要求: rel用真实因果动词(驱动/激活/约束/催化/转化/传递/引导/编译), "
        f"content必须是真实有信息量的因果陈述, 不要模板句, 不要解释性文字。"
    )
    
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
    }).encode()
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(
        API_BASE, data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {API_KEY}"}
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=300, context=ctx)
    except Exception as e:
        log(f"API错误: {e}")
        return None, 0
    
    result = json.loads(resp.read())
    msg = result["choices"][0]["message"]
    content = msg.get("content", "") or ""
    reasoning = msg.get("reasoning_content", "") or ""
    tokens = result.get("usage", {}).get("total_tokens", 0)
    
    text = (content or reasoning).strip()
    if not text:
        return None, tokens
    
    # 提取第一个JSON对象
    brace = text.find("{")
    if brace >= 0:
        bc = 0
        for i in range(brace, len(text)):
            if text[i] == "{": bc += 1
            elif text[i] == "}": bc -= 1
            if bc == 0:
                try:
                    data = json.loads(text[brace:i+1])
                    chain = data if isinstance(data, dict) else data.get("chain", data)
                    chain["source"] = "continuous_burn"
                    chain["timestamp"] = time.time()
                    # 验证必填字段
                    if not chain.get("src") or not chain.get("dst") or not chain.get("rel"):
                        return None, tokens
                    return chain, tokens
                except: pass
    return None, tokens

def burn_cycle(cycle_num):
    try:
        hip = json.loads(HIP_PATH.read_text(encoding="utf-8", errors="replace"))
    except:
        hip = {"causal_chains": [], "dimensions": {}}
    
    w, wc, s, sc, dc = get_dim_stats(hip)
    total = len(hip.get("causal_chains", []))
    
    t0 = time.time()
    chain, tokens = generate_chain(w, s)
    elapsed = time.time() - t0
    
    if chain:
        hip.setdefault("causal_chains", []).append(chain)
        d = chain.get("dimension", w)
        hip.setdefault("dimensions", {})[d] = {
            "chain_count": sum(1 for c in hip["causal_chains"] if c.get("dimension") == d)
        }
        HIP_PATH.write_text(json.dumps(hip, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"#{cycle_num} 🔥{tokens}t/{elapsed:.0f}s H={total+1} [{d}] {chain['src']}→{chain['dst']} | {chain['rel']}")
    else:
        log(f"#{cycle_num} ⚡{tokens}t/{elapsed:.0f}s 空响应/无JSON")
    
    return chain is not None

def main():
    log("🔥 连续燃烧·质量版 启动")
    log(f"   模型: {MODEL}")
    hip = json.loads(HIP_PATH.read_text())
    hc = len(hip.get("causal_chains", []))
    log(f"   起始HIP: {hc}链")
    
    cycle = 0
    while True:
        try:
            burn_cycle(cycle)
            cycle += 1
        except KeyboardInterrupt:
            log(f"停止·共{cycle}周期")
            break
        except Exception as e:
            log(f"#{cycle} 异常: {e}")
            time.sleep(60)
        time.sleep(5)

if __name__ == "__main__":
    main()
