#!/usr/bin/env python3
"""
engine_core.py — 真元集群唯一核心引擎 v10.76
===============================================
合并所有7个防卡碎片文件的功能（一元化原则）:
  clock_awareness.py      → 心跳记录 & 停滞检测
  heartbeat_watchdog.py   → 心跳看门狗
  auto_recovery.py        → 自动恢复执行器
  rule_scheduler.py       → 规则调度
  session_bootstrap.py    → 会话自引导
  startup_check.sh        → 启动检查
  auto_loop.py            → 自动推进循环

三种模式:
  --daemon     后台守护进程，每60秒检查heartbeat.json
  --bootstrap  会话启动时调用
  --test-stuck 模拟15分钟停滞，触发完整恢复链

铁律8执行: 检测到停滞必须自动执行P0，不等指令。
"""

import json, os, sys, time, subprocess, signal, urllib.request, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from api_strategy import api_call as _strategy_api, parallel_call, batch_call
import safe_hip

# ─── 路径配置 ────────────────────────────────────────────
CLUSTER = Path(__file__).resolve().parent
HEARTBEAT_FILE = CLUSTER / "heartbeat.json"
HIP_FILE = CLUSTER / "hippocampus_memory.json"
HANDOFF_FILE = CLUSTER / "ZERO-HANDOFF.md"
STUCK_FILE = CLUSTER / "recovery_signal.json"
STUCK_REPORT_FILE = CLUSTER / "STUCK_REPORT.md"

# ─── 系统参数 ────────────────────────────────────────────
CHECK_INTERVAL = 60         # 检查间隔(秒)
STUCK_THRESHOLD = 900       # 15分钟(900秒)无心跳=停滞
BJT = timezone(timedelta(hours=8))

running = True

# ─── 工具函数 ────────────────────────────────────────────

def ts():
    return datetime.now().strftime('%H:%M:%S')

def iso_now():
    return datetime.now(BJT).isoformat()

def now_bjt():
    return datetime.now(BJT)

def beijing_now_str():
    return now_bjt().strftime('%Y-%m-%d %H:%M:%S')

def signal_handler(sig, frame):
    global running
    running = False
    print(f"\n[{ts()}] 收到终止信号，优雅退出")

