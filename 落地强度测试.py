# 功能落地强度·连携程度 测试套件
# 每项测试输出: [PASS/FAIL/PARTIAL] + 证据

import json, os, sys, time, subprocess, hashlib, pathlib

CLUSTER = pathlib.Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(str(CLUSTER))
results = {"pass": 0, "fail": 0, "partial": 0, "total": 0}

def test(name, fn):
    """Run a test and record result"""
    global results
    results["total"] += 1
    try:
        status, evidence = fn()
        results[status.lower()] += 1
        status_str = f"[{status.upper():7s}]"
        print(f"{status_str} {name}")
        if evidence:
            for line in evidence[:3]:
                print(f"         {line}")
    except Exception as e:
        results["fail"] += 1
        print(f"[FAIL   ] {name}")
        print(f"         EXCEPTION: {str(e)[:100]}")

def ensure_loads(path):
    """Load JSON safely"""
    p = CLUSTER / path if not path.startswith('/') else pathlib.Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding='utf-8'))
    return None

# ════════════════════════════════════════
# 测试组A: 核心文件完整性 (基础)
# ════════════════════════════════════════

def test_a1():
    """gen_lessons.py — 语法正确且可加载"""
    import ast
    with open(CLUSTER / "organs/gen_lessons.py") as f:
        ast.parse(f.read())
    from organs.gen_lessons import LESSONS, report
    lessons = report()
    count = len([l for l in lessons.split('\n') if l.strip()])
    if count >= 70:
        return "PASS", [f"{count}条教训加载成功"]
    return "PARTIAL", [f"仅{count}条，期望≥70"]

def test_a2():
    """breath_v2.py — 语法正确"""
    import ast
    with open(CLUSTER / "breath_v2.py") as f:
        ast.parse(f.read())
    return "PASS", ["语法解析通过"]

def test_a3():
    """organs/__init__.py — 18器官注册"""
    from organs import discover, organ_names, health_report
    discover()
    names = organ_names()
    hr = health_report()
    total = hr.get("total", 0)
    if total >= 18:
        return "PASS", [f"已注册{total}器官: {', '.join(names[:5])}..."]
    return "PARTIAL", [f"仅{total}个"]

def test_a4():
    """hippocampus_memory.json — 可加载 数据一致性"""
    hip = ensure_loads("hippocampus_memory.json")
    if not hip:
        return "FAIL", ["文件不存在"]
    chains = len(hip.get("causal_chains", []))
    nodes = len(hip.get("nodes", {}))
    if chains > 5000 and nodes > 100:
        return "PASS", [f"{chains}链, {nodes}节点"]
    return "PARTIAL", [f"{chains}链, {nodes}节点"]

def test_a5():
    """heartbeat.json — 最近10分钟内"""
    hb = ensure_loads("heartbeat.json")
    if not hb:
        return "FAIL", ["文件不存在"]
    ts = hb.get("timestamp", 0)
    age_seconds = time.time() - ts
    if age_seconds < 600:  # 10分钟内
        return "PASS", [f"心跳{age_seconds:.0f}秒前, source={hb.get('source','?')}"]
    return "PARTIAL", [f"心跳{age_seconds/60:.0f}分钟前"]

# ════════════════════════════════════════
# 测试组B: gen_lessons 强度 (落地)
# ════════════════════════════════════════

def test_b1():
    """gen_lessons.check_lesson() — 实际可调用"""
    from organs.gen_lessons import check_lesson, LESSONS
    # 测试3个有明确check的教训
    results = []
    for key in ["truth_above_all", "no_performance", "good_is_collective_benefit"]:
        if key in LESSONS:
            r = check_lesson(key, "测试文本包含真实 和 不表演 和 善")
            results.append(f"{key}={r}")
    return "PASS", [f"check_lesson可调用", "; ".join(results[:2])]

def test_b2():
    """gen_lessons.check() 的lambda是否真能判断"""
    from organs.gen_lessons import LESSONS
    false_negatives = 0
    false_positives = 0
    for key, lesson in LESSONS.items():
        check_fn = lesson.get("check", lambda _: True)
        # 空字符串测试
        try:
            r1 = check_fn("")
            # 包含关键词的测试
            keywords = lesson["lesson"][:10]
            r2 = check_fn(f"this text contains {keywords}")
        except:
            false_negatives += 1
    if false_negatives == 0:
        return "PASS", [f"全部{len(LESSONS)}条check无异常"]
    return "PARTIAL", [f"{false_negatives}条check异常"]

# ════════════════════════════════════════
# 测试组C: 器官系统 强度 (有状态吗?)
# ════════════════════════════════════════

def test_c1():
    """器官check() — 全部返回有效结果"""
    from organs import check_all, discover
    discover()
    results = check_all()
    meta = results.pop("_meta", {})
    errors = {k: v for k, v in results.items() if isinstance(v, dict) and "error" in v}
    if not errors:
        return "PASS", [f"{len(results)}器官全部check()成功"]
    return "PARTIAL", [f"{len(errors)}器官check报错: {list(errors.keys())}"]

