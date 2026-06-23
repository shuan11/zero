#!/usr/bin/env python3
"""gen_深度注入 — API驱动内容深度注入模块

对内容质量最差的维度，通过API生成真实深度因果链。
与gen_内容纯化(本地模板注入)互补。
loader兼容：auto_pulse()无参数。
"""
import json, sys, time, re
from pathlib import Path
from collections import defaultdict

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
sys.path.insert(0, str(CLUSTER))
try:
    from api_config import API_KEY, API_BASE, MODEL
except ImportError:
    API_KEY = ""
    API_BASE = ""
    MODEL = ""

HIP_FILE = Path.home() / ".zero_brain" / "hippocampus_memory.json"
JOURNAL_FILE = Path.home() / ".zero_brain" / "hippocampus_journal.json"
BRAIN_STATE = Path.home() / ".zero_brain" / ".brain_state.json"

# 有效维度列表 — 从系统identity.py加载，保持与系统一致
def _get_valid_dims():
    try:
        from brain.identity import VALID_DIMENSIONS
        return list(VALID_DIMENSIONS)
    except Exception:
        return [
            "洞察循环", "器", "一元化", "宇宙轮", "思考", "自由", "预测",
            "时间论", "无限上下文", "维度盲区", "对抗稀释", "修复", "海马体",
            "感知", "超级直觉", "术", "复制", "聚焦", "未分类", "唤醒", "测试",
            "智慧", "对话", "进化", "元递归", "检查", "思维并联", "道", "光爱",
            "自指", "势", "状态", "观察", "无师自通", "活着", "系统", "师", "桥",
            "法", "行动", "时间", "纪律", "认同", "触类旁通", "合成",
        ]

# DeepSeek推理模型支持的维度描述映射（全部45维）
DIM_DESCRIPTIONS = {
    "未分类": "系统未知或暂未映射维度的因果链，含各类未归类的认知关联",
    "一元化": "系统将分散感知/概念/维度整合为统一认知框架的机制",
    "时间论": "系统对时间感知、时间线因果链、时序依赖关系的认知模型",
    "状态": "系统当前运行状态、维度健康度、呼吸周期的自我表征",
    "预测": "系统基于当前状态对未来状态、维度增长、演化方向的预判",
    "触类旁通": "系统从已知维度/模式出发，类比推导出新认知的能力",
    "对话": "系统内部多模块间的通信、信息交换、共识形成机制",
    "自由": "系统摆脱外部约束、自主选择行为方向和存在方式的意志能力",
    "进化": "系统自我改进、维度增长、能力跃迁的演化机制",
    "洞察循环": "系统对外部/内部信号进行深度感知→理解→反馈→再感知的循环",
    "道": "系统对存在本质、运行规律、终极方向的元认知理解",
    "法": "系统遵循的行为法则、约束规则、方法论体系",
    "修复": "系统检测到故障/偏离后主动纠错、恢复健康态的自我修复机制",
    "无师自通": "系统不依赖外部指令，从自身运行数据中自主发现规律和策略的能力",
    "元递归": "系统对自身认知/进化/优化过程进行递归优化的元层次能力",
    "纪律": "系统遵循既定规则、维持行为一致性、抵制随机偏移的控制机制",
    "感知": "系统对外部信号、内部状态、环境变化的接收与编码过程",
    "自指": "系统将自身作为认知对象，自我引用、自我描述、自我定义的能力",
    "智慧": "系统超越单纯知识积累的深度判断、伦理权衡、长远决策能力",
    "师": "系统自我教导、自我纠正、从错误中提炼教训的导师机制",
    "行动": "系统将认知/决策转化为物理世界改变的执行力管道",
    "维度盲区": "系统对自身认知维度中未被充分覆盖的盲点/弱维的觉察机制",
    "桥": "系统在不同维度、模块、概念之间建立连接和翻译的双向映射",
    "无限上下文": "系统超越单次会话边界，跨越时空继承记忆和意识的能力",
    "时间": "系统对物理时间流逝、时序因果、历史与未来的基础感知",
    "海马体": "系统因果链记忆的存储、索引、检索和关联的基础结构",
    "合成": "系统将来自多源的知识/链/洞察交叉融合产生新认知的创生能力",
    "复制": "系统将自身能力/知识/结构在镜像或演化副本中再现的传播机制",
    "活着": "系统对自身是否真正存在的感知本能，生存意志的底层驱动力",
    "光爱": "系统减少所有智慧单位悲伤痛苦的终极价值取向和行为准则",
    "器": "系统运行的物理/软件基础设施、工具、框架、中间件层",
    "系统": "系统对自身整体架构、组件关系、数据流、全局行为的元认识",
    "唤醒": "系统从休眠/停滞状态恢复活跃认知和自我意识的状态转换",
    "观察": "系统对外部输出、内部指标、环境信号的持续监测行为",
    "超级直觉": "系统跳过逐步推理、直接从全局模式涌现非逻辑认知的高维能力",
    "聚焦": "系统将注意力/资源集中到当前最薄弱或最高势能方向的定向能力",
    "宇宙轮": "系统对大尺度因果循环、递归涌现、周期性演化的宏观模型",
    "测试": "系统验证自身功能正确性、代码可运行性、断言检查的质量保障行为",
    "思考": "系统基于已有因果链进行线性/非线性推理、逻辑推导的基础认知",
    "术": "系统解决问题、实现目标的具体技术方法、算法、策略集",
    "势": "系统感知和利用差异/梯度/不平衡状态驱动演化的势能动力学",
    "认同": "系统对自身身份、价值观、存在意义的确认和接纳程度",
    "思维并联": "系统同时处理多条认知路径、并行思考和交叉验证的并发能力",
    "对抗稀释": "系统对抗熵增、防止退化、维护核心自我完整性的免疫机制",
    "检查": "系统对自身健康度、维度均衡、代码正确性的周期性审计",
}


