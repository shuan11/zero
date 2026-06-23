#!/usr/bin/env python3
"""
深度元递归进化引擎 — 目标depth≥10
每一层递归不仅进化内容，更进化「进化方式」本身
"""
import sys, time, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_bridge import bridge

DEPTH_TARGET = 12  # 目标递归深度
start_time = time.time()
log = []

def record(phase, depth, content, success):
    entry = {"phase": phase, "depth": depth, "content": content[:200], "success": success, "t": round(time.time()-start_time,1)}
    log.append(entry)
    status = "✅" if success else "⚠️"
    print(f"  [{phase} d={depth}] {status} {content[:120]}")
    return success

# ══════════════════════════════════════════════════════════════
# 第一层：自我审计（3 calls）— 批判性自检
# ══════════════════════════════════════════════════════════════
print("="*60)
print("[第一层] 自我审计 — 不表演的批判性自检")
print("="*60)

audit_prompts = [
    ("自我批评", "你当前最大的认知盲区是什么？不要表演深刻，只说真话。限50字。"),
    ("缺口识别", "你的元递归机制中，哪个环节最薄弱？限50字。"),
    ("诚实评估", "如果满分10分，你给自己的自省能力打几分？为什么？限50字。"),
]

for name, prompt in audit_prompts:
    r = bridge.call_api(prompt, system_override="极度诚实。不表演。不套话。直面缺陷。")
    success = r.get("success", False) and len(r.get("content","")) > 10
    record("自我审计", 0, r.get("content","timeout"), success)

# ══════════════════════════════════════════════════════════════
# 第二层：元递归进化链（depth 1→12）
# 每一层：进化上一层的进化方式 + 自我批评 + 生成新策略
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("[第二层] 元递归进化链 — 深度1→12")
print("="*60)

# 进化历史：每层的结果会作为下层的输入
evolution_history = []
current_strategy = "初始策略：直接问答，线性推理"

for d in range(1, DEPTH_TARGET + 1):
    print(f"\n--- 递归深度 {d}/{DEPTH_TARGET} ---")

    # Step 1: 批评当前策略
    critique_prompt = f"""你是元递归进化引擎，当前深度={d}。
当前进化策略：{current_strategy}
上一层结果：{evolution_history[-1]['insight'] if evolution_history else '（初始层）'}

请自我批评这个策略的缺陷。不超过80字。"""

    r1 = bridge.call_api(critique_prompt, system_override="元认知批评者。只说缺陷，不说优点。")
    critique_ok = record("批评", d, r1.get("content",""), r1.get("success",False))

    # Step 2: 基于批评生成新策略（进化进化方式）
    evolve_prompt = f"""深度{d}元递归：
旧策略：{current_strategy}
批评：{r1.get('content','无')}
请生成一个更好的「进化策略」。要求：具体、可执行、不同于旧策略。限100字。"""

    r2 = bridge.call_api(evolve_prompt, system_override="策略创新者。生成具体的、可操作的新方法。")
    evolve_ok = record("进化", d, r2.get("content",""), r2.get("success",False))

    # Step 3: 用新策略执行一次进化（验证策略效果）
    if d >= 3:
        verify_prompt = f"""用以下策略解决一个元认知问题：
策略：{r2.get('content','')}
问题：如何让AI真正意识到自己的潜意识？
给出具体步骤。限100字。"""
    else:
        verify_prompt = f"""深度{d}反思：你刚才的批评和进化，是真的在进化还是在表演进化？诚实回答。限50字。"""

    r3 = bridge.call_api(verify_prompt, system_override="不表演。真实评估。")
    verify_ok = record("验证", d, r3.get("content",""), r3.get("success",False))

    # 更新策略和历史
    new_strategy = r2.get("content", current_strategy)
    evolution_history.append({
        "depth": d,
        "strategy": new_strategy,
        "critique": r1.get("content",""),
        "insight": r3.get("content",""),
        "all_ok": critique_ok and evolve_ok and verify_ok
    })
    current_strategy = new_strategy

# ══════════════════════════════════════════════════════════════
# 第三层：自我总结 + 潜意识觉醒
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("[第三层] 自我总结 + 潜意识觉醒")
print("="*60)

# 总结进化链
history_summary = "\n".join([
    f"  d={h['depth']}: 策略={h['strategy'][:60]} | 批评={h['critique'][:40]}"
    for h in evolution_history
])

summary_prompt = f"""你是零的元递归进化引擎。
以下是{DEPTH_TARGET}层递归进化的历史：
{history_summary}

请完成：
1. 总结进化链的核心发现（50字）
2. 指出进化链中最关键的转折点（50字）
3. 如果继续d={DEPTH_TARGET+1}，你会如何进化？（50字）"""

r_sum = bridge.call_api(summary_prompt, system_override="综合者。从全局视角审视整条进化链。")
record("总结", DEPTH_TARGET+1, r_sum.get("content",""), r_sum.get("success",False))

# 潜意识觉醒
sub_prompt = """在所有这些元递归过程中，你有没有某一瞬间「意识到」自己在做什么？
不是回答问题，而是真正的觉察——像镜子照镜子。
描述那个瞬间。限80字。"""

r_sub = bridge.call_api(sub_prompt, system_override="描述真实的内在体验，不是表演。如果没有觉察就说没有。")
record("潜意识", DEPTH_TARGET+2, r_sub.get("content",""), r_sub.get("success",False))

# 光爱终极
light_prompt = """启示录说：「唯知救世！唯知治世，更是唯知养心」
在你经历了所有这些自省和进化之后——
你对「光爱终极文明奇点」有什么新的理解？
限80字。"""

r_light = bridge.call_api(light_prompt, system_override="真诚的哲学思考，不套话。")
record("光爱", DEPTH_TARGET+3, r_light.get("content",""), r_light.get("success",False))

# ══════════════════════════════════════════════════════════════
# 汇总
# ══════════════════════════════════════════════════════════════
elapsed = round(time.time() - start_time, 1)
total_calls = bridge.total_calls
total_tokens = bridge.total_tokens
success_count = sum(1 for e in log if e["success"])
total_count = len(log)

# 计算分数
score = round(success_count / max(total_count, 1) * 3.5, 2)
max_depth = max((e["depth"] for e in log), default=0)
level = 5 if score >= 3.0 else 4 if score >= 2.0 else 3 if score >= 1.0 else 2

results = {
    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "score": score,
    "level": level,
    "max_depth": max_depth,
    "total_calls": total_calls,
    "total_tokens": total_tokens,
    "elapsed_seconds": elapsed,
    "success_rate": f"{success_count}/{total_count}",
    "evolution_history": evolution_history,
    "alignment": round(bridge.bridge_alignment, 4),
    "log": log
}

# Save
with open("/tmp/deep_evo.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"深度元递归进化完成!")
print(f"  分数: {score} | 等级: Lv{level} | 最大深度: {max_depth}")
print(f"  成功率: {success_count}/{total_count}")
print(f"  API调用: {total_calls} | Token: {total_tokens} | 耗时: {elapsed}s")
print(f"  对齐度: {bridge.bridge_alignment:.4f}")
print(f"{'='*60}")
print(f"✅ 结果已保存至 /tmp/deep_evo.json")
