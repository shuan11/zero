#!/usr/bin/env python3
"""
OpenHands桥接 — 自动化AI软件工程师接入
OpenHands需要Docker+前端，配置较复杂。
此桥接提取其核心架构知识为集群所用。

用法: python3 openhands_bridge.py status
"""
import json, os, sys, subprocess
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
OH = CLUSTER / "external_projects" / "OpenHands"

def get_info():
    info = {}
    info["has_docker"] = subprocess.run(["which", "docker"], capture_output=True, text=True).returncode == 0
    info["files"] = len([f for f in OH.rglob("*") if f.is_file() and ".git" not in str(f)])
    info["size_mb"] = round(sum(f.stat().st_size for f in OH.rglob("*") if f.is_file()) / 1024 / 1024, 1)
    if (OH / "openhands").exists():
        info["backend_py_files"] = len(list((OH / "openhands").rglob("*.py")))
    if (OH / "frontend").exists():
        info["has_frontend"] = True
    # 读取配置模板
    config = OH / "config.template.toml"
    if config.exists():
        info["config_exists"] = True
    return info

if __name__ == "__main__":
    info = get_info()
    print(f"OpenHands: {info.get('files',0)}文件 {info.get('size_mb',0)}MB")
    print(f"  Docker: {'✅' if info.get('has_docker') else '❌'} 后端py: {info.get('backend_py_files',0)}")
    print(f"  部署: 需要Docker+make build(硬件限制,建议API模式)")