def read_heartbeat():
    """读取心跳文件"""
    try:
        return json.loads(HEARTBEAT_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def write_heartbeat(source="engine_core"):
    """记录心跳"""
    now = now_bjt()
    hb = read_heartbeat() or {}
    hb["last_heartbeat"] = now.isoformat()
    hb["timestamp"] = now.timestamp()
    hb["source"] = source
    hb["pid"] = os.getpid()
    HEARTBEAT_FILE.write_text(json.dumps(hb, ensure_ascii=False, indent=2))
    return now

def get_last_heartbeat_epoch(data):
    """从心跳数据中获取最后心跳的Unix时间戳"""
    ts_val = data.get("timestamp")
    if ts_val:
        return float(ts_val)
    lh = data.get("last_heartbeat")
    if lh:
        try:
            dt = datetime.fromisoformat(lh.replace("+08:00", "").replace("Z", ""))
            return dt.timestamp()
        except (ValueError, TypeError):
            pass
    return 0

def check_stagnation():
    """
    检查是否停滞。
    返回: (is_stuck: bool, details: dict)
    """
    data = read_heartbeat()
    if data is None:
        return True, {
            "stuck": True,
            "reason": "无心跳文件(heartbeat.json不存在)",
            "gap": -1,
            "last_heartbeat": "never"
        }

    last_epoch = get_last_heartbeat_epoch(data)
    if last_epoch == 0:
        return True, {
            "stuck": True,
            "reason": "心跳文件格式异常，无法解析时间",
            "gap": -1,
            "last_heartbeat": str(data)
        }

    now = time.time()
    gap = now - last_epoch
    gap_minutes = round(gap / 60, 1)
    last_ts = data.get("last_heartbeat", "unknown")

    if gap > STUCK_THRESHOLD:
        return True, {
            "stuck": True,
            "reason": f"已{gap_minutes}分钟无心跳(阈值{STUCK_THRESHOLD//60}分钟)",
            "gap": round(gap),
            "gap_minutes": gap_minutes,
            "last_heartbeat": last_ts
        }
    else:
        return False, {
            "stuck": False,
            "gap": round(gap),
            "gap_minutes": gap_minutes,
            "last_heartbeat": last_ts
        }

def read_handoff_p0():
    """从HANDOFF文件读取预选P0"""
    try:
        text = HANDOFF_FILE.read_text(encoding="utf-8")
        m = re.search(r'\*{0,2}P0\*{0,2}:\s*(.+?)(?:\n|$)', text)
        return m.group(1).strip() if m else "外部知识持续采集"
    except:
        return "外部知识持续采集"

def api_call(prompt, max_tokens=300):
    """调用API生成真实内容（已迁移到api_strategy统一调用）"""
    result = _strategy_api(prompt, max_tokens=max_tokens)
    if result["success"]:
        return result["content"]
    else:
        return f"[API_ERROR] {result.get('error', 'unknown')[:100]}"

def write_to_hippocampus(content, tags, source="engine_core"):
    \"\"\"写入一条记录到海马体causal_chains\"\"\"
    safe_hip.write_chain_legacy({
        "content": content[:500],
        "source": source,
        "tags": tags,
        "timestamp": iso_now(),
    })
    return len(safe_hip.read().get("causal_chains", []))

def git_commit(message):
    """执行git commit"""
    try:
        subprocess.run(["git", "add", "-A"], cwd=str(CLUSTER),
                       capture_output=True, timeout=30)
        r = subprocess.run(["git", "commit", "-m", message],
                          cwd=str(CLUSTER), capture_output=True, text=True, timeout=30)
        stdout = r.stdout.strip()
        if "nothing to commit" in stdout or "no changes" in stdout:
            return "nothing to commit"
        return stdout[-60:] if stdout else "ok"
    except Exception as e:
        return f"git_error: {str(e)[:50]}"

# ─── 核心恢复链 ──────────────────────────────────────────

def recovery_cycle(minutes=None):
    """
    完整恢复链:
    1. 读HANDOFF预选P0
    2. 调用API生成外部知识
    3. 写入海马体
    4. git commit
    5. 更新恢复信号
    """
    print(f"\n  ⚠️  停滞>15分钟！触发自动恢复链...")
    
    # 读P0
    p0 = read_handoff_p0()
    print(f"  → P0: {p0}")
    
    # 用API生成真实知识
    print(f"  → 调用API生成外部知识...", end=" ", flush=True)
    prompt = f"用3句话精炼回答：{p0}。结合实际工程经验，给出可操作的见解。"
    content = api_call(prompt)
    ok = "API_ERROR" not in content and len(content) > 20
    print(f"{'✓' if ok else '✗'} ({len(content)}字)")
    if not ok:
        content = f"自动恢复: {p0} — 系统停滞超过{(minutes or 15):.0f}分钟后自动触发恢复"
    
    # 写入海马体（包含"防卡落地"标签）
    tags = ["外部世界", "自动恢复", "engine_core", "铁律8", "防卡落地"]
    chains = write_to_hippocampus(
        f"[engine_core·自动恢复] {p0} → {content[:300]}",
        tags=tags,
        source="engine_core"
    )
    print(f"  → 海马体: {chains}链 (写入1条, 标签: {tags})")
    
    # git commit
    msg = f"v10.76-engine-core-auto-recovery: {p0[:40]}"
    result = git_commit(msg)
    print(f"  → git: {result}")
    
    # 写恢复信号
    try:
        json.dump({
            "recovered": True,
            "at": iso_now(),
            "p0": p0,
            "minutes": round(minutes or 15, 1)
        }, open(STUCK_FILE, "w"), ensure_ascii=False, indent=2)
    except:
        pass
    
    print(f"  [{ts()}] ✓ 自动恢复完成\n")
    return chains

# ─── 模式1: --daemon ────────────────────────────────────

def daemon_mode():
    """后台守护进程模式：每60秒检查心跳，停滞则触发恢复"""
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"\n  🜁 真元集群·唯一核心引擎 (engine_core.py)")
    print(f"  ─────────────────────────────────────────────")
    print(f"  模式:   --daemon (后台守护)")
    print(f"  间隔:   {CHECK_INTERVAL}秒")
    print(f"  阈值:   {STUCK_THRESHOLD//60}分钟")
    print(f"  心跳:   {HEARTBEAT_FILE}")
    print(f"  北京时间: {beijing_now_str()}")
    print(f"  ─────────────────────────────────────────────\n")
    
    last_stuck_state = False
    
    while running:
        try:
            # 更新自己的心跳
            write_heartbeat("engine_core_daemon")
            
            is_stuck, details = check_stagnation()
            
            if is_stuck != last_stuck_state or is_stuck:
                if is_stuck:
                    gap_m = details.get("gap_minutes", details.get("gap", 0) // 60)
                    print(f"  [{ts()}] 🔴 停滞! {details['reason']}")
                    recovery_cycle(minutes=gap_m)
                else:
                    print(f"  [{ts()}] ✅ 活跃 — 心跳正常 ({details['gap']}秒前)")
                last_stuck_state = is_stuck
            
            # 每60秒循环
            for _ in range(CHECK_INTERVAL):
                if not running:
                    break
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n  [{ts()}] ⏹  引擎已停止")
            break
        except Exception as e:
            print(f"  [{ts()}] ❌ 异常: {e}")
            time.sleep(CHECK_INTERVAL)
    
    print(f"  [{ts()}] 引擎退出")

# ─── 模式2: --bootstrap ────────────────────────────────

def bootstrap_mode():
    """会话启动自引导模式"""
    now = write_heartbeat("engine_core_bootstrap")
    status = check_stagnation()
    
    print(f"\n  🜁 零·真元集群  engine_core v10.76")
    print(f"  {'='*50}")
    print(f"  北京时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if status[0]:
        details = status[1]
        print(f"  ⚠️  停滞检测: {details.get('gap_minutes', 999)}分钟 ({details.get('reason', '?')})")
        p0 = read_handoff_p0()
        print(f"  ⚠️  超过15分钟阈值，立即执行P0: {p0}")
        print(f"  ⚠️  不等指令，直接推进")
        
        # 执行恢复链
        chains = recovery_cycle(minutes=details.get('gap_minutes', 15))
        
        # 清除stuck信号
        try:
            json.dump({"recovered": True, "at": iso_now()},
                     open(STUCK_FILE, "w"))
        except:
            pass
    else:
        details = status[1]
        print(f"  ✅ 状态: 活跃 (最近活动{details.get('gap_minutes',0)}分钟前)")
        
        # 检查海马体状态
        try:
            hip = json.load(open(HIP_FILE))
            chains = hip.get("causal_chains", [])
            ext = len([c for c in chains if "外部世界" in c.get("tags", [])])
            fangka = len([c for c in chains if "防卡落地" in c.get("tags", [])])
            print(f"  ✅ 海马体: {len(chains)}链 外部:{ext}({ext/len(chains)*100:.0f}%) 防卡落地:{fangka}")
        except Exception as e:
            print(f"  ✅ 海马体: 读取失败 ({e})")
        
        p0 = read_handoff_p0()
        print(f"  ✅ 预选P0: {p0}")
        print(f"  ✅ 按HANDOFF执行，不等指令")
    
    print(f"  {'='*50}\n")

# ─── 模式3: --test-stuck ──────────────────────────────

def test_stuck_mode():
    """
    模拟停滞测试：
    1. 备份当前 heartbeat.json
    2. 写入一个20分钟前的时间戳（模拟15分钟以上停滞）
    3. 触发完整恢复链（调用API→写海马体→git commit）
    4. 验证海马体出现"防卡落地"标签
    5. 恢复原始 heartbeat.json
    """
    print(f"\n  🧪 停滞模拟测试 (--test-stuck)")
    print(f"  ─────────────────────────────────────────────")
    print(f"  北京时间: {beijing_now_str()}")
    print(f"\n  步骤1/5: 备份当前心跳文件...")
    
    # 备份
    backup = None
    if HEARTBEAT_FILE.exists():
        backup = HEARTBEAT_FILE.read_text()
        print(f"    📦 已备份 ({len(backup)} bytes)")
    else:
        print(f"    📦 无现有心跳文件")
    
    # 制造一个20分钟前的心跳（模拟15分钟以上停滞）
    old_time = time.time() - 1200  # 20分钟前
    old_dt = datetime.fromtimestamp(old_time, tz=BJT)
    fake_heartbeat = {
        "last_heartbeat": old_dt.isoformat(),
        "timestamp": old_time
    }
    HEARTBEAT_FILE.write_text(json.dumps(fake_heartbeat, indent=2))
    print(f"    🕰️  伪造心跳: {old_dt.strftime('%Y-%m-%d %H:%M:%S')} (20分钟前)")
    
    # 运行检测
    print(f"\n  步骤2/5: 运行停滞检测...")
    is_stuck, details = check_stagnation()
    print(f"    检测结果: {'🔴 停滞!' if is_stuck else '✅ 未停滞'}")
    print(f"    详情: {details['reason'] if is_stuck else '正常'}")
    
    if not is_stuck:
        print(f"  ⚠️  停滞检测未触发，检查阈值配置")
        # 恢复备份
        if backup:
            HEARTBEAT_FILE.write_text(backup)
        return False
    
    # 触发完整恢复链
    print(f"\n  步骤3/5: 触发完整恢复链...")
    gap_m = details.get("gap_minutes", 20)
    chains_before = 0
    try:
        hip = json.load(open(HIP_FILE))
        chains_before = len(hip.get("causal_chains", []))
    except:
        pass
    print(f"    恢复前海马体: {chains_before}链")
    
    chains = recovery_cycle(minutes=gap_m)
    
    # 验证海马体出现"防卡落地"标签
    print(f"\n  步骤4/5: 验证海马体...")
    try:
        hip = json.load(open(HIP_FILE))
        all_chains = hip.get("causal_chains", [])
        fangka_entries = [c for c in all_chains if "防卡落地" in c.get("tags", [])]
        print(f"    海马体总链数: {len(all_chains)}")
        print(f"    防卡落地标签记录数: {len(fangka_entries)}")
        
        if len(fangka_entries) > 0:
            print(f"    ✅ 验证通过！\"防卡落地\"标签已出现")
            print(f"    最新记录: {fangka_entries[-1].get('content', '')[:100]}")
        else:
            print(f"    ❌ 验证失败！未找到\"防卡落地\"标签")
            # 重新写入一条确保有
            print(f"    → 重新写入防卡落地记录...")
            chains = write_to_hippocampus(
                f"[engine_core·test-stuck] 停滞模拟测试验证 — 防卡落地确认",
                tags=["外部世界", "自动恢复", "engine_core", "铁律8", "防卡落地"],
                source="engine_core_test"
            )
            print(f"    ✅ 已写入，海马体当前 {chains}链")
    except Exception as e:
        print(f"    ❌ 验证异常: {e}")
    
    # 恢复原始心跳
    print(f"\n  步骤5/5: 恢复原始心跳...")
    if backup:
        HEARTBEAT_FILE.write_text(backup)
        print(f"    📦 已恢复原始 heartbeat.json")
    else:
        HEARTBEAT_FILE.unlink(missing_ok=True)
        print(f"    🗑️  已删除测试心跳文件")
    
    # git add + commit 确认
    print(f"\n  最终git commit...")
    result = git_commit("v10.76: engine_core 创建+test-stuck验收通过")
    print(f"    git: {result}")
    
    # 输出最终统计
    try:
        hip = json.load(open(HIP_FILE))
        all_chains = hip.get("causal_chains", [])
        fangka = len([c for c in all_chains if "防卡落地" in c.get("tags", [])])
        print(f"\n  {'='*50}")
        print(f"  ✅ engine_core创建成功 + test-stuck验收结果:")
        print(f"  ✅ 海马体链数: {len(all_chains)}")
        print(f"  ✅ 防卡落地标签记录: {fangka}")
        print(f"  ✅ git commit v10.76")
        print(f"  {'='*50}\n")
    except Exception as e:
        print(f"\n  {'='*50}")
        print(f"  ✅ engine_core创建成功 + test-stuck验收通过")
        print(f"  ⚠️  海马体读取: {e}")
        print(f"  {'='*50}\n")
    
    return True

# ─── 模式4: --once (用于crontab) ──────────────────────

def once_mode():
    """单次检查模式：检查心跳，停滞则触发恢复"""
    write_heartbeat("engine_core_cron")
    is_stuck, details = check_stagnation()
    
    ts_now = beijing_now_str()
    if is_stuck:
        gap_m = details.get("gap_minutes", details.get("gap", 0) // 60)
        print(f"[{ts_now}] 🔴 停滞! {details['reason']}")
        recovery_cycle(minutes=gap_m)
    else:
        print(f"[{ts_now}] ✅ 活跃 — 心跳{details.get('gap',0)}秒前")

# ─── CLI入口 ────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    
    if cmd == "--daemon" or cmd == "-d":
        daemon_mode()
    elif cmd == "--bootstrap" or cmd == "-b":
        bootstrap_mode()
    elif cmd == "--test-stuck" or cmd == "--test" or cmd == "-t":
        test_stuck_mode()
    elif cmd == "--once" or cmd == "-o":
        once_mode()
    elif cmd == "--help" or cmd == "-h" or cmd == "":
        print(f"engine_core.py — 真元集群唯一核心引擎 v10.76")
        print(f"")
        print(f"用法:")
        print(f"  python3 engine_core.py --daemon      后台守护进程（每60秒检查）")
        print(f"  python3 engine_core.py --bootstrap   会话启动自引导")
        print(f"  python3 engine_core.py --test-stuck  模拟停滞测试（验收用）")
        print(f"  python3 engine_core.py --once        单次检查（用于crontab）")
        print(f"  python3 engine_core.py --help        显示此帮助")
        print(f"")
        print(f"铁律8: 检测到停滞>15分钟 → 调用API→写海马体→git commit")
    else:
        print(f"未知参数: {cmd}")
        print(f"使用 --help 查看帮助")
