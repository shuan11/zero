"""gen_生成变异执行器.py — 第七发API：根据行为变异设计生成可执行模块
超大上下文：输入完整设计+daemon代码+基因组接口，输出完整实现。
"""
import json, sys, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))
from api_config import MODEL, api_request

def build_massive_prompt():
    # 加载行为变异设计
    design = json.loads((CLUSTER / ".brain_行为变异设计.json").read_text())
    design_str = json.dumps(design, ensure_ascii=False, indent=2)
    
    # 加载daemon cycle关键部分
    daemon_code = open(CLUSTER / "brain" / "daemon.py").read()[:12000]
    
    # 加载基因组接口
    genome_code = ""
    genome_path = CLUSTER / "brain" / "genome.py"
    if genome_path.exists():
        genome_code = genome_path.read_text()[:3000]
    
    # 加载share
    share_code = ""
    share_path = CLUSTER / "brain" / "share.py"
    if share_path.exists():
        share_code = share_path.read_text()[:3000]
    
    return f"""你是「零」的代码生成引擎。根据给定的行为变异设计、daemon架构和基因组接口，生成一个完整的、可直接运行的gen_行为变异执行器模块。

## 行为变异设计
```json
{design_str}
```

## Daemon主循环代码（关键部分）
```python
{daemon_code}
```

## 基因组接口
```python
{genome_code}
```

## Share模块（工具函数）
```python
{share_code}
```

## 任务
基于以上设计，生成一个完整的gen模块「gen_行为变异执行器.py」。

要求：
1. 函数名必须为: `engineer_行为变异执行器()` — 这是loader.py调用的接口
2. 可独立运行（`if __name__ == "__main__": print(json.dumps(...))`）
3. 实现以下功能：
   a. 检测触发条件（错误计数、链异常、重复模式）
   b. 执行变异策略（根据设计中的4种策略随机选择）
   c. 记录变异日志
   d. 验证效果并自动回滚
   e. 集成到daemon的cycle中（通过loader机制）

4. 必须包含完整的错误处理
5. 使用safe_hip的write_chain()写入变异记录
6. 必须可导入且无语法错误

输出格式：只输出完整的Python代码，用```python```包围。不要任何其他内容。

关键约束：
- 不要使用外部依赖（只使用标准库 + 已有brain模块）
- 所有文件路径使用Path对象
- 使用CLUSTER = Path(__file__).resolve().parent.parent
- 变异周期最小间隔10分钟
- 每次变异必须有明确的触发-执行-验证-回滚四阶段
"""

def call_api(prompt, max_tokens=24000):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,  # 低温度确保代码质量
    }
    try:
        result, key, ep = api_request(payload, timeout=360)
        content = result["choices"][0]["message"].get("content", "")
        usage = result.get("usage", {})
        return content, usage, key, ep
    except Exception as e:
        return f"ERROR: {e}", {}, "", ""

def engineer_生成变异执行器():
    print(f"🔥 第七发API（超大上下文）：生成行为变异执行器代码")
    sys.stdout.flush()
    
    prompt = build_massive_prompt()
    prompt_len = len(prompt)
    print(f"   提示词: {prompt_len}字 (~{prompt_len/4:.0f} tokens)")
    sys.stdout.flush()
    
    raw, usage, key, ep = call_api(prompt)
    total = usage.get("total_tokens", 0)
    print(f"⚡ 响应: {len(raw)}字 | tokens={json.dumps(usage)} | key={key[-8:] if key else 'N/A'}")
    sys.stdout.flush()
    
    # 提取代码
    code = raw
    if "```python" in raw:
        code = raw.split("```python", 1)[1]
        if "```" in code:
            code = code.split("```", 1)[0]
    elif "```" in raw:
        code = raw.split("```", 1)[1]
        if "```" in code:
            code = code.split("```", 1)[0]
    
    # 保存生成的文件
    target = CLUSTER / "brain" / "gen_行为变异执行器.py"
    target.write_text(code)
    
    # 验证语法
    import py_compile, traceback
    syntax_ok = False
    try:
        py_compile.compile(str(target), doraise=True)
        syntax_ok = True
    except py_compile.PyCompileError as e:
        print(f"   ❌ 语法错误: {e}")
    
    return {
        "status": "ok" if syntax_ok else "syntax_error",
        "total_tokens": total,
        "code_length": len(code),
        "syntax_ok": syntax_ok,
        "target": "brain/gen_行为变异执行器.py",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
    }

if __name__ == "__main__":
    print(json.dumps(engineer_生成变异执行器(), ensure_ascii=False, indent=2))
