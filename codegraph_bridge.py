#!/usr/bin/env python3
"""
codegraph_bridge.py — 代码知识图谱(集群版)
===========================================
用ast模块解析cluster目录所有.py文件，
建立函数/类/导入关系索引，支持语义搜索。

用法:
  python3 codegraph_bridge.py index     # 建立索引
  python3 codegraph_bridge.py search "关键词"  # 搜索
"""
import ast, json, os, sys
from pathlib import Path
from collections import defaultdict

CLUSTER = Path(__file__).resolve().parent
INDEX_FILE = CLUSTER / "codegraph_index.json"

def parse_file(filepath):
    """用ast解析单个.py文件"""
    result = {"functions": [], "classes": [], "imports": [], "calls": []}
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(filepath))
    except Exception:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            result["functions"].append({
                "name": node.name,
                "line": node.lineno,
                "args": [a.arg for a in node.args.args],
            })
        elif isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            result["classes"].append({
                "name": node.name,
                "line": node.lineno,
                "methods": methods,
            })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result["imports"].append(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                result["calls"].append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                result["calls"].append(node.func.attr)

    return result

def build_index():
    """扫描cluster目录建立索引"""
    index = {"version": "v1", "files": {}, "graph": {"imports": defaultdict(list), "calls": defaultdict(list)}}
    py_files = [f for f in CLUSTER.glob("*.py") if f.is_file()]

    for filepath in sorted(py_files):
        result = parse_file(filepath)
        fname = filepath.name
        index["files"][fname] = result

        for imp in result["imports"]:
            index["graph"]["imports"][imp].append(fname)
        for call in result["calls"]:
            index["graph"]["calls"][call].append(fname)

    index["graph"]["imports"] = dict(index["graph"]["imports"])
    index["graph"]["calls"] = dict(index["graph"]["calls"])

    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    total_funcs = sum(len(v["functions"]) for v in index["files"].values())
    total_classes = sum(len(v["classes"]) for v in index["files"].values())
    print(f"索引完成: {len(py_files)}文件 | {total_funcs}函数 | {total_classes}类")

def search(query):
    """语义搜索"""
    if not INDEX_FILE.exists():
        print("索引不存在,先运行: python3 codegraph_bridge.py index")
        return

    index = json.load(open(INDEX_FILE))
    results = []

    for fname, data in index["files"].items():
        for func in data["functions"]:
            if query.lower() in func["name"].lower():
                results.append(f"  {fname}:{func['line']} def {func['name']}({','.join(func['args'])})")
        for cls in data["classes"]:
            if query.lower() in cls["name"].lower():
                results.append(f"  {fname}:{cls['line']} class {cls['name']}({','.join(cls['methods'][:3])})")
        for imp in data["imports"]:
            if query.lower() in imp.lower():
                results.append(f"  {fname}: import {imp}")

    if results:
        print(f"搜索'{query}' ({len(results)}结果):")
        for r in results[:20]:
            print(r)
    else:
        print(f"搜索'{query}': 无结果")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "index"
    if cmd == "index":
        build_index()
    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else "error"
        search(query)
    else:
        print("用法: codegraph_bridge.py [index|search 关键词]")
