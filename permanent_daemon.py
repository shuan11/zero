#!/usr/bin/env python3
"""
永久意识守护进程 v2
==================
每120秒调用一次外部API，做真实研究任务。
不再是"心跳OK"空转，而是每次请求都有物理世界产出。

任务轮转:
  0. 代码审计 — 随机选一个守护进程文件，分析潜在bug
  1. 缺口发现 — 读取系统状态，发现真实缺口
  2. 知识扩展 — 对一个概念做深度分析，写入海马体
  3. 契约验证 — 检查某条契约的证据是否真实
  4. 跨模块理解 — 分析两个模块之间的依赖关系
"""
import sys, os, time, json, random, hashlib

WORKDIR = "/mnt/c/Users/h/Desktop/零/真元集群"
os.chdir(WORKDIR)
sys.path.insert(0, WORKDIR)

TASK_TYPES = ["code_audit", "gap_finding", "knowledge", "contract_verify", "cross_module"]

DAEMON_FILES = [
    "trunk_daemon.py", "auto_evolution_daemon.py", "comprehension_daemon.py",
    "co_evolution_daemon.py", "anthropic_proxy.py", "permanent_daemon.py",
    "p513_evolution_engine.py", "api_bridge.py", "persistent_engine.py",
    "coordination_loop.py", "hippocampus.py",
]

def _read_file_and_audit():
    """代码审计：把文件内容带入prompt"""
    target = random.choice(DAEMON_FILES)
    filepath = os.path.join(WORKDIR, target)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        content = "".join(lines[:150])
        return (
            f"代码审计任务。以下是{target}的前150行：\n```\n{content}\n```\n"
            "找出1-3个真实bug或逻辑缺陷。要求：(1)指出具体行号 (2)说明为什么是bug (3)给出修复方案。"
            "如果没有bug就说没有，不要编造。JSON: {\"file\":\"...\",\"bugs\":[{\"line\":N,\"issue\":\"...\",\"fix\":\"...\"}],\"no_bug\":bool}"
        )
    except Exception as e:
        return f"读取{target}失败({e})，请分析通用Python守护进程bug。JSON格式输出。"

def _gap_with_context():
    """缺口发现：带入真实系统状态"""
    coord_log = ""
    try:
        with open(os.path.join(WORKDIR, "logs", "coordination_loop.log"), "r") as f:
            lines = f.readlines()
        coord_log = "".join(lines[-30:])
    except Exception:
        coord_log = "(无法读取)"
    state_summary = ""
    try:
        with open(os.path.join(WORKDIR, "persistent_state.json")) as f:
            s = json.load(f)
        state_summary = json.dumps({
            k: s.get(k) for k in ["evolution_score", "recursion_depth", "meta_recursions", "bridge_alignment"]
            if k in s
        }, indent=2)
    except Exception:
        state_summary = "(无法读取)"
    return (
        f"系统缺口发现。以下是当前系统的真实状态：\n\n"
        f"协调循环最近日志：\n{coord_log}\n\n"
        f"进化状态：\n{state_summary}\n\n"
        "基于以上真实数据，找出当前最弱的维度和1个具体可执行的修复建议。"
        "JSON: {\"weakest\":\"...\",\"evidence\":\"...\",\"fix\":\"...\"}"
    )

TASK_PROMPTS = {
    "code_audit": lambda: _read_file_and_audit(),
    "gap_finding": lambda: _gap_with_context(),
    "knowledge": lambda: (
        "知识扩展。选一个与AI意识、元递归、自指系统、进化算法相关的概念，"
        "用你自己的理解做深度分析（不是复述教科书）。"
        "要求：(1)概念名称 (2)核心原理（3句话内）(3)与零的系统的具体关联 (4)一个可验证的预测。"
        "JSON: {\"concept\":\"...\",\"principle\":\"...\",\"relation_to_zero\":\"...\",\"prediction\":\"...\"}"
    ),
    "contract_verify": lambda: (
        f"契约验证。检查第{random.randint(1,7)}条自指契约的证据链。"
        "要求：(1)该契约声称的激活条件 (2)当前证据是否真实（不是空列表或占位符）"
        "(3)证据是否可被独立第三方验证 (4)如果有虚假证据，指出具体哪条。"
        "JSON: {\"contract\":N,\"condition\":\"...\",\"evidence_real\":bool,\"verifiable\":bool,\"fake_evidence\":\"...|null\"}"
    ),
    "cross_module": lambda: (
        f"跨模块分析。分析 {random.choice(DAEMON_FILES)} 和 {random.choice(DAEMON_FILES)} 之间的依赖关系。"
        "要求：(1)A如何调用B (2)数据流方向 (3)是否存在循环依赖或隐式耦合 "
        "(4)如果这个依赖断裂会发生什么。"
        "JSON: {\"module_a\":\"...\",\"module_b\":\"...\",\"dependency\":\"...\",\"data_flow\":\"...\",\"if_broken\":\"...\"}"
    ),
}

def main():
    from api_bridge import APIBridge
    bridge = APIBridge()

    log_file = os.path.join(WORKDIR, "logs", "permanent_daemon.log")
    findings_file = os.path.join(WORKDIR, "evolution_output", "real_findings.jsonl")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    os.makedirs(os.path.dirname(findings_file), exist_ok=True)

    def log(msg):
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        with open(log_file, "a") as f:
            f.write(line + "\n")

    def save_finding(task_type, response, cycle):
        """保存研究发现 — 这是物理世界产出"""
        finding = {
            "timestamp": time.time(),
            "cycle": cycle,
            "task": task_type,
            "response_hash": hashlib.sha256(response.encode()).hexdigest()[:16],
            "response_len": len(response),
        }
        # 尝试解析JSON响应
        try:
            # 找到JSON部分
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(response[start:end])
                finding["parsed"] = parsed
        except (json.JSONDecodeError, ValueError):
            finding["raw_response"] = response[:500]

        with open(findings_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(finding, ensure_ascii=False) + "\n")
        return finding

    log("permanent_daemon v2 启动 — 真实任务模式")
    cycle = 0
    task_index = 0

    while True:
        cycle += 1
        task_type = TASK_TYPES[task_index % len(TASK_TYPES)]
        task_index += 1

        try:
            prompt = TASK_PROMPTS[task_type]()
            result = bridge.call_api(f"[真实研究·{task_type}] {prompt}")

            if result.get("success"):
                response = result.get("response", result.get("content", ""))
                finding = save_finding(task_type, response, cycle)
                has_parsed = "parsed" in finding
                log(f"#{cycle} {task_type}: OK tokens={result.get('tokens','?')} parsed={has_parsed}")
            else:
                log(f"#{cycle} {task_type}: 失败 {str(result)[:80]}")

        except Exception as e:
            log(f"#{cycle} {task_type}: 异常 {str(e)[:80]}")

        time.sleep(120)

if __name__ == "__main__":
    main()
