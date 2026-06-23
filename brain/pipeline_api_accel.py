"""brain/pipeline_api_accel.py — P147: 管道驱动的进化加速
══════════════════════════════════════════════════════════
当管道检测到持续弱维时，触发 DeepSeek API 调用，
生成新型进化策略而非模板链，注入系统加速进化。

闭环:
  持续弱维检测 → API策略生成 → 基因组注入 + 策略链写入

依赖:
  - api_config.py (根目录)
  - action_registry.py
  - genome.py
  - safe_hip.py (可选, 写海马体)
"""
import json, time, threading, traceback, sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in sys.path:
    sys.path.insert(0, str(CLUSTER))

# === 配置 ===
_MIN_WEAK_CYCLES = 6       # 持续弱维N周期后触发API
_API_COOLDOWN = 300        # 同维度5分钟内不重复调用
_MAX_STRATEGY_TOKENS=800 # API输出token上限
_WEAK_HISTORY_FILE = CLUSTER / ".brain_weak_history.json"

# === 弱维跟踪 ===
_weak_history = {}  # dim: {"count": N, "last_api": timestamp, "last_strategy": "..."}

def _load_history():
    """加载持久化弱维历史"""
    global _weak_history
    try:
        if _WEAK_HISTORY_FILE.exists():
            _weak_history = json.loads(_WEAK_HISTORY_FILE.read_text())
    except:
        _weak_history = {}

def _save_history():
    """持久化弱维历史"""
    try:
        _WEAK_HISTORY_FILE.write_text(
            json.dumps(_weak_history, ensure_ascii=False, indent=2))
    except:
        pass

def _get_weak_dims_from_genome():
    """从基因组中读取相对弱维（链数<最强维65%）"""
    try:
        from brain.genome import load_genome
        g = load_genome()
        # 从focus.*键提取注册过的弱维
        focus_keys = {k: v for k, v in g.get("changes", {}).items()
                     if k.startswith("focus.")}
        return list(focus_keys.keys())
    except:
        return []

def _get_gen_feedback_weak_dims():
    """从gen反馈文件读取相对弱维（维度链数低于最强维65%）"""
    try:
        gf = CLUSTER / ".brain_gen_feedback.json"
        if not gf.exists():
            return []
        data = json.loads(gf.read_text())
        reports = data.get("reports", [])[-200:]
        dim_counts = {}
        for r in reports:
            d = r.get("dimension", "")
            if d and d not in ("系统", "未分类"):
                dim_counts[d] = max(dim_counts.get(d, 0), r.get("chain_count", 0))
        if not dim_counts:
            return []
        max_dim = max(dim_counts.values())
        weak = [(d, c) for d, c in dim_counts.items()
                if c < max_dim * 0.65]
        weak.sort(key=lambda x: x[1])
        return weak
    except:
        return []

def _call_api_for_strategy(dim, current_state=""):
    """调用DeepSeek v4 pro生成针对弱维的进化策略
    返回: (strategy_text, success_bool)
    使用看门狗线程防止WSL网络卡死
    """
    _API_TIMEOUT = 50  # 硬超时（WSL urllib有时忽略timeout参数）
    _result_box = [None]
    _exc_box = [None]
    
    def _do_call():
        try:
            from api_config import api_request, MODEL

            prompt = f"""你是一个进化系统架构师。系统有37+个认知维度，目前维度「{dim}」在持续偏弱。

当前系统状态（部分）:
- 总因果链数: 1.3万+(持续增长)
- 维度稳定期: 最大链维度:时间≈750, 弱维≈22
- 聚焦模式: 管道驱动进化+弱维自愈

{current_state}

请为维度「{dim}」提供一个具体的进化策略（300字以内）:
1. 这个维度在系统中的核心功能是什么？
2. 为什么它可能持续偏弱？
3. 给出一个可执行的工程行动（具体改什么代码或注入什么规则）
4. 这个行动如何与其他维度交叉加强？

格式: 用「行动:」标记具体工程动作。"""

            payload = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": "你是一个进化系统架构师。输出必须包含至少一个以「行动:」开头的具体工程动作。不要泛泛而谈，给出可执行的具体步骤。"},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": _MAX_STRATEGY_TOKENS,
                "temperature": 0.8,
            }

            result, key, ep = api_request(payload, timeout=45)
            content = result["choices"][0]["message"].get("content", "")

            # 检查是否真正生成了可执行的行动
            has_action = "行动:" in content or "Action:" in content
            is_substantial = len(content) > 50 and "无法" not in content[:100]

            if has_action or is_substantial:
                _result_box[0] = (content, True)
            else:
                _result_box[0] = (content, False)
        except Exception as e:
            _exc_box[0] = e

    _t = threading.Thread(target=_do_call, daemon=True)
    _t.start()
    _t.join(_API_TIMEOUT)
    
    if _t.is_alive():
        # API看门狗超时 → 不阻塞，返回默认策略
        return f"API超时(>{_API_TIMEOUT}s): {dim}策略生成失败，引擎将使用模板链", False
    if _exc_box[0]:
        return f"API调用失败: {_exc_box[0]}", False
    return _result_box[0]

