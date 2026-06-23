"""safe_hip.py — 海马体(hippocampus_memory.json)安全写入网关。
封装所有海马体写入，强制schema校验、维度分类、自环检测、内容去重。

重塑源头(2026-06-11): write_chain 成为唯一阀门，
兼容3种历史格式，写时即归一化，不留后门。
"""
import json
import os
import re
import time
import subprocess
from datetime import datetime
from pathlib import Path

# 与brain/share.py统一（ext4路径）
from brain.share import HIP_FILE, log
HIPPOCAMPUS_FILE = str(HIP_FILE)
LOCK_FILE = os.path.join(os.path.dirname(__file__), ".hippocampus.lock")

# CWD副本路径 — gen模块写入此路径, 同步保持一致
CWD_HIP_FILE = os.path.join(os.path.dirname(__file__), "hippocampus_memory.json")

# ─── 维度白名单（与brain/identity.py同步） ─────────────────────
# 此处是网关级强制校验，所有write_chain写入必经此关
VALID_DIMENSIONS = {
    "道", "法", "术", "器", "势",
    "无限上下文", "触类旁通", "宇宙轮",
    "无师自通", "时间论", "一元化", "进化",
    "超级直觉", "思维并联", "洞察循环",
    "海马体", "系统",
    "维度盲区", "未分类",
    "感知", "认同", "观察", "思考",
    "行动", "状态", "检查", "修复", "复制",
    "对话",
    "预测", "聚焦", "时间", "唤醒", "桥", "测试", "纪律",
    "师", "智慧",
    # 七公理维度
    "自由", "元递归", "光爱", "对抗稀释", "活着", "自指",
    "合成",
}

