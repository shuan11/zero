#!/usr/bin/env python3
"""
技能注册表模块
==============
功能：
1. 扫描 superpowers/skills/ 下所有 SKILL.md 文件
2. 提取每个 skill 的名称、触发条件(description)、步骤
3. 构建 skill 注册表并写入 skill_registry.json
4. 支持根据任务描述匹配最佳 skill
"""

import os
import re
import json
import glob
from pathlib import Path
from difflib import SequenceMatcher

# ============================================================
# 配置
# ============================================================

# 基础路径：相对于本文件所在目录
BASE_DIR = Path(__file__).resolve().parent
SKILLS_DIR = BASE_DIR / "external_projects" / "superpowers" / "skills"
REGISTRY_PATH = BASE_DIR / "skill_registry.json"


# ============================================================
# 解析单个 SKILL.md
# ============================================================

def parse_skill_md(filepath: str) -> dict | None:
    """
    解析一个 SKILL.md 文件，提取：
    - name: 技能名称（来自 YAML frontmatter）
    - description: 触发条件/描述（来自 YAML frontmatter）
    - steps: 正文中提取的步骤列表
    - file_path: 文件路径
    - directory: 所在目录名
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # --- 提取 YAML frontmatter ---
    frontmatter_match = re.match(
        r"^---\s*\n(.*?)\n---", content, re.DOTALL
    )
    if not frontmatter_match:
        print(f"  [跳过] 无 YAML frontmatter: {filepath}")
        return None

    frontmatter_text = frontmatter_match.group(1)

    # 提取 name
    name_match = re.search(r"name:\s*(.+)", frontmatter_text)
    name = name_match.group(1).strip().strip('"').strip("'") if name_match else ""

    # 提取 description（触发条件）
    desc_match = re.search(r"description:\s*(.+)", frontmatter_text)
    description = desc_match.group(1).strip().strip('"').strip("'") if desc_match else ""

    # --- 提取正文（frontmatter 之后的内容） ---
    body = content[frontmatter_match.end():]

    # 提取步骤：多种格式
    steps = extract_steps(body)

    # 提取 "When to Use" 部分作为触发条件补充
    when_to_use = extract_when_to_use(body)

    return {
        "name": name,
        "description": description,
        "when_to_use": when_to_use,
        "steps": steps,
        "file_path": str(filepath),
        "directory": os.path.basename(os.path.dirname(filepath)),
    }


def extract_steps(body: str) -> list[str]:
    """
    从正文中提取步骤列表。
    支持多种格式：
    - Markdown 有序列表 (1. xxx  2. xxx)
    - Checklist (- [ ] xxx)
    - 带编号的标题 (### Phase 1: xxx  ### Step 1: xxx)
    - ## Checklist 下的内容
    """
    steps = []

    # 策略1：查找 "Checklist" 区块中的有序列表
    checklist_match = re.search(
        r"##?\s*Checklist.*?\n((?:.*?\n)*?)(?=\n##?\s|\Z)",
        body, re.DOTALL | re.IGNORECASE
    )
    if checklist_match:
        checklist_block = checklist_match.group(1)
        numbered = re.findall(
            r"^\d+\.\s+\*\*(.+?)\*\*", checklist_block, re.MULTILINE
        )
        if numbered:
            steps.extend(numbered)

    # 策略2：提取 "Phase" 或 "The Four Phases" 等区块的标题
    if not steps:
        phases = re.findall(
            r"###?\s+(?:Phase\s+\d+|Step\s+\d+|The\s+\w+\s+Phase)[:\s]*(.+)",
            body, re.MULTILINE | re.IGNORECASE
        )
        if phases:
            steps.extend([p.strip() for p in phases])

    # 策略3：提取有序列表项（顶层）
    if not steps:
        ordered = re.findall(
            r"^\d+\.\s+\*\*(.+?)\*\*", body, re.MULTILINE
        )
        if ordered:
            steps.extend(ordered)

    # 策略4：提取 ### 带编号的标题（如 Phase 1: Root Cause Investigation）
    if not steps:
        section_titles = re.findall(
            r"###\s+(?:Phase|Step)\s+\d+[:\s]+(.+)",
            body, re.MULTILINE
        )
        if section_titles:
            steps.extend([t.strip() for t in section_titles])

    # 策略5：提取 ### 标题列表（排除 "Overview"、"Red Flags" 等通用标题）
    if not steps:
        skip_titles = {
            "overview", "red flags", "common rationalizations",
            "quick reference", "key principles", "real-world impact",
            "when to use", "when not to use", "common mistakes",
            "verification", "when stuck", "debugging integration",
            "final rule", "iron law", "supporting techniques",
            "when process reveals \"no root cause\"",
        }
        h3_titles = re.findall(r"###\s+(.+)", body)
        for t in h3_titles:
            cleaned = t.strip().rstrip("*").strip()
            if cleaned.lower().split("—")[0].strip().rstrip(":") not in skip_titles:
                steps.append(cleaned)

    # 去重并限制数量
    seen = set()
    unique_steps = []
    for s in steps:
        s_clean = s.strip()
        if s_clean and s_clean not in seen:
            seen.add(s_clean)
            unique_steps.append(s_clean)
    return unique_steps[:20]  # 最多保留20个步骤


def extract_when_to_use(body: str) -> list[str]:
    """
    提取 "When to Use" 部分的触发场景列表。
    """
    when_match = re.search(
        r"##?\s*When to Use.*?\n((?:.*?\n)*?)(?=\n##?\s|\Z)",
        body, re.DOTALL | re.IGNORECASE
    )
    if not when_match:
        return []

    block = when_match.group(1)
    # 提取 "- xxx" 列表项
    items = re.findall(r"^[-*]\s+(.+)", block, re.MULTILINE)
    # 过滤掉纯代码块和空行
    items = [i.strip() for i in items if i.strip() and not i.strip().startswith("`") and not i.strip().startswith("//")]
    return items


# ============================================================
# 扫描并构建注册表
# ============================================================

def scan_all_skills() -> list[dict]:
    """
    扫描 skills 目录下所有 SKILL.md 文件，返回解析后的技能列表。
    """
    if not SKILLS_DIR.exists():
        print(f"[错误] skills 目录不存在: {SKILLS_DIR}")
        return []

    skill_files = sorted(SKILLS_DIR.rglob("SKILL.md"))
    print(f"[扫描] 找到 {len(skill_files)} 个 SKILL.md 文件\n")

    skills = []
    for filepath in skill_files:
        print(f"  解析: {filepath}")
        skill = parse_skill_md(str(filepath))
        if skill:
            skills.append(skill)
            print(f"    → 名称: {skill['name']}")
            print(f"    → 描述: {skill['description'][:60]}...")
            print(f"    → 步骤数: {len(skill['steps'])}")
        else:
            print(f"    → [跳过] 无法解析")

    return skills


def build_registry(skills: list[dict]) -> dict:
    """
    构建技能注册表结构。
    """
    registry = {
        "version": "1.0",
        "skill_count": len(skills),
        "skills": {},
    }
    for skill in skills:
        key = skill["name"]
        registry["skills"][key] = {
            "description": skill["description"],
            "when_to_use": skill["when_to_use"],
            "steps": skill["steps"],
            "directory": skill["directory"],
            "file_path": skill["file_path"],
        }
    return registry


def save_registry(registry: dict, path: Path = REGISTRY_PATH):
    """
    将注册表写入 JSON 文件。
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    print(f"\n[保存] 注册表已写入: {path}")


# ============================================================
# Token 提取与概念映射（支持中英文）
# ============================================================

def extract_tokens(text: str) -> set[str]:
    """
    从文本中提取 token 集合。
    支持中英文混合文本：
    - 英文：按空格/标点分词，去除停用词
    - 中文：提取单字 + 相邻双字（bigram）
    """
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall", "can",
        "need", "to", "of", "in", "for", "on", "with", "at", "by",
        "from", "as", "into", "about", "between", "through", "during",
        "before", "after", "and", "but", "or", "not", "no", "so",
        "if", "then", "than", "that", "this", "it", "its", "i", "we",
        "you", "your", "my", "me", "he", "she", "they", "them",
        "some", "any", "all", "each", "every", "just", "also", "very",
    }
    # 中文停用词（虚词）
    cn_stop = set("的了在是和与或不有这那我你他她它们个要把被从到用为做")

    text = text.lower()
    tokens = set()

    # 1. 英文分词
    for w in re.split(r"[\s,;:.!?\"'()\[\]{}\-_/\\]+", text):
        if w and w not in stop_words and len(w) > 1:
            # 判断是否含中文字符
            if not re.search(r"[\u4e00-\u9fff]", w):
                tokens.add(w)

    # 2. 中文字符提取（单字 + bigram）
    cn_chars = [ch for ch in text if "\u4e00" <= ch <= "\u9fff"]
    for i, ch in enumerate(cn_chars):
        if ch not in cn_stop:
            tokens.add(ch)
            # bigram
            if i + 1 < len(cn_chars) and cn_chars[i + 1] not in cn_stop:
                tokens.add(ch + cn_chars[i + 1])

    return tokens


