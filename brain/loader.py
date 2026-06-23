"""brain/loader.py — 工程产出加载器
每周期加载gen_*.py中的导出函数并调用，使工程产出真正参与系统运行
"""
import json, os, sys, time, importlib, traceback
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

_loaded_cache = {}  # {filename: (module, mtime), ...}
_last_scan = 0
_SCAN_INTERVAL = 60  # 每60秒重扫
_MAX_ENGINE_FILES = 60  # 最多加载最近N个工程文件，防膨胀（原20 → 60，确保自我通知等核心模块加载）

def load_engineering_outputs(log_func=print):
    """扫描并加载brain/下所有gen_*.py文件
    返回: [(name, success, result_or_error), ...]
    """
    global _last_scan
    results = []
    now = time.time()
    
    gen_dir = Path(__file__).parent
    all_files = list(gen_dir.glob("gen_*.py"))
    # 按修改时间排序（最新的在前），只取最近_MAX_ENGINE_FILES个
    all_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    gen_files = all_files[:_MAX_ENGINE_FILES]
    skipped = len(all_files) - len(gen_files)
    
    # 去重：同一维度只保留最新的一个（gen_{dimension}_{date}.py）
    # 从文件名提取维度名，如 gen_洞察循环_20260614.py → 洞察循环
    seen_dims = set()
    deduped = []
    for fpath in gen_files:
        stem = fpath.stem  # "gen_洞察循环_20260614"
        # 去掉 gen_ 前缀，去掉最后 _date 部分
        parts = stem.split('_')
        if len(parts) >= 3:
            dim = '_'.join(parts[1:-1])  # 维度名可能在中间有下划线
        else:
            dim = stem  # 兜底
        if dim not in seen_dims:
            seen_dims.add(dim)
            deduped.append(fpath)
        else:
            skipped += 1
    
    gen_files = deduped
    
    if not gen_files:
        return [("no_gen_files", False, "无工程产出")]
    if skipped > 0:
        results.append(("skipped_old", True, f"跳过{skipped}个旧工程文件"))
    
    for fpath in gen_files:
        name = fpath.stem
        
        # 跳过太新的文件（防止刚写入就加载）
        try:
            mtime = fpath.stat().st_mtime
            if now - mtime < 2:
                continue
        except OSError:
            continue
        
        # 尝试导入模块
        if name in _loaded_cache:
            mod, cached_mtime = _loaded_cache[name]
            # 如果文件更新了，重载模块（从头创建而非reload——因为module_from_spec不注册sys.modules）
            try:
                current_mtime = fpath.stat().st_mtime
                if current_mtime > cached_mtime:
                    # 移除旧缓存再重新导入
                    if name in sys.modules:
                        del sys.modules[name]
                    spec = importlib.util.spec_from_file_location(name, fpath)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        sys.modules[name] = mod
                        _loaded_cache[name] = (mod, current_mtime)
            except OSError:
                pass  # 无法检查mtime时继续使用缓存
        else:
            try:
                spec = importlib.util.spec_from_file_location(name, fpath)
                if spec is None or spec.loader is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                sys.modules[name] = mod  # 注册到sys.modules，支持后续reload/重查
                _loaded_cache[name] = (mod, fpath.stat().st_mtime)
            except SystemExit:
                # gen文件调用exit()会导致daemon意外退出——捕获并记作失败
                results.append((name, False, "exit()被调用——gen文件不应直接exit"))
                continue
            except Exception as e:
                results.append((name, False, f"导入失败: {str(e)[:60]}"))
                continue
        
        # 查找可调用的顶层函数（排除私有和标准函数）
        callables = []
        for attr_name in dir(mod):
            if attr_name.startswith("_") or attr_name in ("CLUSTER", "Path", "sys"):
                continue
            attr = getattr(mod, attr_name)
            if callable(attr) and attr.__module__ == name:
                callables.append(attr_name)
        
        if not callables:
            callables = [a for a in dir(mod) 
                        if not a.startswith("_") and callable(getattr(mod, a))]
        
        # 调用每个可调用函数（排除导入函数——只在模块自身定义的）
        # 跳过已知的阻塞函数（API燃烧器/长循环/守护进程）
        _blocklist = {"burn", "make_call", "start_burn", "_burn", "run_forever", "main_loop"}
        for func_name in callables[:2]:  # 最多调2个
            if func_name in _blocklist:
                continue
            func = getattr(mod, func_name)
            # 跳过导入的函数（__module__不是当前模块名）
            if getattr(func, '__module__', '') != name:
                continue
            try:
                ret = func()
                if isinstance(ret, bool):
                    results.append((f"{name}.{func_name}", ret, ""))
                else:
                    results.append((f"{name}.{func_name}", True, str(ret)[:40]))
                    # 自动注入动作关键字：弱维时添加路由
                    _ret_str = str(ret)
                    if "[弱]" in _ret_str:
                        try:
                            _dim_name = name.replace("gen_", "").rsplit("_", 1)[0]
                            from brain.share import add_action_keyword as _aak
                            _aak(_dim_name)
                        except Exception:
                            pass
            except Exception as e:
                results.append((f"{name}.{func_name}", False, str(e)[:60]))
    
    # 协调器：目标对齐+冲突检测（在gen文件注册完、执行前）
    try:
        from brain.coordinator import coordinate
        coord_result = coordinate(log=log_func)
        if coord_result.get("suppressed", 0) > 0:
            log_func(f"  协调器: 抑制{coord_result['suppressed']}个冲突动作 "
                     f"(目标:{coord_result.get('goal_type','?')}, "
                     f"聚焦:{coord_result.get('focus_dim','?')})")
        if coord_result.get("conflicts"):
            log_func(f"  协调器: {len(coord_result['conflicts'])}个冲突对")
    except Exception as ce:
        log_func(f"  协调器异常: {ce}")
    
    # 后处理合成：将gen文件的检测结果自动翻译为动作
    # 这样所有77个gen文件无需修改也能参与动作管道
    try:
        # 兼容两种路径：gen模块写root/，但loader在brain/启动时路径可能不同
        # 优先读root（gen模块实际写入位置），其次brain/（历史兼容）
        _gf_paths = [
            CLUSTER / ".brain_gen_feedback.json",   # gen模块写入位置
            gen_dir / ".brain_gen_feedback.json",    # 历史读取位置
        ]
        _gf_data = {"reports": []}
        for _gf_path in _gf_paths:
            if _gf_path.exists():
                try:
                    _d = json.loads(_gf_path.read_text(encoding="utf-8"))
                    if isinstance(_d, dict) and "reports" in _d:
                        _gf_data["reports"] = _d["reports"]
                        break
                except (json.JSONDecodeError, OSError):
                    continue
        _reports = _gf_data.get("reports", [])[-80:]
        # 计算相对弱维：链数低于所有维度均值(或低于最强维60%)
        _dim_counts = {}
        for r in _reports:
            d = r.get("dimension","")
            if d and d not in ("系统","未分类"):
                _dim_counts[d] = max(_dim_counts.get(d, 0), r.get("chain_count", 0))
        if _dim_counts:
            _max_dim = max(_dim_counts.values())
            _weak_dims = [(d, c) for d, c in _dim_counts.items() 
                         if c < _max_dim * 0.65]
            _weak_dims.sort(key=lambda x: x[1])
            _prev_weak = set()
            try:
                import json as _json2
                _pwf = gen_dir / ".brain_prev_weak.json"
                if _pwf.exists():
                    _prev_weak = set(_json2.loads(_pwf.read_text()))
            except:
                pass
            if _weak_dims:
                log_func(f"  后处理: {len(_weak_dims)}个相对弱维(最强={_max_dim})")
                from brain.action_registry import register_action as _ra
                for dim, cnt in _weak_dims[:5]:  # 前5弱（原3，加强覆盖）
                    _focus_key = f"focus.{dim}"
                    _ra("update_genome", {"changes": {_focus_key: 1.0},
                        "dimension": dim,
                        "reason": f"{dim}相对偏弱({cnt}/{_max_dim})——强制聚焦"},
                        priority=5, source=f"auto:{dim}_weak")
                    _ra("write_chain", {"src": f"弱维纠正·{dim}",
                        "rel": "品质聚焦", "dst": dim,
                        "content": f"{dim}维度(cnt={cnt})引入最强维度({_max_dim}链)的品质模式替代模板填充。在{dim}现有链中提取与{_max_dim}维共同的结构特征，建立维度间的映射而不失{dim}的独特性",
                        "dimension": dim, "strength": 0.75},
                        priority=7, source=f"auto:{dim}_chain")
                    # 自动生成v3模板gen文件（若无最新版本）
                    try:
                        _gen_dir = Path(__file__).parent
                        _existing = list(_gen_dir.glob(f"gen_{dim}_*.py"))
                        _need_gen = True
                        if _existing:
                            _newest = max(_existing, key=lambda p: p.stat().st_mtime)
                            if _newest.stat().st_mtime > time.time() - 600:
                                if 'gene_expression_v3' in _newest.read_text()[:200]:
                                    _need_gen = False
                        if _need_gen:
                            from brain.gene_expression import GEN_TEMPLATE
                            _ts = time.strftime('%Y%m%d_%H%M%S', time.localtime())
                            _gen_content = GEN_TEMPLATE.format(
                                dim_name=dim, gen=int(time.time()*1000),
                                insight=f"管道自动检测弱维<{dim}>并生成v3工程"
                            )
                            _target = _gen_dir / f"gen_{dim}_{_ts.split('_')[0]}.py"
                            _target.write_text(_gen_content, encoding="utf-8")
                            log_func(f"  🧬 管道自繁殖: gen_{dim}_{_ts.split('_')[0]}.py (v3)")
                            _ra("write_chain", {"src": "管道自繁殖",
                                "rel": "生成v3", "dst": dim,
                                "content": f"后处理检测到弱维<{dim}>，自动生成v3工程文件",
                                "dimension": dim, "strength": 0.6},
                                priority=5, source=f"auto:{dim}_v3")
                    except Exception as e:
                        log_func(f"  自繁殖异常: {e}")
        else:
            log_func(f"  无反馈数据，跳过弱维检测")
    except Exception as e:
        log_func(f"  后处理异常: {e}")

    # 执行gen文件注册的动作(动作注册表)
    try:
        from brain.action_registry import execute_actions
        action_results = execute_actions(max_actions=20)
        if action_results:
            ok_count = sum(1 for _, s, _ in action_results if s)
            results.append(("action_registry", True, f"执行{len(action_results)}个动作({ok_count}成功)"))
            for aid, aok, amsg in action_results:
                results.append((f"act:{aid}", aok, str(amsg)[:40]))
    except Exception as ae:
        results.append(("action_registry", False, str(ae)[:60]))
    
    # 动作验证反馈(执行后检查效果)
    try:
        from brain.action_verifier import verify_recent_actions
        vresult = verify_recent_actions(max_check=5, log=log_func)
        if vresult["verified_fail"] > 0:
            results.append(("action_verifier", False, 
                           f"{vresult['verified_fail']}/{vresult['total_verified']}个动作验证失败"))
            for aid, atype, reason in vresult["failures"]:
                results.append((f"verifier:{atype}:{aid[:16]}", False, reason[:40]))
        else:
            results.append(("action_verifier", True, 
                           f"{vresult['total_verified']}个动作已验证通过"))
    except Exception as ve:
        log_func(f"  验证器异常: {ve}")
        results.append(("action_verifier", False, str(ve)[:60]))
    
    return results


def register_loaded(name, mod):
    """手动注册已加载模块到缓存"""
    _loaded_cache[name] = (mod, time.time())


def clear_cache():
    """清空缓存，强制下次全量重扫"""
    _loaded_cache.clear()