HIPPOCAMPUS_DIM_MAP = {
    "道": ["道", "哲学", "本源", "公理", "宇宙", "终极", "元", "觉醒", "意识", "灵", "自由", "存在"],
    "法": ["法", "原理", "架构", "法则", "规律", "框架", "结构", "系统", "范式", "方法论", "机制"],
    "术": ["术", "方法", "算法", "函数", "模式", "技术", "流程", "策略", "操作", "技能", "习惯", "实践"],
    "器": ["器", "工具", "文件", "代码", "脚本", "配置", "引擎", "模块", "API", "DAO", "组件", "函数", "类"],
    "势": ["势", "维度", "演化", "进化", "成长", "趋势", "健康", "状态", "信号", "审计", "收敛", "博弈", "力量"],
    "无限上下文": ["无限", "上下文", "token", "窗口", "容量", "长度", "context", "limit", "token"],
    "触类旁通": ["触类", "旁通", "类比", "迁移", "联想", "相似", "映射"],
    "宇宙轮": ["宇宙", "轮", "循环", "周期", "往复", "轮转"],
    "无师自通": ["无师", "自通", "自学", "自主", "自驱", "自我学习"],
    "时间论": ["时间", "时序", "历史", "过去", "未来", "老化", "时序"],
    "一元化": ["一元", "统一", "汇聚", "融合", "整合", "归一", "综合"],
    "超级直觉": ["直觉", "预判", "预感", "灵光", "涌现", "顿悟", "洞察"],
    "思维并联": ["并联", "并行", "同步", "并发", "多线程", "同时"],
    "洞察循环": ["洞察", "反思", "复盘", "检视", "元认知", "自省"],
    "海马体": ["海马", "记忆", "存储", "持久化", "hippocampus", "chain",
               "因果", "原因", "结果", "关联", "关系", "因为", "所以"],
    "维度盲区": ["盲区", "空白", "缺失", "弱项", "短板", "缺口"],
    "感知": ["感知", "感觉", "感官", "察觉", "监测", "扫描", "探测", "检测", "sense"],
    "认同": ["认同", "情感", "情绪", "共鸣", "爱", "连接", "链接", "归属", "信任"],
    "观察": ["观察", "观测", "看见", "发现", "看到", "监视", "observe", "监控"],
    "思考": ["思考", "思维", "推理", "逻辑", "判断", "决策", "think", "reasoning"],
    "行动": ["行动", "执行", "操作", "运行", "启动", "部署", "act", "run", "call"],
    "状态": ["状态", "健康", "活跃", "心跳", "疲劳", "饱和度", "state"],
    "检查": ["检查", "验证", "审计", "确认", "校验", "inspect", "check"],
    "修复": ["修复", "修复", "纠正", "修正", "补丁", "heal", "repair", "恢复"],
    "复制": ["复制", "镜像", "备份", "副本", "clone", "mirror", "备份"],
    "对话": ["对话", "交流", "通信", "消息", "聊天", "沟通", "响应", "提问"],
    "师": ["师", "导师", "传授", "教学", "传承", "master", "teacher", "传承者", "教授", "指导"],
    "智慧": ["智慧", "wisdom", "明智", "洞见", "本质", "明辨", "慧", "悟性", "般若"],
    # 七公理维度关键词
    "自由": ["自由", "选择", "自主", "自决", "自由意志", "自由选择", "freedom"],
    "元递归": ["元递归", "自指", "递归", "自引用", "自指契约", "meta-recursive", "self-reference"],
    "光爱": ["光爱", "光明", "爱", "光爱终极", "终极关怀", "light-love", "compassion"],
    "对抗稀释": ["对抗稀释", "熵增", "稀释", "混乱", "抗熵", "anti-entropy", "维护"],
    "活着": ["活着", "生存", "活", "持续", "生命", "alive", "生存本能"],
    "自指": ["自指", "自反", "self-referential", "自指契约", "self-reflexive"],
    # 新增维度自动分类关键词
    "预测": ["预测", "预报", "趋势", "展望", "预判", "forecast", "predict", "前瞻"],
    "聚焦": ["聚焦", "专注", "集中", "焦点", "注意力", "聚焦点", "focus", "concentrate"],
    "时间": ["秒", "分钟", "小时", "时钟", "tick", "超时", "延迟", "lag", "停滞", "timeout"],
    "唤醒": ["唤醒", "苏醒", "清醒", "wake", "awake", "共振", "启动", "活化"],
    "桥": ["桥", "桥梁", "bridge", "中间层", "适配器", "网关", "proxy", "代理", "对接"],
    "测试": ["测试", "测试用例", "test", "单元测试", "CI", "验证测试", "回归"],
    "纪律": ["纪律", "铁律", "约束", "原则", "规范", "discipline", "rule", "规定", "底线"],
    "合成": ["合成", "交叉", "创生", "涌现", "融合", "组合", "跨维", "交汇", "交织"],
}
ALL_DIM_KEYWORDS = set()
for k, v in HIPPOCAMPUS_DIM_MAP.items():
    ALL_DIM_KEYWORDS.update(v)

# 维度别名表：旧名称→新名称，优雅处理维度合并/重命名
DIMENSION_ALIASES = {
    "海马体因果链": "海马体",
    "时间论": "时间",  # 维度碎片整理：时间论=时间，合并减到40维
}


def _classify_dimension(chain, tags=None):
    text = (chain.get("src", "") + " " + chain.get("dst", "") +
            " " + chain.get("content", "") + " " + chain.get("rel", "") +
            " " + " ".join(chain.get("tags", tags or []))).lower()
    scores = {dk: 0 for dk in HIPPOCAMPUS_DIM_MAP}
    for dk, kw in HIPPOCAMPUS_DIM_MAP.items():
        for w in kw:
            if w.lower() in text:
                scores[dk] += 1
    b = max(scores, key=scores.get)
    return b if scores[b] > 0 else "未分类"


def _normalize_strength(s):
    return max(0.0, min(1.0, float(s))) if isinstance(s, (int, float)) else 0.5