# 中文概念 → 英文技能关键词的语义映射表
# 用于跨语言匹配
CONCEPT_MAP: dict[str, list[str]] = {
    # 调试相关
    "调试": ["debug", "debugging", "systematic", "bug", "fix", "root", "cause"],
    "修复": ["fix", "bug", "debug", "test"],
    "错误": ["bug", "error", "debug", "failure", "test"],
    "根本原因": ["root", "cause", "debug", "systematic"],
    "测试失败": ["test", "failure", "debug", "failing"],
    "bug": ["bug", "debug", "systematic", "fix"],
    # 功能开发相关
    "新功能": ["feature", "brainstorming", "creative", "design"],
    "功能": ["feature", "brainstorming", "implementation"],
    "开发": ["implementation", "development", "tdd", "test"],
    "实现": ["implementation", "executing", "plan", "development"],
    "创建": ["creating", "feature", "brainstorming", "creative"],
    "构建": ["building", "feature", "brainstorming"],
    # 设计相关
    "设计": ["design", "brainstorming", "spec"],
    "头脑风暴": ["brainstorming", "design", "creative"],
    "需求": ["spec", "requirements", "plan", "brainstorming"],
    # 计划相关
    "计划": ["plan", "writing-plans", "executing"],
    "方案": ["plan", "spec", "design"],
    "执行": ["executing", "plan", "implementation"],
    # 并行相关
    "并行": ["parallel", "dispatching", "agents", "independent"],
    "多个": ["parallel", "multiple", "dispatching"],
    "独立": ["independent", "parallel", "dispatching"],
    # 测试相关
    "测试": ["test", "tdd", "test-driven", "failing"],
    "单元测试": ["test", "tdd", "test-driven"],
    # 代码审查
    "审查": ["review", "code-review"],
    "代码审查": ["review", "code-review", "receiving"],
    "反馈": ["review", "feedback", "receiving"],
    # 分支管理
    "分支": ["branch", "git", "worktree", "finishing"],
    "合并": ["branch", "merge", "finishing"],
    # 验证
    "验证": ["verification", "verification-before-completion"],
    "完成": ["completion", "verification", "finishing"],
    # 子代理
    "子代理": ["subagent", "dispatching", "parallel", "agents"],
    "代理": ["agent", "subagent", "dispatching"],
    # 技能写作
    "技能": ["skill", "writing-skills", "superpowers"],
    "写作": ["writing", "writing-skills", "writing-plans"],
    # 项目
    "项目": ["project", "brainstorming", "feature"],
}