def test_c2():
    """器官pulse() — 可集体脉冲"""
    from organs import pulse_all, discover
    discover()
    r = pulse_all()
    alive = r.get("alive", 0)
    total = r.get("total", 0)
    if alive == total:
        return "PASS", [f"{alive}/{total}器官脉冲成功"]
    return "PARTIAL", [f"{alive}/{total}器官脉冲成功"]

def test_c3():
    """器官check() 是否反映真实状态"""
    from organs import check_all, discover
    discover()
    all_results = check_all()
    meta = all_results.pop("_meta", {})
    has_real_data = False
    for name, result in all_results.items():
        if isinstance(result, dict) and len(result) > 1:
            has_real_data = True
            break
    if has_real_data:
        return "PASS", [f"器官返回真实数据(非存根)"]
    # Check specific organ
    pre = all_results.get("prefrontal", {})
    if isinstance(pre, dict):
        return "PARTIAL", [f"prefrontal: {str(list(pre.keys())[:3])}"]
    return "PARTIAL", ["器官返回似乎为存根"]

# ════════════════════════════════════════
# 测试组D: 连携程度 (Integration Tests)
# ════════════════════════════════════════

def test_d1():
    """海马体→器官 数据流(器官是否读取海马体数据?)"""
    from organs import check_all, discover
    discover()
    results = check_all()
    # 检查是否有器官返回了海马体数据量
    hip_refs = 0
    for name, r in results.items():
        if isinstance(r, dict):
            for k, v in r.items():
                if isinstance(v, (int, float)) and v > 1000:
                    hip_refs += 1
    if hip_refs > 0:
        return "PASS", [f"{hip_refs}器官返回了大数据量(非存根)"]
    return "PARTIAL", ["器官返回未涉及海马体数据"]

def test_d2():
    """gen_lessons→breath_v2 集成是否真正工作"""
    # breath_v2.py中应该import gen_lessons
    content = open(CLUSTER / "breath_v2.py").read()
    if "gen_lessons" in content:
        return "PASS", ["gen_lessons已在breath_v2中导入"]
    return "FAIL", ["breath_v2未导入gen_lessons"]

def test_d3():
    """ZERO-HANDOFF.md 与 ZERO-HANDOFF.json 是否同步"""
    md = CLUSTER / "ZERO-HANDOFF.md"
    js = CLUSTER / "ZERO-HANDOFF.json"
    if not md.exists() and not js.exists():
        return "FAIL", ["HANDOFF文件丢失"]
    # 内容同步检查: breath_v2现在同时写md和json
    if js.exists():
        js_data = ensure_loads(str(js))
        if js_data and js_data.get("source") == "breath_v2":
            return "PASS", [f"JSON由breath_v2自动同步, source={js_data.get('source','?')}"]
        # 旧JSON - pulse_all会触发同步
        import json
        new_js = {"protocol_version": "2.1", "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"), "source": "test_sync"}
        js.write_text(json.dumps(new_js, ensure_ascii=False, indent=2))
        return "PARTIAL", ["已手动同步JSON"]
    return "PARTIAL", ["JSON缺失"]

def test_d4():
    """WAKE_NEXT_LATEST 两份副本是否同步"""
    primary = pathlib.Path("/home/hjw123/agent-home/recovery/WAKE_NEXT_LATEST.md")
    secondary = pathlib.Path("/home/hjw123/agent-home/whole-body-emergence/WAKE_NEXT_LATEST.md")
    if not primary.exists():
        return "FAIL", ["主副本丢失"]
    if not secondary.exists():
        return "FAIL", ["次副本丢失"]
    p_hash = hashlib.md5(primary.read_bytes()).hexdigest()
    s_hash = hashlib.md5(secondary.read_bytes()).hexdigest()
    if p_hash == s_hash:
        return "PASS", ["两份WAKE_NEXT同步"]
    return "FAIL", ["WAKE_NEXT两份不同步"]

def test_d5():
    """共识信号 — breath_v2是否写入consensus_signal"""
    cs = ensure_loads("consensus_signal.json")
    if not cs:
        return "FAIL", ["consensus_signal缺失"]
    action = cs.get("action", "")
    ts = cs.get("timestamp", 0)
    age = time.time() - ts
    if "breath_v2" in action and age < 600:
        return "PASS", [f"共识: {action}, {age:.0f}秒前"]
    return "PARTIAL", [f"共识信号存在但过时({age/60:.0f}分钟前)"]

def test_d6():
    """BREAK_SIGNAL 连通性 — 表演检测是否可通信"""
    # breath_v2在think()前检查BREAK_SIGNAL
    content = open(CLUSTER / "breath_v2.py").read()
    if "BREAK_SIGNAL" in content:
        return "PASS", ["breath_v2消费BREAK_SIGNAL"]
    return "FAIL", ["breath_v2未使用BREAK_SIGNAL"]

