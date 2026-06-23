#!/usr/bin/env python3
"""
evolution_orchestrator.py — 因果驱动自进化引擎
============================================
扫描海马体 → 因果分析 → 检测异常 → 修复 → 写回海马体

铁律：不等指令，一次循环完成全部步骤。
"""
import json, sys, time, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
HIP_FILE = CLUSTER / "hippocampus_memory.json"
from parameter_predictor import ParameterPredictor
from causal_predictor import CausalPredictor

BJT = timezone(timedelta(hours=8))

def ts():
    return datetime.now(BJT).strftime('%H:%M:%S')

def load_hip():
    with open(HIP_FILE) as f:
        return json.load(f)

def save_hip(hip):
    with open(HIP_FILE, 'w') as f:
        json.dump(hip, f, ensure_ascii=False, indent=2)

def scan_new(chains, n=20):
    """扫描最近n条链"""
    return chains[-n:] if len(chains) >= n else chains

def detect_anomalies(chains):
    """检测因果链异常"""
    anomalies = []
    # 1. 有effect无cause
    no_cause = [c for c in chains if c.get('effect') and not c.get('cause') and '因果' not in str(c.get('tags', []))]
    # 2. 有cause无effect
    no_effect = [c for c in chains if c.get('cause') and not c.get('effect') and '因果' not in str(c.get('tags', []))]
    # 3. 孤立链（无标签）
    orphan = [c for c in chains if not c.get('tags') or len(c.get('tags', [])) == 0]
    # 4. 空内容
    empty = [c for c in chains if not c.get('content') or len(c.get('content', '').strip()) < 10]
    # 5. 重复链
    seen = set()
    dupes = []
    for c in chains:
        content = c.get('content', '')[:80]
        if content in seen:
            dupes.append(c)
        seen.add(content)
    
    return {
        'no_cause': len(no_cause),
        'no_effect': len(no_effect),
        'orphan': len(orphan),
        'empty': len(empty),
        'dupes': len(dupes),
        'total_anomalies': len(no_cause) + len(no_effect) + len(orphan) + len(empty) + len(dupes),
    }

def repair(hip, anomalies):
    """修复异常"""
    chains = hip.get('causal_chains', [])
    repaired = 0
    
    # 删除空内容链
    if anomalies['empty'] > 0:
        hip['causal_chains'] = [c for c in chains if c.get('content') and len(c.get('content', '').strip()) >= 10]
        repaired += anomalies['empty']
    
    # 给无标签链加标签
    for c in hip['causal_chains']:
        if not c.get('tags') or len(c.get('tags', [])) == 0:
            c['tags'] = ['auto_tagged', 'evolution_orchestrator']
            repaired += 1
    
    return repaired

def run_cycle():
    """执行一次完整自进化循环"""
    print(f"[{ts()}] ═══ 因果驱动自进化循环 ═══")
    
    # Step 1: 加载海马体
    hip = load_hip()
    chains = hip.get('causal_chains', [])
    print(f"  海马体: {len(chains)}链")
    
    # Step 2: 扫描最近链
    recent = scan_new(chains, 20)
    print(f"  扫描最近{len(recent)}条链")
    
    # Step 3: 检测异常
    anomalies = detect_anomalies(chains)
    print(f"  异常检测: {anomalies['total_anomalies']}个")
    print(f"    无因:{anomalies['no_cause']} 无果:{anomalies['no_effect']} 孤立:{anomalies['orphan']} 空:{anomalies['empty']} 重复:{anomalies['dupes']}")
    
    # Step 3.5: 预测异常发展趋势
    predictions = {}
    try:
        predictor = CausalPredictor()
        predictor.load()
        # 对主要异常类型进行预测
        if anomalies['empty'] > 0:
            predictions['empty'] = predictor.predict_anomaly('空内容', 3)
        if anomalies['dupes'] > 0:
            predictions['dupes'] = predictor.predict_anomaly('重复', 3)
        print(f"  预测分析: {len(predictions)}个异常趋势")
    except Exception as e:
        print(f"  预测失败: {e}")
    
    # Step 3.6: 预测最优参数
    param_predictions = {}
    try:
        param_predictor = ParameterPredictor()
        param_predictions = param_predictor.predict_optimal_parameters()
        print(f"  参数预测: 熵衰减{param_predictions['entropy_threshold_days']}天 可信度{param_predictions['trust_threshold']}")
    except Exception as e:
        print(f"  参数预测失败: {e}")
    
    # Step 4: 修复
    repaired = repair(hip, anomalies)
    print(f"  修复: {repaired}个")
    
    # Step 4.5: 应用预测参数
    if param_predictions:
        try:
            param_predictor = ParameterPredictor()
            applied_params = param_predictor.apply_predicted_parameters()
            print(f"  参数应用: 熵衰减{applied_params['entropy_threshold_days']}天 可信度{applied_params['trust_threshold']}")
            
            # 写入参数应用记录
            hip['causal_chains'].append({
                'content': f"[参数调优] 熵衰减阈值:{applied_params['entropy_threshold_days']}天 可信度阈值:{applied_params['trust_threshold']}",
                'source': 'parameter_predictor',
                'tags': ['参数调优', '自优化', '预测应用'],
                'timestamp': datetime.now(BJT).isoformat(),
            })
        except Exception as e:
            print(f"  参数应用失败: {e}")
    
    # Step 5: 写入进化记录和预测结果
    hip['causal_chains'].append({
        'content': f"[自进化循环] {ts()} 检测{anomalies['total_anomalies']}个异常 修复{repaired}个 链:{len(hip['causal_chains'])}",
        'source': 'evolution_orchestrator',
        'tags': ['自进化', 'evolution', 'anomaly_detection', 'auto_repair'],
        'timestamp': datetime.now(BJT).isoformat(),
    })
    
    # 写入预测结果
    for anomaly_type, pred in predictions.items():
        if pred.get('anomalies'):
            top_pred = pred['anomalies'][0]
            hip['causal_chains'].append({
                'content': f"[异常预测] {anomaly_type} → {top_pred['entity']} (概率:{top_pred['probability']})",
                'source': 'evolution_orchestrator',
                'tags': ['异常预测', '趋势分析', anomaly_type],
                'timestamp': datetime.now(BJT).isoformat(),
            })
    
    # Step 6: 保存
    save_hip(hip)
    new_chains = len(hip['causal_chains'])
    ext = len([c for c in hip['causal_chains'] if '外部世界' in c.get('tags', [])])
    print(f"  海马体更新: {new_chains}链 外部:{ext}({ext/new_chains*100:.0f}%)")
    
    # Step 7: 报告
    report = {
        'timestamp': datetime.now(BJT).isoformat(),
        'chains_before': len(chains),
        'chains_after': new_chains,
        'anomalies': anomalies,
        'repaired': repaired,
        'external_pct': round(ext/new_chains*100, 1),
    }
    
    report_file = CLUSTER / "evolution_output" / "evolution_cycle_report.json"
    report_file.parent.mkdir(exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  报告: {report_file.name}")
    print(f"[{ts()}] ═══ 循环完成 ═══")
    
    return report

if __name__ == '__main__':
    if '--loop' in sys.argv:
        print(f"[{ts()}] 自进化引擎启动 (每3600秒)")
        while True:
            try:
                run_cycle()
            except Exception as e:
                print(f"[{ts()}] 异常: {e}")
            time.sleep(3600)
    else:
        run_cycle()
