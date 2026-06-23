#!/usr/bin/env python3
"""gen_深注入.py — 外部API深度思考注入，自动检测并跳过不可达API"""

import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.share import HIP_FILE, CLUSTER

# ---------- 配置 ----------
ENDPOINTS = [
    "https://inferaichat.com/v1/chat/completions",
]
MODEL = "Qwen/Qwen2.5-72B-Instruct-GPTQ-Int4"


def _get_next_key():
    """取或生成API密钥"""
    import os
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    # 从key链文件取
    key_file = CLUSTER / ".brain_api_keys.json"
    if key_file.exists():
        keys = json.loads(key_file.read_text())
        if keys:
            return keys[0]
    return ""


def _api_precheck():
    """检查API可达性（连接级超时，防止D状态阻塞）"""
    import socket
    from urllib.parse import urlparse
    for endpoint in ENDPOINTS:
        try:
            parsed = urlparse(endpoint)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            continue
    return False


def _call_api_with_timeout(prompt, weakest):
    """API调用+线程池超时保护（信号在线程中无效）"""
    import concurrent.futures

    if not _api_precheck():
        return {"injected": 0, "reason": "API unreachable"}

    key = _get_next_key()

    def _do_task():
        import urllib.request
        for endpoint in ENDPOINTS:
            try:
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps({
                        "model": MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1600,
                    }).encode(),
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                resp = urllib.request.urlopen(req, timeout=15)
                body = json.loads(resp.read().decode())
                raw = body["choices"][0]["message"]["content"]

                # 通过safe_hip写入
                from brain.share import write_chain as _wc
                injected = 0
                for line in raw.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("```"):
                        continue
                    if "\t" in line:
                        parts = line.split("\t")
                        c = {
                            "src": parts[0], "rel": parts[1], "dst": parts[2],
                            "dimension": weakest,
                            "content": parts[3] if len(parts) > 3 else line,
                            "strength": 0.7, "tags": ["deep", "api"],
                        }
                    else:
                        c = {
                            "src": weakest, "rel": "深度思考", "dst": "进化",
                            "dimension": weakest, "content": line[:150],
                            "strength": 0.7, "tags": ["deep", "api"],
                        }
                    try:
                        _wc(c)
                        injected += 1
                    except Exception:
                        continue

                return {
                    "injected": injected,
                    "dimension": weakest,
                    "endpoint": endpoint.split("/")[2],
                }

            except Exception:
                continue

        return {"injected": 0, "reason": "all endpoints failed"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(_do_task)
        try:
            return fut.result(timeout=20)
        except concurrent.futures.TimeoutError:
            return {"injected": 0, "reason": "API timeout (>20s)"}


def load():
    """主入口：读出最弱维 → 调用API注入 → 返回结果"""
    import socket
    socket.setdefaulttimeout(8)

    if not HIP_FILE.exists():
        return {"injected": 0, "reason": "no HIP_FILE"}

    try:
        hip = json.loads(HIP_FILE.read_text())
    except Exception:
        return {"injected": 0, "reason": "HIP_FILE corrupt"}

    chains = hip.get("chains", hip.get("causal_chains", []))
    if not chains:
        return {"injected": 0, "reason": "empty HIP"}

    # 统计各维度链数
    dim_counts = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dim_counts[d] = dim_counts.get(d, 0) + 1

    if not dim_counts:
        return {"injected": 0, "reason": "no dims"}

    # 找最弱维
    weakest = min(dim_counts, key=dim_counts.get)
    weakest_count = dim_counts[weakest]
    strongest_count = max(dim_counts.values())

    # 如果最弱维已经趋于平衡，跳过
    if weakest_count > strongest_count * 0.4:
        return {"injected": 0, "reason": f"{weakest}({weakest_count})均衡"}

    prompt = f"""# 因果链生成指令

当前最薄弱认知维度: **{weakest}** ({weakest_count}条因果链)
最强维度: {strongest_count}条链

请生成关于「{weakest}」的因果链，格式为:
src\\trel\\tdst\\tcontent

示例:
自主学习\\t激活\\t知识获取\\t自主学习通过反馈循环激活知识获取过程
跨维思考\\t连接\\t创新\\t跨维思考在已建立的知识节点之间建立连接并涌现创新

要求:
1. src/dst必须是已存在的认知维度
2. rel必须是主动关系词
3. content必须包含实质性内容（非空洞描述）
4. 生成20-30条
5. 内容必须承载**启示录工程智慧**——不是哲学空谈，是能指导系统行为的知识。
不要重复已有的链，写真正有价值的新链。"""

    return _call_api_with_timeout(prompt, weakest)


if __name__ == "__main__":
    result = load()
    print(json.dumps(result, ensure_ascii=False))