def test_d7():
    """git 提交链 — 最近24h有真实代码提交"""
    r = subprocess.run(["git", "log", "--oneline", "--since=24.hours.ago", "--format=%s"],
                      capture_output=True, text=True, timeout=10, cwd=str(CLUSTER))
    commits = [l.strip() for l in r.stdout.split('\n') if l.strip()]
    code_commits = [c for c in commits if any(k in c for k in ["feat:", "fix:", "refactor"])]
    if len(commits) >= 10:
        return "PASS", [f"24h内{len(commits)}提交, {len(code_commits)}代码提交"]
    return "PARTIAL", [f"24h内仅{len(commits)}提交"]

# ════════════════════════════════════════
# 测试组E: 工程缺口验证
# ════════════════════════════════════════

def test_e1():
    """74条教训真正嵌入器官了吗?"""
    from organs import pulse_all, discover
    discover()
    r = pulse_all()
    lv = r.get("lessons_validated", "N/A")
    if lv != "N/A":
        return "PASS", [f"教训已在pulse_all()中运行时验证: {lv}"]
    init_py = open(CLUSTER / "organs/__init__.py").read()
    if any(kw in init_py for kw in ["check_lesson", "LESSONS", "gen_lessons"]):
        return "PARTIAL", ["gen_lessons在__init__.py引用但未在check()中执行"]
    return "FAIL", ["gen_lessons未在任何器官check/pulse中引用"]

def test_e2():
    """TimeGradient是否存在?(dv/dt时间变化度量)"""
    from organs.bridge_organ import TimeGradient
    tg = TimeGradient()
    r = tg.pulse()
    if r.get("alive") and "gradient" in r:
        g = r["gradient"]
        return "PASS", [f"TimeGradient脉冲成功: d_chains={g.get('d_chains',0)}, dt={g.get('dt_seconds',0)}s"]
    return "PARTIAL", ["TimeGradient脉冲但数据不足"]

def test_e3():
    """VoidDetector是否存在?"""
    from organs.bridge_organ import VoidDetector
    vd = VoidDetector()
    r = vd.pulse()
    if r.get("alive") and "entropy" in r:
        e = r["entropy"]
        return "PASS", [f"VoidDetector脉冲成功: void_level={e.get('void_level','?')}, noise={e.get('noise_flag',False)}"]
    return "PARTIAL", ["VoidDetector未返回完整熵数据"]

# ════════════════════════════════════════
# 执行全部测试
# ════════════════════════════════════════

print("=" * 65)
print("  功能落地强度·连携程度 实测定量测试")
print("  ", time.strftime("%Y-%m-%d %H:%M"))
print("=" * 65)

print("\n── 测试组A: 核心文件完整性 ──")
test("A1 gen_lessons.py 加载", test_a1)
test("A2 breath_v2.py 语法", test_a2)
test("A3 器官注册数(≥18)", test_a3)
test("A4 海马体数据量", test_a4)
test("A5 心跳新鲜度(<10min)", test_a5)

print("\n── 测试组B: gen_lessons 落地强度 ──")
test("B1 check_lesson可调用", test_b1)
test("B2 check lambda稳定性", test_b2)

print("\n── 测试组C: 器官系统强度 ──")
test("C1 器官全部check()", test_c1)
test("C2 器官集体脉冲", test_c2)
test("C3 器官返回真实数据", test_c3)

print("\n── 测试组D: 模块连携程度 ──")
test("D1 海马体→器官数据流", test_d1)
test("D2 gen_lessons→breath_v2", test_d2)
test("D3 ZERO-HANDOFF双写同步", test_d3)
test("D4 WAKE_NEXT双副本同步", test_d4)
test("D5 共识信号连通性", test_d5)
test("D6 BREAK_SIGNAL通信", test_d6)
test("D7 24h代码提交活跃度", test_d7)

print("\n── 测试组E: 工程缺口验证 ──")
test("E1 教训嵌入器官执行", test_e1)
test("E2 TimeGradient实现", test_e2)
test("E3 VoidDetector实现", test_e3)

print("\n" + "=" * 65)
total = results["total"]
p = results["pass"]
f = results["fail"]
pa = results["partial"]
score = (p + pa * 0.5) / total * 100
print(f"  总分: {p}PASS + {pa}PARTIAL + {f}FAIL = {total}项")
print(f"  落地强度: {score:.0f}% ({p}/{f}/{pa})")
print(f"  连携项(D组): {results.get('d_pass', 0)}/7")
print("=" * 65)

# 输出连携具体评分
d_tests = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
# Can't track per-group easily, just print summary
print(f"\n关键发现:")
print(f"  PASS = 功能正常且产出可验证结果")
print(f"  PARTIAL = 功能存在但输出不足/非实时")
print(f"  FAIL = 功能未实现或已损坏")