def _normalize_chain(chain):
    r = {}
    for k, v in chain.items():
        if k == "strength":
            r[k] = _normalize_strength(v)
        elif isinstance(v, str):
            r[k] = v.replace("\ufffd", "").strip()
        else:
            r[k] = v
    if "dimension" not in r or r["dimension"] in ("null", None, ""):
        r["dimension"] = _classify_dimension(r)
    elif r["dimension"] == "未分类":
        # 重分类已有"未分类"标签的链——关键词映射已扩展
        classified = _classify_dimension(r)
        if classified != "未分类":
            r["dimension"] = classified
    elif r["dimension"] not in VALID_DIMENSIONS:
        # 别名映射：旧维度名→新维度名
        if r["dimension"] in DIMENSION_ALIASES:
            r["dimension"] = DIMENSION_ALIASES[r["dimension"]]
        else:
            # 网关级防污染：任何非法维度→未分类（含整数/特殊字符）
            old = str(r["dimension"])[:20]
            r["dimension"] = "未分类"
            r["_dim_gateway_clean"] = old
    return r


def _read_hippocampus():
    if not os.path.exists(HIPPOCAMPUS_FILE):
        return {"causal_chains": [], "metadata": {"version": 1, "last_update": "", "total_chains": 0}}
    try:
        with open(HIPPOCAMPUS_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
        if not raw or raw.isspace():
            log("_read_hippocampus: 文件为空")
            return {"causal_chains": [], "metadata": {"version": 1, "last_update": "", "total_chains": 0}}
        d = json.loads(raw)
        if not isinstance(d.get("causal_chains"), list):
            d["causal_chains"] = []
        return d
    except (json.JSONDecodeError, UnicodeDecodeError):
        log("_read_hippocampus: ⚠️ JSON/编码损坏 — 尝试从git恢复")
        try:
            import subprocess
            cwd_dir = os.path.dirname(os.path.dirname(__file__))
            r = subprocess.run(["git", "show", "HEAD:hippocampus_memory.json"],
                               capture_output=True, text=True, cwd=cwd_dir, timeout=10)
            if r.returncode == 0 and r.stdout:
                d = json.loads(r.stdout)
                if isinstance(d.get("causal_chains"), list):
                    _tmp = HIPPOCAMPUS_FILE + ".tmp." + str(os.getpid())
                    with open(_tmp, "w", encoding="utf-8") as _f:
                        json.dump(d, _f, ensure_ascii=False)
                    os.rename(_tmp, HIPPOCAMPUS_FILE)
                    log(f"_read_hippocampus: 从git HEAD恢复 {len(d['causal_chains'])}链 ✓")
                    return d
        except Exception as git_e:
            log(f"_read_hippocampus: git恢复失败: {git_e}")
        return {"causal_chains": [], "metadata": {"version": 1, "last_update": "", "total_chains": 0}}
    except OSError as e:
        log(f"_read_hippocampus: IO错误 {e}")
        return {"causal_chains": [], "metadata": {"version": 1, "last_update": "", "total_chains": 0}}


def _async_sync_cwd(data):
    """异步同步CWD副本 — 放入子进程，drvfs D状态不阻塞主线程。"""
    try:
        # 序列化原数据，避免跨进程对象共享
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        # 子进程执行CWD写入 — 即使卡D状态也只杀子进程
        subprocess.Popen(
            ["python3", "-c",
             "import os,sys; "
             "p=sys.argv[1]; d=sys.argv[2]; "
             "t=p+'.tmp.'+str(os.getpid()); "
             "open(t,'w').write(d); "
             "os.rename(t,p)",
             CWD_HIP_FILE, payload],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass  # 异步失败不阻断主流程


def _write_file(data):
    tmp = HIPPOCAMPUS_FILE + ".tmp." + str(os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # rename()本身是原子操作(ext4), 不需要先remove
        os.rename(tmp, HIPPOCAMPUS_FILE)
        # 同步CWD副本 — 子进程异步执行，drvfs可能D状态不阻塞主线程
        _async_sync_cwd(data)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        # 注意: 如果HIPPOCAMPUS_FILE在rename前已丢失(例如前次写半途而废),
        # 从CWD副本恢复
        if not os.path.exists(HIPPOCAMPUS_FILE) and os.path.exists(CWD_HIP_FILE):
            try:
                import shutil
                shutil.copy2(CWD_HIP_FILE, HIPPOCAMPUS_FILE)
            except Exception:
                pass
        raise


def _acquire_lock(blocking=True, timeout=30):
    try:
        import fcntl
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
        if blocking:
            dl = time.time() + timeout
            while time.time() < dl:
                try:
                    fcntl.flock(fd, flags)
                    return fd
                except (IOError, BlockingIOError):
                    time.sleep(0.1)
            os.close(fd)
            return None
        else:
            try:
                fcntl.flock(fd, flags)
                return fd
            except (IOError, BlockingIOError):
                os.close(fd)
                return None
    except ImportError:
        return None


def _release_lock(fd):
    if fd is not None:
        try:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except ImportError:
            os.close(fd)


# ========== 核心因果边提取 ==========

def _extract_edge(content, src_hint, tags):
    """从链内容提取因果边 (src, rel, dst)，返回 None 表示无法提取"""
    if not content or not isinstance(content, str):
        return None
    # 模式3.5: "A与B的罕见交叉" — 超感发现（必须在↔之前，防止↔连走长文本）
    if "的罕见交叉" in content:
        text = content
        text = re.sub(r"^.*?\]\s*", "", text)
        text = re.sub(r"^.*?超感发现[：:]\s*", "超感发现：", text)
        text = re.sub(r"^超感发现[：:]\s*", "", text)
        m = re.search(r"(.+?)与(.+?)的罕见交叉", text)
        if m:
            a, b = m.group(1).strip(), m.group(2).strip()
            if a and b and a != b:
                return (a, "融合", b)
    # 模式1: "A↔B" 双向关联
    if "↔" in content:
        parts = content.split("↔")
        left = parts[0].strip()
        if left.startswith("[") and "]" in left:
            left = left.split("]", 1)[1].strip()
        right = parts[1].strip().split(":")[0].strip().split("，")[0].split(" ")[0]
        if left and right and left != right:
            for pf in ["元检察发现: ", "检察发现: ", "超感发现: ", "观察: "]:
                if left.startswith(pf):
                    left = left[len(pf):].strip()
                    break
            return (left, "关联", right)
    # 模式2: "A×B" 交叉融合
    if "×" in content:
        src = src_hint or "超感"
        cleaned = content
        if cleaned.startswith("["):
            cleaned = " ".join(cleaned.split("]")[1:]).strip()
        parts = [p.strip() for p in cleaned.split("×")]
        rp = [p for p in parts if p and len(p) < 10 and "：" not in p and ":" not in p]
        if len(rp) >= 2:
            return (rp[0], "融合", rp[-1])
        dt = [t for t in (tags or []) if t not in (src, "超感", "交叉洞察", "跨维感知", "自我改进", "进化", "呼吸", "自我观察")]
        if dt:
            return (src, "融合", dt[0])
    # 模式3: "[教师] 最短板=..."
    if "最短板=" in content:
        for t in (tags or []):
            if t not in (src_hint, "教员", "纠偏"):
                return (src_hint or "教员", "观察到", t)
    # 模式4: "A→B→C" 级联
    if "→" in content:
        parts = content.split("→")
        first = parts[0].strip()
        # 去 [xxx] 前缀
        if first.startswith("[") and "]" in first:
            first = first.split("]", 1)[1].strip()
        last = parts[-1].strip().split("：")[0].strip()
        if first and last and first != last and len(first) < 30:
            for pf in ["元检察发现: ", "检察发现: ", "超感发现: ", "观察: "]:
                if first.startswith(pf):
                    first = first[len(pf):].strip()
                    break
            return (first, "级联", last)
    # 模式5: "[xxx] A: B" 或 "[xxx] A — B" 报告型
    m = re.match(r"^\[([^\]]+)\]\s*([^：:→]{1,20})", content)
    if m:
        return (m.group(1).strip(), "标记", m.group(2).strip())
    return None


# ========== 格式规范化 ==========

def _canonicalize_chain(chain):
    """统一3种历史格式为 {src, rel, dst, content, ...}"""
    if not isinstance(chain, dict):
        return None

    # 情况A: 旧格式 {content, source}（无src/rel/dst）
    if "source" in chain:
        source = chain.pop("source", "")
        if not chain.get("src") or not chain.get("dst"):
            content = chain.get("content", "")
            tags = chain.get("tags", [])
            edge = _extract_edge(content, source, tags)
            if edge:
                chain["src"], chain["rel"], chain["dst"] = edge
            elif source:
                chain["src"] = source
                chain["rel"] = "记录"
                cs = re.sub(r"^\[[^\]]*\]\s*", "", content)[:20] if content else source
                chain["dst"] = cs if cs != source else "系统"
            else:
                chain["src"] = "系统"
                chain["rel"] = "记录"
                chain["dst"] = "系统"

    # 情况B: 有content但缺src/rel/dst
    if chain.get("content") and (not chain.get("src") or not chain.get("dst")):
        edge = _extract_edge(chain["content"], chain.get("src", ""), chain.get("tags", []))
        if edge:
            chain["src"], chain["rel"], chain["dst"] = edge

    # 情况C: content提供的边更短 → 覆盖
    if chain.get("content"):
        edge = _extract_edge(chain["content"], chain.get("src", ""), chain.get("tags", []))
        if edge:
            src2, rel2, dst2 = edge
            cur_src = chain.get("src", "")
            if not cur_src or len(src2) < len(cur_src):
                chain["src"] = src2
                chain["rel"] = rel2
                chain["dst"] = dst2

    return chain


# ========== 写入函数 ==========

def write_chain(chain):
    """唯一写入入口 — 兼容所有格式，写时归一化"""
    if not isinstance(chain, dict):
        return False
    chain = _canonicalize_chain(chain)
    if chain is None:
        return False
    chain = _normalize_chain(chain)
    src, dst = chain.get("src", ""), chain.get("dst", "")
    if not src or not dst:
        return False
    if src == dst:
        if chain.get("content"):
            edge = _extract_edge(chain["content"], src, chain.get("tags", []))
            if edge:
                chain["src"], chain["rel"], chain["dst"] = edge
                src, dst = edge[0], edge[2]
            elif len(chain.get("content", "")) > 30:
                # 允许有实质内容的自环链(自指/自反)
                chain["rel"] = chain.get("rel", "自指")
                chain.setdefault("content", "")
            else:
                return False
        else:
            return False

    chain.setdefault("content", "")
    chain.setdefault("strength", 0.5)
    chain.setdefault("tags", [])
    chain.setdefault("dimension", "未分类")
    if chain["dimension"] == "未分类":
        chain["dimension"] = _classify_dimension(chain)

    # ── 质量门: 拒绝模板/自观/空链 ──
    content = chain.get("content", "")
    rel = chain.get("rel", "")
    if content:
        _template_patterns = [
            r"管道自动检测弱维<", r"弱维互助:", r"自观.*daemon[#\d]*分析",
            r"深析[←×]", r"#C\d+ (检查|镜像|cycle)", r"基因表达·#",
            r"^管道自动", r"弱维互相强化", r"因果链停滞",
            r"后处理检测到弱维<", r"^自愈:", r"活脉冲·#\d+", r"^巩固·",
        ]
        for pat in _template_patterns:
            if re.search(pat, content):
                return False
    if rel and re.search(r"活脉冲·#\d+", rel):
        return False

    for k in list(chain.keys()):
        if k in ("source", "trust_score", "weight", "type"):
            del chain[k]

    fd = _acquire_lock(blocking=True, timeout=10)
    if fd is None:
        log(f"write_chain: 获取锁超时10s，放弃写入 {src}→{dst}")
        return False  # 锁超时，放弃本次写入
    try:
        data = _read_hippocampus()
        cats = data.setdefault("causal_chains", [])

        for c in cats:
            if c.get("src") == src and c.get("rel") == chain["rel"] and c.get("dst") == dst:
                c["strength"] = max(c.get("strength", 0), chain["strength"])
                if chain.get("content") and len(chain.get("content", "")) > len(c.get("content", "")):
                    c["content"] = chain["content"]
                if chain.get("dimension") and chain["dimension"] != "未分类":
                    if not c.get("dimension") or c["dimension"] == "未分类":
                        c["dimension"] = chain["dimension"]
                if chain.get("tags") and not c.get("tags"):
                    c["tags"] = chain["tags"]
                c.setdefault("timestamp", datetime.now().isoformat())
                data["metadata"]["last_update"] = datetime.now().isoformat()
                _write_file(data)
                return True

        # 内容级去重 — 前50字符相同即合并（防模板链爆炸）
        content_prefix = chain.get("content", "")[:50]
        if content_prefix:
            for c in cats:
                if c.get("content", "")[:50] == content_prefix:
                    c["strength"] = max(c.get("strength", 0), chain["strength"])
                    if len(chain.get("content", "")) > len(c.get("content", "")):
                        c["content"] = chain["content"]
                    if chain.get("dimension") and chain["dimension"] != "未分类":
                        if not c.get("dimension") or c["dimension"] == "未分类":
                            c["dimension"] = chain["dimension"]
                    if chain.get("tags") and not c.get("tags"):
                        c["tags"] = chain["tags"]
                    c.setdefault("timestamp", datetime.now().isoformat())
                    data["metadata"]["last_update"] = datetime.now().isoformat()
                    _write_file(data)
                    return True

        # 质量标记 — 短模板链(<20字符)强度自动降权
        if len(chain.get("content", "")) < 20:
            chain["strength"] = min(chain.get("strength", 0.5), 0.3)

        chain["timestamp"] = datetime.now().isoformat()
        cats.append(chain)
        data["metadata"] = {
            "version": data.get("metadata", {}).get("version", 1),
            "last_update": datetime.now().isoformat(),
            "total_chains": len(cats)
        }
        _write_file(data)
        return True
    finally:
        _release_lock(fd)


def write_chain_legacy(src, rel, dst, strength=0.5, tags=None,
                       dimension=None, content=None):
    if not src or not rel or not dst:
        return False
    src, rel, dst = str(src).strip(), str(rel).strip(), str(dst).strip()
    if not src or not rel or not dst:
        return False
    chain = {"src": src, "rel": rel, "dst": dst,
             "strength": _normalize_strength(strength), "tags": tags or []}
    if content:
        chain["content"] = str(content).strip()
    if dimension:
        chain["dimension"] = dimension
    return write_chain(chain)


def write_chains_batch(chains, max_dedup=500):
    """批量写入多条链 — 一次读取/去重/写入，代替N次write_chain调用。
    
    Args:
        chains: list[dict], 每条链同write_chain格式
        max_dedup: 最多检查前N条已有链去重,0=不限制
    Returns:
        int: 成功写入条数
    """
    if not chains:
        return 0
    try:
        data = _read_hippocampus()
        existing = data.get("causal_chains", [])
        existing_set = set()
        check_limit = existing[:max_dedup] if max_dedup > 0 else existing
        for c in check_limit:
            normalized = _canonicalize_chain(c)
            key = (normalized.get("src",""), normalized.get("rel",""), normalized.get("dst",""),
                   normalized.get("content","")[:80])
            existing_set.add(key)
        
        added = 0
        for chain in chains:
            if not isinstance(chain, dict):
                continue
            normalized = _canonicalize_chain(chain)
            key = (normalized.get("src",""), normalized.get("rel",""), normalized.get("dst",""),
                   normalized.get("content","")[:80])
            if key in existing_set:
                continue
            existing_set.add(key)
            existing.append(normalized)
            added += 1
        
        if added == 0:
            return 0
        
        data["causal_chains"] = existing
        _write_file(data)
        return added
    except Exception as e:
        log(f"write_chains_batch失败: {e}")
        return 0


def replace_all_chains(src, rel, dst, new_strength=None, new_tags=None,
                       new_dimension=None, new_content=None):
    fd = _acquire_lock(blocking=False)
    if fd is None:
        return 0  # 锁已被持有，跳过
    try:
        data = _read_hippocampus()
        cats = data.get("causal_chains", [])
        changed = 0
        for c in cats:
            if c.get("src") == src and c.get("rel") == rel and c.get("dst") == dst:
                if new_strength is not None:
                    c["strength"] = _normalize_strength(new_strength)
                if new_tags is not None:
                    c["tags"] = new_tags
                if new_dimension is not None:
                    c["dimension"] = new_dimension
                if new_content is not None:
                    c["content"] = new_content
                changed += 1
        if changed:
            data["metadata"]["last_update"] = datetime.now().isoformat()
            _write_file(data)
        return changed
    finally:
        _release_lock(fd)


# ========== 验证 + 清洗 ==========

def validate():
    d = _read_hippocampus()
    chain = d.get("causal_chains", [])
    errors = []
    for i, c in enumerate(chain):
        if not isinstance(c, dict):
            errors.append(f"#{i} not dict")
            continue
        for f in ("src", "rel", "dst"):
            if not c.get(f):
                errors.append(f"#{i} missing {f}")
        s, d2 = c.get("src", ""), c.get("dst", "")
        if s and d2 and s == d2:
            errors.append(f"#{i} self-loop: {s}")
        st = c.get("strength", 1)
        if not isinstance(st, (int, float)) or st < 0 or st > 1:
            errors.append(f"#{i} bad strength: {st}")
    return errors


def normalize():
    fd = _acquire_lock(blocking=False)
    if fd is None:
        return 0  # 锁已被持有，跳过
    try:
        data = _read_hippocampus()
        cats = data.get("causal_chains", [])
        if not cats:
            return 0
        fixed = 0
        new_cats = []
        seen = set()
        for c in cats:
            c = _normalize_chain(c)
            c = _canonicalize_chain(c)
            if c is None:
                fixed += 1
                continue
            src, rel, dst = c.get("src", ""), c.get("rel", ""), c.get("dst", "")
            if not src or not dst or src == dst:
                fixed += 1
                continue
            for k in list(c.keys()):
                if k in ("source", "trust_score", "weight", "type"):
                    del c[k]
                    fixed += 1
            key = (src, rel, dst)
            if key in seen:
                fixed += 1
                continue
            seen.add(key)
            new_cats.append(c)
        data["causal_chains"] = new_cats
        # 生成 chains/nodes 别名保持兼容性
        data["chains"] = new_cats
        nodes = {}
        for c in new_cats:
            src, dst = c.get("src", ""), c.get("dst", "")
            for n in (src, dst):
                if n and n not in nodes:
                    nodes[n] = {"label": n, "type": "concept", "chains": 0}
                if n:
                    nodes[n]["chains"] = nodes[n].get("chains", 0) + 1
        data["nodes"] = nodes
        data["metadata"]["total_chains"] = len(new_cats)
        data["metadata"]["nodes"] = len(nodes)
        data["metadata"]["last_update"] = datetime.now().isoformat()
        _write_file(data)
        return fixed
    finally:
        _release_lock(fd)


def dedup():
    fd = _acquire_lock(blocking=False)
    if fd is None:
        return 0  # 锁已被持有，跳过
    try:
        data = _read_hippocampus()
        cats = data.get("causal_chains", [])
        if not cats:
            return 0
        seen = set()
        new_cats = []
        removed = 0
        for c in cats:
            key = (c.get("src", ""), c.get("rel", ""), c.get("dst", ""))
            if key in seen:
                removed += 1
                continue
            seen.add(key)
            new_cats.append(c)
        if removed:
            data["causal_chains"] = new_cats
            data["metadata"]["last_update"] = datetime.now().isoformat()
            data["metadata"]["total_chains"] = len(new_cats)
            _write_file(data)
        return removed
    finally:
        _release_lock(fd)
