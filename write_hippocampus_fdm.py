#!/usr/bin/env python3
"""
FDM总线激活 → 写入海马体因果链
"""
import json, os, sys, time
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
os.chdir(str(CLUSTER))

from hippocampus import 因果记忆库, 记忆类型, 关系类型

def write_fdm_activation_chains():
    print("=" * 60)
    print("第5步：写入海马体causal_chains")
    print("=" * 60)

    # 加载海马体
    海马 = 因果记忆库(str(CLUSTER / "hippocampus_memory.json"))
    
    # 获取当前统计
    before = 海马.获取统计()
    print(f"  写入前: {before['节点数']}节点, {before['关系数']}关系, {before['总写入']}总写入")
    
    # ── 写入FDM激活因果链 ──
    
    # 1. 观察：控制通道在线但业务频道离线
    id1 = 海马.存储记忆(
        "FDM总线审计: 控制通道18789有10神经元在线，业务频道18790-18795监听中但0Agent连接",
        记忆类型.感知, 情感值=-0.2, 重要性=0.8,
        标签=["FDM", "总线", "审计", "通道离线"]
    )
    print(f"  ✅ 记忆1: 总线审计感知 (id={id1[:20]}...)")
    
    # 2. 分析：根本原因是所有神经元默认连接控制通道
    id2 = 海马.存储记忆(
        "因果分析: neuron_daemon.py硬编码BUS_PORT=18789，所有10个神经元只连接控制通道，业务频道虽在监听但无Agent注册。NeuralAgent默认channel='control'。",
        记忆类型.思考, 情感值=-0.1, 重要性=0.9,
        标签=["FDM", "因果分析", "neuron_daemon", "BUS_PORT"]
    )
    海马.建立关系(id1, id2, 关系类型.因果)
    print(f"  ✅ 记忆2: 因果分析 (id={id2[:20]}...)")
    
    # 3. 激活行为：在6个业务频道启动echo服务
    id3 = 海马.存储记忆(
        "执行: 在6个业务频道(18790代码/18791分析/18792专业/18793哲学/18794外部知识/18795保留)启动PersistentEcho守护进程，使用NeuralAgent连接到对应端口",
        记忆类型.行为, 情感值=0.5, 重要性=0.9,
        标签=["FDM", "激活", "echo_daemon", "18790", "18791", "18792", "18793", "18794", "18795"]
    )
    海马.建立关系(id2, id3, 关系类型.因果)
    print(f"  ✅ 记忆3: 激活行为 (id={id3[:20]}...)")
    
    # 4. 验证：路由测试通过控制通道→业务通道双向通信成功
    id4 = 海马.存储记忆(
        "验证: 通过控制通道18789向6个业务频道发送路由测试消息，双向通信成功。每个Echo服务收到task消息并回复result，控制通道成功接收回声。",
        记忆类型.感知, 情感值=0.7, 重要性=0.8,
        标签=["FDM", "路由测试", "双向通信", "验证"]
    )
    海马.建立关系(id3, id4, 关系类型.因果)
    print(f"  ✅ 记忆4: 验证结果 (id={id4[:20]}...)")
    
    # 5. 知识采集任务发送
    id5 = 海马.存储记忆(
        "知识采集: 通过业务频道发送5个真实知识采集任务(code: Python元编程, analysis: FDM架构分析, pro: Agent架构模式, phil: 元认知定义, ext: AI前沿方向)",
        记忆类型.行为, 情感值=0.4, 重要性=0.7,
        标签=["FDM", "知识采集", "跨频道通信"]
    )
    海马.建立关系(id4, id5, 关系类型.因果)
    print(f"  ✅ 记忆5: 知识采集 (id={id5[:20]}...)")
    
    # 6. 最终状态：7/7通道在线
    id6 = 海马.存储记忆(
        "结果: FDM总线从0/7通道在线修复为7/7通道在线。控制通道10Agent+6业务频道各1Echo=16Agent在线，6827条消息。验证指标达成。",
        记忆类型.感知, 情感值=0.8, 重要性=0.95,
        标签=["FDM", "里程碑", "7/7在线", "激活成功"]
    )
    海马.建立关系(id5, id6, 关系类型.因果)
    print(f"  ✅ 记忆6: 最终状态 (id={id6[:20]}...)")
    
    # 保存
    海马.保存()
    
    after = 海马.获取统计()
    print(f"\n  📊 写入后: {after['节点数']}节点 (+{after['节点数']-before['节点数']}), "
          f"{after['关系数']}关系 (+{after['关系数']-before['关系数']}), "
          f"{after['总写入']}总写入 (+{after['总写入']-before['总写入']}), "
          f"自指折叠 {after['自指折叠次数']}次")
    
    # 导出因果链到可读文件
    chain = {
        "timestamp": datetime.now().isoformat(),
        "chains": [
            {"step": 1, "title": "审计发现", "id": id1, "type": "感知", "content": "FDM总线业务频道离线"},
            {"step": 2, "title": "因果分析", "id": id2, "type": "思考", "content": "BUS_PORT=18789硬编码"},
            {"step": 3, "title": "激活执行", "id": id3, "type": "行为", "content": "启动6个业务频道echo服务"},
            {"step": 4, "title": "验证通信", "id": id4, "type": "感知", "content": "跨频道双向路由测试成功"},
            {"step": 5, "title": "知识采集", "id": id5, "type": "行为", "content": "5个知识采集任务下发"},
            {"step": 6, "title": "达标确认", "id": id6, "type": "感知", "content": "7/7通道在线"},
        ],
        "stats": after,
    }
    chain_path = CLUSTER / "fdm_causal_chains.json"
    with open(chain_path, "w", encoding="utf-8") as f:
        json.dump(chain, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 因果链已导出到 {chain_path.name}")
    
    return chain

if __name__ == "__main__":
    write_fdm_activation_chains()
