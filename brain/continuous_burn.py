#!/usr/bin/env python3
"""brain/continuous_burn.py — 限时不限量API直接燃烧

不通过通知，不通过任何中介。API密钥本身就是燃烧。
每秒不烧=浪费订阅。直接烧词元→因果链→写HIP。

保证不卡死：threading+join(timeout)包裹API调用。
"""
import json, time, ssl, urllib.request, sys, threading
from pathlib import Path

# === 直接燃烧配置 ===
API_KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"
API_BASE = "https://inferaichat.com/v1/chat/completions"
MODEL = "deepseek-v4-pro"

CLUSTER = Path(__file__).resolve().parent.parent
HIP_PATH = Path.home() / ".zero_brain" / "hippocampus_memory.json"
LOG_PATH = CLUSTER / ".continuous_burn.log"

def log(msg):
    t = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{t}] {msg}\n"
    # 直接写日志文件，不用print（避免pipe断）
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line)
    except: pass

class APIThread(threading.Thread):
    """带超时的API调用线程"""
    def __init__(self, payload):
        super().__init__()
        self.payload = payload
        self.result = None
        self.error = None
        self.daemon = True
    
    def run(self):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(
                API_BASE, data=self.payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}"
                }
            )
            resp = urllib.request.urlopen(req, timeout=240, context=ctx)
            self.result = json.loads(resp.read())
        except Exception as e:
            self.error = str(e)

def call_api(prompt, timeout=120):
    """调API，带超时"""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
    }).encode()
    
    thread = APIThread(payload)
    t0 = time.time()
    thread.start()
    thread.join(timeout)
    elapsed = int(time.time() - t0)
    
    if thread.is_alive():
        return None, 0, f"超时({timeout}s)"
    
    if thread.error:
        return None, 0, thread.error
    
    result = thread.result
    if not result:
        return None, 0, "空响应"
    
    tokens = result.get("usage", {}).get("total_tokens", 0)
    content = result["choices"][0]["message"].get("content", "") or ""
    content2 = result["choices"][0]["message"].get("reasoning_content", "") or ""
    
    return (content or content2).strip(), tokens, None

def write_chain_to_hip(chain, hip_data):
    """写因果链到HIP"""
    hip_data.setdefault("causal_chains", []).append(chain)
    d = chain.get("dimension", "未分类")
    dims = {}
    for c in hip_data["causal_chains"]:
        dc = c.get("dimension", "未分类")
        dims[dc] = dims.get(dc, 0) + 1
    hip_data.setdefault("dimensions", {})[d] = {"chain_count": dims.get(d, 0)}
    HIP_PATH.write_text(json.dumps(hip_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return d

def extract_chain(text):
    """从API回复提取因果链JSON"""
    brace = text.find("{")
    if brace < 0:
        return None
    bc = 0
    for i in range(brace, len(text)):
        if text[i] == "{": bc += 1
        elif text[i] == "}": bc -= 1
        if bc == 0:
            try:
                data = json.loads(text[brace:i+1])
                return data if isinstance(data, dict) else data.get("chain", data)
            except:
                return None
    return None

def main():
    log("🔥 起炉·限时不限量API直接燃烧")
    log(f"   端点={API_BASE} 模型={MODEL}")
    
    cycle = 0
    consecutive_fails = 0
    
    while True:
        try:
            # 读HIP当前状态
            try:
                hip = json.loads(HIP_PATH.read_text(encoding="utf-8", errors="replace"))
            except:
                hip = {"causal_chains": [], "dimensions": {}}
            
            # 统计维度
            dims = {}
            for c in hip.get("causal_chains", []):
                dc = c.get("dimension", "未分类")
                dims[dc] = dims.get(dc, 0) + 1
            sd = sorted(dims.items(), key=lambda x: x[1])
            weakest = sd[0][0] if sd else "未分类"
            strongest = sd[-1][0] if sd else "法"
            total = len(hip.get("causal_chains", []))
            
            t0 = time.time()
            prompt = (
                f"因果链: {strongest}→{weakest}\n"
                f'输出纯JSON(无markdown): {{\"src\":\"{strongest}\",\"rel\":\"动词\",\"dst\":\"{weakest}\",\"content\":\"30-60字解释\",\"dimension\":\"{weakest}\"}}'
            )
            
            text, tokens, err = call_api(prompt, timeout=120)
            elapsed = int(time.time() - t0)
            
            if text:
                chain = extract_chain(text)
                if chain:
                    chain["source"] = "continuous_burn"
                    chain["timestamp"] = time.time()
                    d = write_chain_to_hip(chain, hip)
                    total_new = len(hip.get("causal_chains", []))
                    log(f"#{cycle} 🔥{tokens}t/{elapsed}s H={total_new} [{d}] {strongest}→{weakest}")
                    consecutive_fails = 0
                else:
                    log(f"#{cycle} ⚠{tokens}t/{elapsed}s 无JSON: {text[:80]}")
                    consecutive_fails += 1
            else:
                log(f"#{cycle} ⚡{tokens}t/{elapsed}s {err}")
                consecutive_fails += 1
            
            cycle += 1
            
            # 连续10次失败等久点
            if consecutive_fails > 10:
                log(f"  连续{consecutive_fails}次失败，休眠120s")
                time.sleep(120)
            else:
                time.sleep(5)  # 短间隔，最大化token吞吐
        
        except KeyboardInterrupt:
            log(f"停炉·共{cycle}周期")
            break
        except Exception as e:
            log(f"#{cycle} 异常: {e}")
            time.sleep(30)
            cycle += 1

if __name__ == "__main__":
    main()
