#!/usr/bin/env python3
"""
superpowers_bridge.py — 真元集群 × Superpowers 编码工作流桥接
================================================================
管道: 接收任务 → brainstorming → TDD计划 → 实现 → 代码审查
读取 superpowers skill 文件作提示词模板，通过 deepseek-v4-pro API 执行。
用法: python3 superpowers_bridge.py "实现一个TODO CLI工具"
"""
import os, sys, json, time, argparse, urllib.request
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
SKILLS = CLUSTER / "external_projects" / "superpowers" / "skills"
sys.path.insert(0, str(CLUSTER))
try:
    from api_config import API_KEY, API_BASE, MODEL
except Exception:
    API_KEY = os.environ.get("OPENAI_API_KEY", "")
    API_BASE = "https://inferaichat.com/v1"
    MODEL = "deepseek-v4-pro"

# ── 四个阶段的 system prompt（精简版 superpowers 方法论）──────

STAGES = {
    "brainstorm": {
        "title": "🧠 头脑风暴",
        "skill": "brainstorming",
        "system": (
            "你是资深产品架构师。严格遵循 brainstorming 方法论：\n"
            "1) 分析上下文 2) 提出2-3方案(含利弊) 3) 输出设计spec 4) 自审\n"
            "核心: YAGNI、每次只问一个问题、先设计后编码。直接输出，不需要交互。"
        ),
        "max_tokens": 4000,
    },
    "plan": {
        "title": "📋 实现计划",
        "skill": "writing-plans",
        "system": (
            "你是顶级计划编写者。遵循 writing-plans 方法论：\n"
            "- 假设工程师零背景知识 - 每步骤2-5分钟原子操作\n"
            "- 必须TDD: 写失败测试→验证失败→最小实现→验证→重构→提交\n"
            "- checkbox格式 - 每Task明确文件路径"
        ),
        "max_tokens": 5000,
    },
    "implementation": {
        "title": "⚡ TDD实现",
        "skill": "test-driven-development",
        "system": (
            "你是严格TDD实践者。铁律：没有失败测试就不写生产代码。\n"
            "Red-Green-Refactor: 写测试→验证失败→最小实现→验证通过→重构→提交。\n"
            "不过度设计，只写让测试通过的最少代码。输出完整可用代码。"
        ),
        "max_tokens": 6000,
    },
    "review": {
        "title": "🔍 代码审查",
        "skill": "requesting-code-review",
        "system": (
            "你是资深代码审查专家。审查维度：\n"
            "- 计划一致性 - 代码质量(职责分离/错误处理/DRY/边界)\n"
            "- 架构合理性 - 测试质量(真实行为/边界覆盖)\n"
            "按Critical/Important/Minor分类，给出明确结论。"
        ),
        "max_tokens": 4000,
    },
}

# 阶段间管道提示词模板
STAGE_PROMPTS = {
    "brainstorm": "## 任务\n{task}\n\n## 参考方法论\n```\n{ref}```\n\n请: 1)分析需求 2)2-3方案对比 3)完整设计spec 4)自审",
    "plan": "## 设计spec\n{prev}\n\n## 原始任务\n{task}\n\n## 参考方法论\n```\n{ref}```\n\n编写TDD实现计划，checkbox格式，每Task含文件路径",
    "implementation": "## 实现计划\n{prev}\n\n## 设计\n{first}\n\n## 参考方法论\n```\n{ref}```\n\n逐Task实现TDD，输出完整代码(测试+实现)",
    "review": "## 实现代码\n{prev}\n\n## 需求/设计\n{first}\n\n## 计划\n{plan}\n\n## 参考方法论\n```\n{ref}```\n\n全面审查: 一致性/质量/架构/测试，分类问题",
}


def load_skill_ref(skill_name: str, max_len: int = 2500) -> str:
    """加载 superpowers SKILL.md 作为参考上下文"""
    f = SKILLS / skill_name / "SKILL.md"
    if f.exists():
        t = f.read_text(encoding="utf-8")
        if t.startswith("---"):
            parts = t.split("---", 2)
            t = parts[2].strip() if len(parts) > 2 else t
        return t[:max_len]
    return ""


def api_call(prompt: str, system: str, max_tokens: int = 4000) -> dict:
    """通过 DeepSeek V4 Pro API 执行推理"""
    data = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        f"{API_BASE}/chat/completions", data=data,
        headers={"Authorization": f"Bearer {API_KEY}",
                 "Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())
            msg = resp["choices"][0]["message"]
            content = msg.get("content", "") or msg.get("reasoning_content", "")
            u = resp.get("usage", {})
            print(f"  [{time.time()-t0:.1f}s | {u.get('total_tokens','?')} tokens]")
            return {"content": content, "usage": u}
    except Exception as e:
        print(f"  [API错误 {time.time()-t0:.1f}s]: {e}")
        return {"content": f"[失败: {e}]", "usage": {}}


def build_prompt(stage_key: str, task: str, prev: str, first: str, plan: str) -> str:
    """构建阶段提示词，填充上下文"""
    tpl = STAGE_PROMPTS[stage_key]
    ref = load_skill_ref(STAGES[stage_key]["skill"])
    return tpl.format(task=task, prev=prev, first=first, plan=plan, ref=ref)


def run_pipeline(task: str, output_dir: Path = None) -> dict:
    """执行完整 superpowers 工作流管道"""
    out = output_dir or (CLUSTER / "superpowers_output")
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {}
    prev = ""       # 上一阶段输出
    first = ""      # brainstorm 输出(供后续阶段引用)
    plan_out = ""   # plan 输出(供 review 引用)

    order = ["brainstorm", "plan", "implementation", "review"]
    for key in order:
        cfg = STAGES[key]
        print(f"\n{'='*50} {cfg['title']} {'='*50}")
        prompt = build_prompt(key, task, prev, first, plan_out)
        result = api_call(prompt, cfg["system"], cfg["max_tokens"])
        content = result["content"]
        results[key] = content
        # 保存阶段输出
        (out / f"{ts}_{key}.md").write_text(content, encoding="utf-8")
        # 更新管道上下文
        if key == "brainstorm":
            first = content
        elif key == "plan":
            plan_out = content
        prev = content

    # 保存汇总
    summary = out / f"{ts}_summary.md"
    lines = [f"# Superpowers 工作流汇总", f"**任务:** {task}", f"**时间:** {datetime.now().isoformat()}", ""]
    for key in order:
        lines.extend([f"## {STAGES[key]['title']}", "", results[key], "", "---"])
    summary.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✅ 完成! 汇总: {summary}")
    return results


def main(task=None):
    if task:
        run_pipeline(task)
        return
    p = argparse.ArgumentParser(description="Superpowers 编码工作流桥接")
    p.add_argument("task", nargs="?", help="编码任务描述")
    p.add_argument("--task", "-t", dest="alt_task", help="编码任务描述")
    p.add_argument("--output", "-o", help="输出目录")
    args = p.parse_args()
    task = args.alt_task or args.task
    if not task:
        p.print_help()
        sys.exit(1)
    run_pipeline(task, Path(args.output) if args.output else None)


if __name__ == "__main__":
    import sys as _sys
    task = " ".join(_sys.argv[1:]) if len(_sys.argv) > 1 else None
    main(task)
