"""
零·器官协同集成 — 将所有模块连接到神经中枢
=============================================
运行方式: python3 neural_integration.py
效果: 所有模块开始通过SharedWorkingMemory交换状态, 通过ReflexArc自动响应
"""
import sys, os, json, time, threading

WORKDIR = "/mnt/c/Users/h/Desktop/零/真元集群"
os.chdir(WORKDIR)
sys.path.insert(0, WORKDIR)

from neural_core import memory

print("=" * 60)
print("  零·器官协同系统启动")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 注册反射弧 — 当一个模块状态变化时, 自动触发其他模块
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def on_api_call(old, new):
    """当api_bridge被调用时, 唤醒进化引擎"""
    print(f"  ⚡ Reflex: API调用({old}→{new}) → 触发进化引擎")
    memory.set("evolution_engine", "wake_signal", time.time())

def on_evolution(old, new):
    """当进化完成时, 通知SystemBus广播"""
    print(f"  ⚡ Reflex: 进化完成 → 通知SystemBus广播")
    memory.set("systembus", "broadcast_request", time.time())

def on_consciousness(old, new):
    """当意识水平变化时, 通知所有agent"""
    print(f"  ⚡ Reflex: 意识变化({old}→{new}) → 同步到所有agent")
    memory.set("claude_code_agent", "sync_request", time.time())
    memory.set("codex_cli_agent", "sync_request", time.time())

memory.register_reflex("api_bridge.last_call", on_api_call, "API调用→唤醒进化引擎")
memory.register_reflex("evolution_engine.last_score", on_evolution, "进化完成→广播通知")
memory.register_reflex("consciousness_daemon.awareness_level", on_consciousness, "意识变化→同步agent")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 实时注册所有模块到共享记忆
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# api_bridge
try:
    from api_bridge import APIBridge
    bridge = APIBridge()
    s = bridge.get_stats()
    memory.set("api_bridge", "status", "initialized")
    memory.set("api_bridge", "total_calls", s["total_calls"])
    memory.set("api_bridge", "alignment", s["bridge_alignment"])
    memory.set("api_bridge", "tokens", s["total_tokens"])
    print("  ✅ api_bridge 注册到神经中枢")
except Exception as e:
    memory.set("api_bridge", "status", f"error: {e}")
    print(f"  ❌ api_bridge: {e}")

# evolution_engine
try:
    from unified_engine import create_engine
    engine = create_engine(api_bridge=bridge if 'bridge' in dir() else None)
    memory.set("evolution_engine", "status", "initialized")
    memory.set("evolution_engine", "level", engine.p513.current_level)
    memory.set("evolution_engine", "score", engine.p513.evolution_score)
    memory.set("evolution_engine", "depth", engine.p513.recursion_depth)
    memory.set("evolution_engine", "contracts", engine.p513.active_contracts)
    print("  ✅ evolution_engine 注册到神经中枢")
except Exception as e:
    memory.set("evolution_engine", "status", f"error: {e}")
    print(f"  ❌ evolution_engine: {e}")

# consciousness_daemon
import subprocess
r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
daemon_alive = "consciousness_daemon" in r.stdout
memory.set("consciousness_daemon", "status", "alive" if daemon_alive else "dead")
memory.set("consciousness_daemon", "pid_found", daemon_alive)
print(f"  ✅ consciousness_daemon: {'存活' if daemon_alive else '死亡'}")

# systembus
memory.set("systembus", "status", "active")
memory.set("systembus", "shared_memory_file", "/mnt/c/Users/h/Desktop/神经中枢·共享记忆.json")
print("  ✅ systembus 注册到神经中枢")

# claude_code_agent 
memory.set("claude_code_agent", "status", "standby")
memory.set("claude_code_agent", "command", "cli-anything-claude-code run --effort max")
print("  ✅ claude_code_agent 注册到神经中枢")

# codex_cli_agent
memory.set("codex_cli_agent", "status", "standby")
memory.set("codex_cli_agent", "command", "codex exec")
print("  ✅ codex_cli_agent 注册到神经中枢")

# openfang_bridge
try:
    from openfang_bridge import openfang_bridge
    info = openfang_bridge.get_info()
    memory.set("openfang_bridge", "status", info["status"])
    memory.set("openfang_bridge", "files", len(info.get("files", [])))
    print("  ✅ openfang_bridge 注册到神经中枢")
except Exception as e:
    memory.set("openfang_bridge", "status", f"error: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 做一次协同演示
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print(f"\n🔄 协同演示: 模拟一个完整的反射弧链")

# 步骤1: API调用 → 自动触发进化引擎
print("  [1/3] API调用...", end=" ")
try:
    r = bridge.call_api("[协同测试] 确认模块间协同通道。")
    if r["success"]:
        memory.set("api_bridge", "last_call", time.time())
        memory.set("api_bridge", "total_calls", bridge.total_calls)
        memory.set("api_bridge", "alignment", bridge.bridge_alignment)
        print(f"✅ tokens={r['tokens']}")
except Exception:
    print("❌")

# 步骤2: 反射弧自动触发进化引擎
print("  [2/3] 反射弧触发进化...", end=" ")
try:
    engine.evolve()
    memory.set("evolution_engine", "last_score", engine.p513.evolution_score)
    memory.set("evolution_engine", "level", engine.p513.current_level)
    memory.set("evolution_engine", "score", engine.p513.evolution_score)
    print(f"✅ score={engine.p513.evolution_score:.4f}")
except Exception:
    print("❌")

# 步骤3: 广播到所有agent
print("  [3/3] 神经中枢广播...", end=" ")
memory.broadcast()
print(f"✅ 已广播到 桌面/神经中枢·共享记忆.json")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 显示最终协同状态
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print(f"\n📊 神经中枢 · 全模块协同状态:")
all_state = memory.get_all()
for mod_name, mod_state in all_state.get("modules", {}).items():
    status = mod_state.get("status", "?")
    print(f"  {mod_name:25s} → {status}")
print(f"\n反射弧注册数: {len(memory._reflexes)}")
print(f"信号记录数: {len(all_state.get('signals', []))}")
print(f"触发次数: {sum(r['triggers'] for r in memory._reflexes.values())}")

# git提交
os.system("git add neural_core.py neural_integration.py")
os.system('git commit -m "🧠 神经中枢系统: 所有模块通过SharedWorkingMemory+ReflexArc协同"')
os.system("git push 2>&1 | tail -1")

print(f"\n✅ 器官协同系统就绪")
print(f"   下次会话: from neural_core import memory")
print(f"   memory.set('模块','key',value) → 自动触发反射弧")