# ============================================================
# 匹配功能：根据任务描述匹配最佳 skill
# ============================================================

def match_skill(task_description: str, registry: dict | None = None, top_n: int = 3) -> list[dict]:
    """
    根据任务描述匹配最佳 skill。

    匹配策略（综合评分）：
    1. 中英文 token 匹配（含中文概念→英文关键词映射）
    2. SequenceMatcher 文本相似度
    3. when_to_use 触发条件逐项比较

    返回排序后的匹配结果列表（最多 top_n 个）。
    """
    if registry is None:
        if REGISTRY_PATH.exists():
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                registry = json.load(f)
        else:
            print("[错误] 注册表文件不存在，请先运行构建。")
            return []

    # 提取任务的原始 token
    task_tokens = extract_tokens(task_description)

    # 中文概念扩展：对每个中文 bigram/token 查映射表，注入英文关键词
    expanded_tokens = set(task_tokens)
    for token in task_tokens:
        # 精确匹配
        if token in CONCEPT_MAP:
            expanded_tokens.update(CONCEPT_MAP[token])
        # bigram 包含匹配
        for cn_key, en_values in CONCEPT_MAP.items():
            if token in cn_key or cn_key in token:
                expanded_tokens.update(en_values)

    results = []
    for skill_name, skill_info in registry.get("skills", {}).items():
        score = 0.0

        name_lower = skill_name.lower()
        desc_lower = skill_info.get("description", "").lower()
        when_items = skill_info.get("when_to_use", [])
        steps = skill_info.get("steps", [])

        # 构建技能的 token 集合
        skill_text = f"{name_lower} {desc_lower} {' '.join(when_items)} {' '.join(steps)}"
        skill_tokens = extract_tokens(skill_text)

        # --- 维度1：扩展 token 交集 ---
        common_tokens = expanded_tokens & skill_tokens
        if expanded_tokens:
            token_score = len(common_tokens) / len(expanded_tokens)
        else:
            token_score = 0
        score += token_score * 50

        # --- 维度2：name 文本相似度 ---
        name_sim = SequenceMatcher(None, task_description.lower(), name_lower).ratio()
        score += name_sim * 15

        # --- 维度3：description 文本相似度 ---
        desc_sim = SequenceMatcher(None, task_description.lower(), desc_lower).ratio()
        score += desc_sim * 15

        # --- 维度4：when_to_use 逐项匹配 ---
        when_best = 0
        for item in when_items:
            item_sim = SequenceMatcher(None, task_description.lower(), item.lower()).ratio()
            if item_sim > when_best:
                when_best = item_sim
        score += when_best * 10

        # --- 维度5：原始 token 与技能 token 的交集（不带映射扩展） ---
        raw_common = task_tokens & skill_tokens
        if task_tokens:
            raw_score = len(raw_common) / len(task_tokens)
        else:
            raw_score = 0
        score += raw_score * 10

        results.append({
            "name": skill_name,
            "description": skill_info.get("description", ""),
            "score": round(score, 2),
            "matched_keywords": sorted(common_tokens & {"debug", "bug", "fix", "test",
                "feature", "design", "brainstorming", "plan", "parallel", "review",
                "tdd", "branch", "verification", "subagent", "skill", "spec",
                "implementation", "executing", "dispatching", "completion",
                "development", "writing", "project", "error", "failure",
            }),
        })

    # 按得分降序排列
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


