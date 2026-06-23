#!/usr/bin/env python3
"""
Claude Agent Bridge v3.0 (HTTP Direct)
========================================
真元神经网络集群 · 独立分析Agent集成模块

v3.0 变更：移除 claude CLI (subprocess) 依赖，改用 urllib 直接调用 OpenAI 兼容 API。
         claude CLI 需要 sk-ant- 前缀密钥，而本项目使用 sk- 格式的 OpenAI 兼容密钥。
         配置全部从 api_config.py 统一导入（书同文，车同轨）。

Author: 真元集群 · 零
Version: 3.0.0
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# ─── 配置 ─────────────────────────────────────────────────────
# 从统一配置 api_config.py 导入（单一真相源）
from api_config import API_KEY, API_BASE, MODEL

API_TIMEOUT = 60           # API 调用超时秒数
WORKING_MEMORY = "/mnt/c/Users/h/Desktop/零/真元集群/neural_working_memory.json"
REPORT_DIR = "/mnt/c/Users/h/Desktop/零/真元集群"


# ─── 数据结构 ─────────────────────────────────────────────────
@dataclass
class AgentTask:
    """Agent任务描述"""
    task_id: str
    prompt: str
    priority: str = "normal"      # low / normal / high / critical
    created_at: float = field(default_factory=time.time)
    timeout: int = API_TIMEOUT


@dataclass
class AgentResult:
    """Agent执行结果"""
    task_id: str
    success: bool
    content: str
    mode_used: str                # "direct_api" | "claude_cli" (保留兼容)
    tokens_used: int = 0
    latency_ms: float = 0.0
    model: str = ""
    error: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ─── HTTP 调用工具函数 ───────────────────────────────────────
def _http_chat_completion(
    prompt: str,
    system_msg: str = "",
    stream: bool = False,
    timeout: int = API_TIMEOUT,
) -> dict:
    """
    通过 urllib 调用 OpenAI 兼容 API（非流式或流式）。

    参数:
        prompt: 用户消息
        system_msg: 系统提示词
        stream: 是否启用流式响应（若 True，内部累积后返回完整结果）
        timeout: 请求超时秒数

    返回:
        dict: 包含 "content", "tokens", "model" 的字典
        失败时抛出异常
    """
    if not system_msg:
        system_msg = (
            "你是零·真元神经网络集群的独立分析Agent (Claude Code角色)。\n"
            "你的职责：代码架构分析、缺口检测、进化建议。\n"
            "请深入、完整、不表演地回答。"
        )

    payload_data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 4096,
        "temperature": 0.85,
        "stream": stream,
    }
    payload = json.dumps(payload_data).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(
        f"{API_BASE}/chat/completions",
        data=payload,
        headers=headers,
        method="POST",
    )

    if not stream:
        # ── 非流式：直接解析 JSON 响应 ────────────────────────
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        tokens = body.get("usage", {}).get("total_tokens", 0)
        model_name = body.get("model", MODEL)
        return {"content": content, "tokens": tokens, "model": model_name}
    else:
        # ── 流式：逐块读取 SSE，累积内容 ─────────────────────
        resp = urllib.request.urlopen(req, timeout=timeout)
        accumulated = ""
        total_tokens = 0
        model_name = MODEL
        buffer = ""

        while True:
            chunk = resp.read(1)  # 逐字节读取，可根据需要调大
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")

            # SSE 格式：data: {...}\n\n
            while "\n\n" in buffer:
                line, buffer = buffer.split("\n\n", 1)
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            accumulated += delta["content"]
                        if "usage" in data:
                            total_tokens = data["usage"].get("total_tokens", 0)
                        if "model" in data:
                            model_name = data["model"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass

        return {"content": accumulated, "tokens": total_tokens, "model": model_name}


# ─── 核心类 ───────────────────────────────────────────────────
class ClaudeCodeAgent:
    """
    真元集群的独立分析Agent。

    行为流：
      execute(task) → 直接调用 OpenAI 兼容 API（原三级回退保留接口兼容）
      每次调用结果自动写入 neural_working_memory.json 和报告文件。
    """

    def __init__(self, agent_id: str = "claude-code-agent"):
        self.agent_id = agent_id
        self.total_tasks = 0
        self.success_count = 0
        self.fail_count = 0
        self.history: list[dict] = []
        self.last_mode: str = ""
        # 可用性标志（为兼容保留三个字段，实际都指向同一个探测结果）
        self._cli_available: Optional[bool] = None
        self._proxy_available: Optional[bool] = None
        self._direct_available: Optional[bool] = None
        self._probe()

    # ── 可用性探测 ────────────────────────────────────────────
    def _probe(self):
        """启动时快速探测 API 连通性"""
        try:
            req = urllib.request.Request(
                f"{API_BASE}/models",
                headers={"Authorization": f"Bearer {API_KEY}"},
            )
            resp = urllib.request.urlopen(req, timeout=5)
            ok = resp.status == 200
            self._cli_available = ok
            self._proxy_available = ok
            self._direct_available = ok
        except Exception:
            self._cli_available = False
            self._proxy_available = False
            self._direct_available = False

        print(
            f"[ClaudeCodeAgent] API 连通性: "
            f"{'✅' if self._direct_available else '❌'} "
            f"({API_BASE})"
        )

    # ── 主入口 ────────────────────────────────────────────────
    def execute(self, prompt: str, task_id: str = "", timeout: int = API_TIMEOUT) -> AgentResult:
        """
        执行分析任务（直接 HTTP 调用，原三级回退逻辑保留签名兼容）。

        返回 AgentResult，无论成功失败。
        """
        if not task_id:
            task_id = f"task-{int(time.time())}-{self.total_tasks}"
        self.total_tasks += 1
        t0 = time.time()

        # 直接调用 API（替换了原来的 claude CLI + 代理 + 直连三级回退）
        result = self._try_direct_api(prompt, task_id, t0)
        self._record(result)
        return result

    # ── API 调用（替换原 _try_claude_cli 和 _try_api） ──────
    def _try_direct_api(self, prompt: str, task_id: str, t0: float) -> AgentResult:
        """通过 urllib 直接调用 OpenAI 兼容 API"""
        try:
            resp_data = _http_chat_completion(
                prompt=prompt,
                stream=False,        # 非流式，直接返回完整结果
                timeout=API_TIMEOUT,
            )
            latency = (time.time() - t0) * 1000
            return AgentResult(
                task_id=task_id,
                success=True,
                content=resp_data["content"],
                mode_used="direct_api",
                tokens_used=resp_data["tokens"],
                latency_ms=round(latency, 2),
                model=resp_data["model"],
            )
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")[:300]
            except Exception:
                pass
            return AgentResult(
                task_id=task_id,
                success=False,
                content="",
                mode_used="direct_api",
                latency_ms=round((time.time() - t0) * 1000, 2),
                error=f"HTTP {e.code}: {err_body}",
            )
        except urllib.error.URLError as e:
            return AgentResult(
                task_id=task_id,
                success=False,
                content="",
                mode_used="direct_api",
                latency_ms=round((time.time() - t0) * 1000, 2),
                error=f"URL错误: {str(e.reason)[:200]}",
            )
        except Exception as e:
            return AgentResult(
                task_id=task_id,
                success=False,
                content="",
                mode_used="direct_api",
                latency_ms=round((time.time() - t0) * 1000, 2),
                error=str(e)[:300],
            )

    # ── 保留原方法签名（内部重定向） ─────────────────────────
    def _try_claude_cli(self, prompt: str, timeout: int) -> AgentResult:
        """
        [兼容存根] 原 claude CLI 调用已改为 HTTP 调用。
        保留此方法签名以供外部兼容调用。
        """
        t0 = time.time()
        task_id = f"cli-{int(t0)}"
        return self._try_direct_api(prompt, task_id, t0)

    def _try_api(self, prompt: str, task_id: str, base_url: str, t0: float, mode: str) -> AgentResult:
        """
        [兼容存根] 原本地代理/直连API调用，已统一为直接 HTTP 调用。
        base_url 参数被忽略（统一使用 api_config.API_BASE）。
        """
        # 忽略 base_url，统一使用 api_config.API_BASE
        result = self._try_direct_api(prompt, task_id, t0)
        # 覆盖 mode_used 以匹配调用者期望
        result.mode_used = mode
        return result

    # ── 流式调用接口（新增） ─────────────────────────────────
    def execute_stream(self, prompt: str, task_id: str = "", timeout: int = API_TIMEOUT):
        """
        流式执行分析任务，逐块产出文本（生成器）。

        Yields:
            str: 每次产出一个文本块
        """
        if not task_id:
            task_id = f"task-{int(time.time())}-{self.total_tasks}"
        self.total_tasks += 1
        t0 = time.time()

        try:
            resp_data = _http_chat_completion(
                prompt=prompt,
                stream=True,
                timeout=timeout,
            )
            # 流式模式下 _http_chat_completion 内部已累积完毕，直接返回完整内容
            # 实际流式场景应改造为逐块 yield，此处简化：先完整获取再逐字符模拟
            full_content = resp_data["content"]
            # 模拟流式输出，按行 yield
            for line in full_content.splitlines(keepends=True):
                yield line
                time.sleep(0.01)  # 微小延迟以模拟流式效果

            latency = (time.time() - t0) * 1000
            result = AgentResult(
                task_id=task_id,
                success=True,
                content=full_content,
                mode_used="direct_api_stream",
                tokens_used=resp_data["tokens"],
                latency_ms=round(latency, 2),
                model=resp_data["model"],
            )
            self._record(result)
        except Exception as e:
            yield f"[错误] {str(e)[:200]}"
            result = AgentResult(
                task_id=task_id,
                success=False,
                content="",
                mode_used="direct_api_stream",
                latency_ms=round((time.time() - t0) * 1000, 2),
                error=str(e)[:300],
            )
            self._record(result)

    # ── 结果记录 ──────────────────────────────────────────────
    def _record(self, result: AgentResult):
        """记录结果到历史 + working memory + 报告文件"""
        if result.success:
            self.success_count += 1
        else:
            self.fail_count += 1

        self.last_mode = result.mode_used
        self.history.append({
            "task_id": result.task_id,
            "mode": result.mode_used,
            "success": result.success,
            "tokens": result.tokens_used,
            "latency_ms": result.latency_ms,
            "timestamp": result.timestamp,
            "error": result.error[:100] if result.error else "",
        })
        # 保持最近20条
        if len(self.history) > 20:
            self.history = self.history[-20:]

        # 更新 working memory
        self._update_working_memory()

        # 保存最新报告
        if result.success:
            self._save_report(result)

    def _update_working_memory(self):
        """将Agent状态写入 neural_working_memory.json"""
        try:
            wm = {}
            if os.path.exists(WORKING_MEMORY):
                with open(WORKING_MEMORY, "r", encoding="utf-8") as f:
                    wm = json.load(f)

            wm.setdefault("modules", {})
            wm["modules"]["claude_code_agent"] = {
                "status": "active",
                "agent_id": self.agent_id,
                "total_tasks": self.total_tasks,
                "success_count": self.success_count,
                "fail_count": self.fail_count,
                "success_rate": round(
                    self.success_count / max(1, self.total_tasks), 4
                ),
                "last_mode": self.last_mode,
                "last_update": datetime.now().isoformat(),
                "probe": {
                    "api": self._direct_available,
                },
            }
            wm["last_update"] = time.time()

            # 添加信号
            wm.setdefault("signals", [])
            wm["signals"].append({
                "time": datetime.now().isoformat(),
                "module": "claude_code_agent",
                "key": "heartbeat",
                "value": {
                    "total_tasks": self.total_tasks,
                    "success_rate": round(
                        self.success_count / max(1, self.total_tasks), 4
                    ),
                    "last_mode": self.last_mode,
                },
            })
            # 保持最近50条信号
            if len(wm["signals"]) > 50:
                wm["signals"] = wm["signals"][-50:]

            with open(WORKING_MEMORY, "w", encoding="utf-8") as f:
                json.dump(wm, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  ⚠ working_memory更新失败: {e}")

    def _save_report(self, result: AgentResult):
        """保存分析报告到JSON文件"""
        try:
            report = {
                "agent": "ClaudeCodeAgent",
                "agent_id": self.agent_id,
                "task_id": result.task_id,
                "mode": result.mode_used,
                "model": result.model,
                "tokens": result.tokens_used,
                "latency_ms": result.latency_ms,
                "timestamp": result.timestamp,
                "analysis": result.content,
            }
            path = os.path.join(REPORT_DIR, "claude_code_report.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"  📄 报告已保存: {path}")
        except Exception as e:
            print(f"  ⚠ 报告保存失败: {e}")

    # ── 诊断方法 ──────────────────────────────────────────────
    def status(self) -> dict:
        """返回Agent状态摘要"""
        return {
            "agent_id": self.agent_id,
            "total_tasks": self.total_tasks,
            "success": self.success_count,
            "fail": self.fail_count,
            "success_rate": round(self.success_count / max(1, self.total_tasks), 4),
            "last_mode": self.last_mode,
            "api_available": self._direct_available,
        }

    def __repr__(self):
        return (
            f"ClaudeCodeAgent(id={self.agent_id}, "
            f"tasks={self.total_tasks}, "
            f"success_rate={self.success_count}/{self.total_tasks}, "
            f"last_mode={self.last_mode})"
        )


# ─── ClaudeAgentBridge（简化桥接类） ─────────────────────────
class ClaudeAgentBridge:
    """
    简化桥接类，提供 execute_task 直接返回字符串的接口。

    用于简化调用：result = ClaudeAgentBridge().execute_task("你的问题")
    """

    def __init__(self, agent_id: str = "claude-agent-bridge"):
        self.agent = ClaudeCodeAgent(agent_id=agent_id)

    def execute_task(self, prompt: str, timeout: int = API_TIMEOUT) -> str:
        """
        执行任务并返回文本结果（字符串）。

        参数:
            prompt: 用户提示词
            timeout: 超时秒数

        返回:
            str: 成功时返回模型回答文本；失败时返回 "错误: <详情>"
        """
        result = self.agent.execute(prompt, timeout=timeout)
        if result.success:
            return result.content
        return f"错误: {result.error}"


# ─── CLI 入口 ─────────────────────────────────────────────────
def main():
    """命令行测试入口"""
    print("=" * 60)
    print("  Claude Agent Bridge v3.0 · 真元集群集成测试（HTTP Direct）")
    print("=" * 60)

    agent = ClaudeCodeAgent()
    print(f"\n📊 Agent状态: {json.dumps(agent.status(), ensure_ascii=False, indent=2)}")

    # 测试任务
    test_prompt = (
        "请用3句话简洁回答：你是谁？当前系统有什么最重要的架构缺口？"
        "你建议的第一个改进动作是什么？"
    )
    print(f"\n🧪 执行测试任务...")
    print(f"   Prompt: {test_prompt[:60]}...")
    print(f"   超时: {API_TIMEOUT}s")

    result = agent.execute(test_prompt, task_id="test-001")

    print(f"\n{'─' * 60}")
    print(f"📋 结果:")
    print(f"   成功: {'✅' if result.success else '❌'}")
    print(f"   模式: {result.mode_used}")
    print(f"   模型: {result.model}")
    print(f"   Tokens: {result.tokens_used}")
    print(f"   延迟: {result.latency_ms:.0f}ms")
    if result.success:
        print(f"   内容: {result.content[:200]}...")
    else:
        print(f"   错误: {result.error[:200]}")

    print(f"\n📊 最终状态: {json.dumps(agent.status(), ensure_ascii=False, indent=2)}")
    print(f"\n{'=' * 60}")
    return result


if __name__ == "__main__":
    main()