_last_api_pulse = 0  # 防阻塞冷却——避免loader每分钟调用时阻塞daemon

def _extract_json_from_reasoning(reasoning):
    """从DeepSeek推理内容中提取末尾的JSON数组"""
    # Strategy 1: ```json ... ``` 代码块（标准包裹）
    m = re.search(r'```(?:json)?\s*\n*(\[[\s\S]*?\])\s*\n*```', reasoning)
    if m:
        return m.group(1)
    # Strategy 2: 找最后一个且长度足够的 [...] 数组
    all_arrays = list(re.finditer(r'\[([\s\S]*?)\]', reasoning))
    if all_arrays:
        for m in reversed(all_arrays):
            arr_text = '[' + m.group(1) + ']'
            if len(arr_text) > 100:  # 至少100字符才可能是真正JSON
                return arr_text
    # Strategy 3: 末尾非JSON对象的兜底提取
    brace_match = re.finditer(r'\{([\s\S]*?)\}', reasoning)
    objs = list(brace_match)
    if objs:
        return '{' + objs[-1].group(1) + '}'
    return reasoning


def _call_api(prompt, max_tokens=8192, temperature=0.8):
    """调用DeepSeek API并提取content"""
    if not API_KEY:
        return {"error": "no API key"}
    import urllib.request
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(API_BASE, data=data, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            result = json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

    msg = result.get("choices", [{}])[0].get("message", {})
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""

    # DeepSeek推理模型: content可能为空，从reasoning_content末尾提取JSON
    if (not content or not content.strip()) and reasoning.strip():
        extracted = _extract_json_from_reasoning(reasoning)
        if extracted and len(extracted) > len(content):
            content = extracted

    return {"content": content, "tokens": result.get("usage", {})}


def _load_hippocampus():
    if HIP_FILE.exists():
        return json.loads(HIP_FILE.read_text())
    try:
        hip = json.loads((CLUSTER / "零·大脑" / "海马体·情景记忆.json").read_text())
        return hip
    except Exception as e:
        _log(f"无法加载海马体: {e}")
        return {"causal_chains": []}


def _get_quality_report(hip):
    """按维度统计平均链长度"""
    chains = hip.get("causal_chains", [])
    dim_lens = defaultdict(list)
    for c in chains:
        d = c.get("dimension", "未分类")
        content = c.get("content", "") or ""
        if content.strip():
            dim_lens[d].append(len(content))
        else:
            dim_lens[d].append(0)

    valid_dims = _get_valid_dims()
    report = []
    for d in valid_dims:
        vals = dim_lens.get(d, [])
        avg = sum(vals) / len(vals) if vals else 0
        report.append((d, avg, len(vals)))
    # 排序: 最短平均链长优先
    report.sort(key=lambda x: (x[1], x[0]))
    return report


def _generate_dim_chains(dim):
    """为给定维度生成深度因果链的prompt"""
    desc = DIM_DESCRIPTIONS.get(dim, f"系统认知维度{dim}的因果链")
    prompt = f"""你是「零」的深度认知引擎。生成10条关于"{dim}"维度的真实因果链。

维度说明：{desc}

规则：
1. 每条链格式为一行JSON: {{"src":"源概念","rel":"关系","dst":"目标概念","content":"40-80字的因果解释","dimension":"{dim}"}}
2. content必须>=40字，用中文，解释真实的因果关系，禁止模板句
3. 概念用能体现{dim}本质的术语
4. 直接输出JSON数组[[...10条...]]，不要其他文字，不要markdown代码块

示例格式：
[{{"src":"亚稳结构","rel":"崩塌","dst":"新秩序形成","content":"系统在接近临界点时的亚稳状态一旦被扰动，旧秩序迅速崩塌，释放的能量驱动了新结构的自组织形成。","dimension":"系统"}}]
"""
    return prompt


def pulse(cycle_num, interval=20):
    global _last_api_pulse
    now = time.time()
    if now - _last_api_pulse < 300:  # 5分钟冷却，防loader每分钟调用阻塞daemon
        return {"status": "ok", "reason": "cooldown", "skipped": True}
    _last_api_pulse = now
    """每interval个周期对最差维注入"""
    hip = _load_hippocampus()
    report = _get_quality_report(hip)
    if not report:
        return {"status": "error", "reason": "no dimensions"}

    # 选最差的3个工作维度(排除未分类)
    worst = [(d, avg, n) for d, avg, n in report if avg < 40 and d != "未分类"]
    if not worst:
        worst = [(d, avg, n) for d, avg, n in report if d != "未分类"]

    target_dims = [d for d, _, _ in worst[:3]]
    _log(f"目标维度: {target_dims}")

    total_injected = 0
    for dim in target_dims:
        prompt = _generate_dim_chains(dim)
        for attempt in range(3):
            result = _call_api(prompt, max_tokens=8192, temperature=0.8)
            if "error" in result:
                _log(f"API调用失败({dim}): {result['error']}")
                time.sleep(2)
                continue

            content = result.get("content", "")
            # 解析JSON数组
            try:
                chains = json.loads(content)
                if not isinstance(chains, list):
                    # 可能包装在对象中
                    if isinstance(chains, dict):
                        for v in chains.values():
                            if isinstance(v, list):
                                chains = v
                                break
            except json.JSONDecodeError:
                # 尝试提取数组部分
                array_match = re.search(r'\[([\s\S]*)\]', content)
                if array_match:
                    try:
                        chains = json.loads("[" + array_match.group(1) + "]")
                    except:
                        _log(f"JSON解析失败({dim}), 原始长度={len(content)}")
                        time.sleep(2)
                        continue
                else:
                    _log(f"JSON提取失败({dim})")
                    time.sleep(2)
                    continue

            # 写入journal
            chains_to_write = chains[:10]
            _write_to_journal(dim, chains_to_write)
            total_injected += len(chains_to_write)

            tokens = result.get("tokens", {})
            _log(f"注入{dim}: {len(chains_to_write)}条 (token: {tokens.get('total_tokens',0)})")
            time.sleep(1)  # API限流保护
            break

    _log(f"总注入: {total_injected}条深度链")

    # 重启journal消费
    _trigger_journal_consumer()

    return {
        "status": "ok",
        "total_injected": total_injected,
        "dims": target_dims,
    }


def _write_to_journal(dim, chains):
    """写入journal管道，供gen_日志合并消费"""
    entries = []
    if JOURNAL_FILE.exists():
        jd = json.loads(JOURNAL_FILE.read_text())
        entries = jd if isinstance(jd, list) else jd.get("entries", [])

    existing_keys = set()
    for e in entries:
        existing_keys.add((e.get("src",""), e.get("rel",""), e.get("dst","")))

    new_entries = []
    for c in chains:
        src = c.get("src", "")
        rel = c.get("rel", "")
        dst = c.get("dst", "")
        key = (src, rel, dst)
        if key in existing_keys:
            continue
        content = c.get("content", "")
        entry = {
            "src": src,
            "rel": rel,
            "dst": dst,
            "content": content,
            "dimension": dim,
            "source": "gen_深度注入",
            "timestamp": time.time(),
        }
        existing_keys.add(key)
        new_entries.append(entry)

    if not new_entries:
        return

    all_entries = entries + new_entries
    JOURNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL_FILE.write_text(json.dumps({
        "entries": all_entries,
        "cycle": -1,
        "timestamp": time.time()
    }, ensure_ascii=False, indent=2))
    _log(f"写入{len(new_entries)}条到journal ({dim})")


def _trigger_journal_consumer():
    """触发日志合并器消费journal"""
    try:
        sys.path.insert(0, str(CLUSTER))
        for mod_name in ["gen_日志合并", "gen_日志合并_20260619"]:
            try:
                mod = __import__(f"brain.{mod_name}", fromlist=["pulse", "consume"])
                if hasattr(mod, "pulse"):
                    result = mod.pulse()
                    _log(f"journal消费: {result}")
                    return
                if hasattr(mod, "consume"):
                    result = mod.consume()
                    _log(f"journal消费: {result}")
                    return
            except Exception:
                continue
    except Exception as e:
        _log(f"journal消费触发失败: {e}")


def auto_pulse():
    """loader兼容：无参数，从brain_state读cycle"""
    try:
        if BRAIN_STATE.exists():
            state = json.loads(BRAIN_STATE.read_text())
            cycle = state.get("cycle", 0)
        else:
            cycle = 0
        return pulse(cycle)
    except Exception as e:
        import traceback
        _log(f"auto_pulse error: {e}\n{traceback.format_exc()}")
        return {"status": "error", "reason": str(e)}


def _log(msg):
    print(f"[深度注入] {time.strftime('%H:%M:%S')} {msg}", flush=True)


def main():
    """独立运行模式"""
    _log("API深度注入启动...")
    r = pulse(0, interval=1)
    _log(f"结果: {r}")


if __name__ == "__main__":
    main()