# ============================================================
# 主函数
# ============================================================

def main():
    """
    主函数：扫描 skills → 构建注册表 → 测试匹配功能。
    """
    print("=" * 60)
    print("  技能注册表构建器 (Skill Registry Builder)")
    print("=" * 60)
    print(f"\n[路径] skills 目录: {SKILLS_DIR}")
    print(f"[路径] 注册表输出: {REGISTRY_PATH}\n")

    # 第一步：扫描所有 SKILL.md
    print("-" * 40)
    print("第一步：扫描 SKILL.md 文件")
    print("-" * 40)
    skills = scan_all_skills()
    print(f"\n[结果] 成功解析 {len(skills)} 个技能\n")

    # 第二步：构建并保存注册表
    print("-" * 40)
    print("第二步：构建并保存注册表")
    print("-" * 40)
    registry = build_registry(skills)
    save_registry(registry)

    # 第三步：测试匹配功能
    print("\n" + "=" * 60)
    print("第三步：测试匹配功能")
    print("=" * 60)

    test_queries = [
        "我发现了一个 bug，需要调试并找到根本原因",
        "我要开始开发一个新功能",
        "我需要写一个实现计划",
        "有多个测试失败了，需要并行处理",
        "我要开始一个新项目，先做个设计",
        "I need to fix a failing test",
        "代码审查后需要处理反馈",
    ]

    for query in test_queries:
        print(f"\n{'─' * 50}")
        print(f"  任务: {query}")
        print(f"{'─' * 50}")
        matches = match_skill(query, registry, top_n=3)
        for i, m in enumerate(matches, 1):
            print(f"  #{i} [{m['score']:.1f}分] {m['name']}")
            print(f"       描述: {m['description'][:80]}")
            if m['matched_keywords']:
                print(f"       匹配关键词: {', '.join(m['matched_keywords'][:8])}")

    print(f"\n{'=' * 60}")
    print("  完成！注册表已保存到 skill_registry.json")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