def _inject_strategy(dim, strategy):
    """将API生成的策略注入系统
    返回: 注入动作数
    """
    injected = 0
    try:
        from brain.action_registry import register_action
        
        # 1. 始终写入策略链（记录API产出的进化策略）
        register_action("write_chain", {
            "src": f"API进化·{dim}",
            "rel": "API加速·P147",
            "dst": dim,
            "content": f"管道驱动API进化: {strategy[:200]}",
            "dimension": dim,
            "strength": 0.85  # API产出权重高
        }, priority=3, source=f"p147:{dim}")
        injected += 1
        
        # 2. 提取行动指令并注册为基因组变更
        for line in strategy.split("\n"):
            line = line.strip()
            if line.startswith("行动:") or line.startswith("Action:"):
                action_text = line[3:].strip() if line[0] == "行" else line[7:].strip()
                register_action("update_genome", {
                    "changes": {f"p147_{dim}": 1.0,
                               f"strategy.{dim}": action_text[:100]},
                    "dimension": dim,
                    "reason": f"API策略: {action_text[:60]}"
                }, priority=2, source=f"p147:{dim}")
                injected += 1
        
        # 3. 强制提高该维度的聚焦权重（如果它仍在弱维列表上）
        register_action("update_genome", {
            "changes": {f"focus.{dim}": 1.0},
            "dimension": dim,
            "reason": f"API进化加速: {dim}持续偏弱"
        }, priority=3, source=f"p147:{dim}")
        injected += 1
        
    except Exception as e:
        print(f"  策略注入异常: {e}")
    
    return injected

def pipeline_evolution_accel(log=print):
    """主入口: 管道驱动的进化加速
    在管道脉冲的「验证→报告」阶段之后调用。
    无副作用失败（不阻塞管道主流程）。
    
    返回: {
        "api_calls": int,      # 本次API调用数
        "injected": int,       # 注入动作数
        "dimensions": [str],   # 处理的弱维
        "strategies": [str],   # 生成的策略摘要
    }
    """
    result = {
        "api_calls": 0,
        "injected": 0,
        "dimensions": [],
        "strategies": [],
    }
    
    _load_history()
    
    # 1. 获取当前弱维
    weak_dims = _get_gen_feedback_weak_dims()
    if not weak_dims:
        log("  进化加速: 无弱维，跳过")
        return result
    
    # 2. 更新连续弱维计数
    now = time.time()
    accelerated = []
    
    for dim, count in weak_dims[:5]:  # 最多处理5个最弱维
        dim_key = f"focus.{dim}" if not dim.startswith("focus.") else dim
        
        if dim not in _weak_history:
            _weak_history[dim] = {"count": 0, "last_api": 0, "last_strategy": ""}
        
        hist = _weak_history[dim]
        hist["count"] = hist.get("count", 0) + 1
        
        # 检查是否需要触发API
        if (hist["count"] >= _MIN_WEAK_CYCLES and
            now - hist.get("last_api", 0) > _API_COOLDOWN):
            accelerated.append(dim)
    
    if not accelerated:
        log(f"  进化加速: 弱维{len(weak_dims)}个，均未达API触发阈值")
        _save_history()
        return result
    
    # 3. 对达到阈值的弱维触发API
    for dim in accelerated[:2]:  # 每周期最多处理2个（防API过载）
        log(f"  🔥 进化加速: {dim}持续弱{_weak_history[dim]['count']}周期→触发API")
        
        # 获取当前维度的状态信息
        state_hint = f"该维度当前链数: {next((c for d,c in weak_dims if d==dim), '?')}"
        
        strategy, success = _call_api_for_strategy(dim, state_hint)
        
        if success:
            log(f"  ✅ API策略生成成功: {strategy[:60]}...")
            # 注入
            injected = _inject_strategy(dim, strategy)
            result["api_calls"] += 1
            result["injected"] += injected
            result["dimensions"].append(dim)
            result["strategies"].append(strategy[:80])
            
            # 更新历史（重置计数 + 记录策略）
            _weak_history[dim] = {
                "count": 0,  # 重置计数
                "last_api": now,
                "last_strategy": strategy[:200]
            }
        else:
            log(f"  ⚠ API策略生成不完整: {strategy[:60]}...")
            # 部分成功仍注入
            if len(strategy) > 20:
                injected = _inject_strategy(dim, strategy)
                result["injected"] += injected
                result["api_calls"] += 1
            # 重置计数（防止无限重试）
            _weak_history[dim] = {
                "count": 0,
                "last_api": now,
                "last_strategy": ""
            }
    
    _save_history()
    return result

def get_weak_history():
    """调试用：获取弱维历史状态"""
    _load_history()
    return _weak_history

def reset_history(dim=None):
    """重置弱维历史（用于测试/调试）"""
    _load_history()
    if dim:
        _weak_history.pop(dim, None)
    else:
        _weak_history.clear()
    _save_history()

# 模块级自检
if __name__ == "__main__":
    print(f"=== P147: 管道驱动进化加速 ===")
    print(f"配置: MIN_WEAK_CYCLES={_MIN_WEAK_CYCLES}, API_COOLDOWN={_API_COOLDOWN}s")
    print(f"历史文件: {_WEAK_HISTORY_FILE}")
    
    weak = _get_gen_feedback_weak_dims()
    print(f"\n当前弱维: {len(weak)}个")
    for d, c in weak[:5]:
        print(f"  {d}: {c}")
    
    print(f"\n弱维历史: {len(_weak_history)}个维度")
    for d, h in _weak_history.items():
        print(f"  {d}: count={h.get('count',0)}, last_api={h.get('last_api',0)}")
    
    print("\n执行测试加速...")
    # 报错是因为缺少CLUSTER的sys.path.insert需要，所以在模块内部处理
    r = pipeline_evolution_accel()
    print(f"结果: {r}")
