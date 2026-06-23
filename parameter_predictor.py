#!/usr/bin/env python3
"""
parameter_predictor.py — 规则参数预测引擎
========================================
基于系统状态预测最优的规则参数，实现系统自我优化。

目标参数：
1. ENTROPY_THRESHOLD_DAYS: 熵衰减阈值（天）
2. TRUST_THRESHOLD: 可信度阈值

预测依据：
- 当前链数和外部知识比例
- 历史异常数量
- 系统进化阶段
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

HIP_FILE = CLUSTER / "hippocampus_memory.json"
BJT = timezone(timedelta(hours=8))

class ParameterPredictor:
    def __init__(self):
        self.current_state = {}
        
    def load_system_state(self):
        """加载当前系统状态"""
        try:
            hip = json.load(open(HIP_FILE))
            chains = hip.get("causal_chains", [])
            
            # 计算关键指标
            total_chains = len(chains)
            external_chains = len([c for c in chains if '外部世界' in c.get('tags', [])])
            external_ratio = external_chains / total_chains if total_chains > 0 else 0
            
            # 计算熵增链比例
            entropy_chains = len([c for c in chains if '熵增' in c.get('tags', [])])
            entropy_ratio = entropy_chains / total_chains if total_chains > 0 else 0
            
            # 计算低可信度链比例
            low_trust_chains = len([c for c in chains if '低可信度' in c.get('tags', [])])
            low_trust_ratio = low_trust_chains / total_chains if total_chains > 0 else 0
            
            # 计算平均链年龄（天）
            now = datetime.now(BJT)
            ages = []
            for c in chains:
                ts = c.get('timestamp', '')
                if ts:
                    try:
                        # 简化处理：假设时间戳格式一致
                        chain_time = datetime.fromisoformat(ts.replace('+08:00', ''))
                        age_days = (now.replace(tzinfo=None) - chain_time.replace(tzinfo=None)).days
                        ages.append(age_days)
                    except:
                        pass
            
            avg_age = sum(ages) / len(ages) if ages else 0
            
            self.current_state = {
                "total_chains": total_chains,
                "external_chains": external_chains,
                "external_ratio": round(external_ratio, 3),
                "entropy_chains": entropy_chains,
                "entropy_ratio": round(entropy_ratio, 3),
                "low_trust_chains": low_trust_chains,
                "low_trust_ratio": round(low_trust_ratio, 3),
                "avg_chain_age_days": round(avg_age, 2),
                "timestamp": now.isoformat()
            }
            
            return self.current_state
            
        except Exception as e:
            print(f"加载系统状态失败: {e}")
            return {}
    
    def predict_entropy_threshold(self):
        """预测最优的熵衰减阈值"""
        if not self.current_state:
            return 0.5  # 默认值
        
        # 基于规则：
        # 1. 如果外部知识比例高（>90%），可以收紧阈值（更短时间就标记熵增）
        # 2. 如果链平均年龄大，需要更宽松的阈值
        # 3. 如果熵增链比例过高（>30%），需要更宽松的阈值
        
        base_threshold = 0.5  # 基准阈值
        
        # 调整因子1：外部知识比例
        external_ratio = self.current_state.get("external_ratio", 0.5)
        if external_ratio > 0.9:
            # 外部知识比例高，可以更激进地标记熵增
            adjustment1 = -0.1
        elif external_ratio < 0.7:
            # 外部知识比例低，需要更保守
            adjustment1 = 0.2
        else:
            adjustment1 = 0.0
        
        # 调整因子2：平均链年龄
        avg_age = self.current_state.get("avg_chain_age_days", 1)
        if avg_age > 7:
            # 链平均年龄大，需要更宽松的阈值
            adjustment2 = 0.3
        elif avg_age < 2:
            # 链很新，可以更严格
            adjustment2 = -0.1
        else:
            adjustment2 = 0.0
        
        # 调整因子3：熵增链比例
        entropy_ratio = self.current_state.get("entropy_ratio", 0.1)
        if entropy_ratio > 0.3:
            # 熵增链太多，需要更宽松
            adjustment3 = 0.2
        elif entropy_ratio < 0.1:
            # 熵增链很少，可以更严格
            adjustment3 = -0.1
        else:
            adjustment3 = 0.0
        
        predicted_threshold = base_threshold + adjustment1 + adjustment2 + adjustment3
        
        # 限制在合理范围内
        predicted_threshold = max(0.1, min(2.0, predicted_threshold))
        
        return round(predicted_threshold, 2)
    
    def predict_trust_threshold(self):
        """预测最优的可信度阈值"""
        if not self.current_state:
            return 0.6  # 默认值
        
        # 基于规则：
        # 1. 如果外部知识比例高，可以提高阈值（更严格）
        # 2. 如果低可信度链比例高，需要降低阈值（更宽松）
        # 3. 如果链平均年龄大，需要更宽松的阈值
        
        base_threshold = 0.6  # 基准阈值
        
        # 调整因子1：外部知识比例
        external_ratio = self.current_state.get("external_ratio", 0.5)
        if external_ratio > 0.9:
            # 外部知识质量高，可以更严格
            adjustment1 = 0.05
        elif external_ratio < 0.7:
            # 外部知识质量可能不高，需要更宽松
            adjustment1 = -0.1
        else:
            adjustment1 = 0.0
        
        # 调整因子2：低可信度链比例
        low_trust_ratio = self.current_state.get("low_trust_ratio", 0.1)
        if low_trust_ratio > 0.3:
            # 低可信度链太多，需要更宽松
            adjustment2 = -0.1
        elif low_trust_ratio < 0.1:
            # 低可信度链很少，可以更严格
            adjustment2 = 0.05
        else:
            adjustment2 = 0.0
        
        # 调整因子3：平均链年龄
        avg_age = self.current_state.get("avg_chain_age_days", 1)
        if avg_age > 7:
            # 链平均年龄大，需要更宽松
            adjustment3 = -0.05
        elif avg_age < 2:
            # 链很新，可以更严格
            adjustment3 = 0.02
        else:
            adjustment3 = 0.0
        
        predicted_threshold = base_threshold + adjustment1 + adjustment2 + adjustment3
        
        # 限制在合理范围内
        predicted_threshold = max(0.3, min(0.9, predicted_threshold))
        
        return round(predicted_threshold, 2)
    
    def predict_optimal_parameters(self):
        """预测所有最优参数"""
        self.load_system_state()
        
        entropy_threshold = self.predict_entropy_threshold()
        trust_threshold = self.predict_trust_threshold()
        
        return {
            "entropy_threshold_days": entropy_threshold,
            "trust_threshold": trust_threshold,
            "system_state": self.current_state,
            "prediction_timestamp": datetime.now(BJT).isoformat()
        }
    
    def apply_predicted_parameters(self):
        """应用预测的参数到规则文件"""
        params = self.predict_optimal_parameters()
        
        # 更新rule_entropy_decay.py
        entropy_file = CLUSTER / "rules" / "rule_entropy_decay.py"
        if entropy_file.exists():
            content = entropy_file.read_text()
            # 替换阈值
            new_content = content.replace(
                "ENTROPY_THRESHOLD_DAYS = 0.5",
                f"ENTROPY_THRESHOLD_DAYS = {params['entropy_threshold_days']}"
            )
            entropy_file.write_text(new_content)
        
        # 更新rule_trust_score.py
        trust_file = CLUSTER / "rules" / "rule_trust_score.py"
        if trust_file.exists():
            content = trust_file.read_text()
            # 替换阈值
            new_content = content.replace(
                "TRUST_THRESHOLD = 0.60",
                f"TRUST_THRESHOLD = {params['trust_threshold']}"
            )
            trust_file.write_text(new_content)
        
        return params

if __name__ == "__main__":
    predictor = ParameterPredictor()
    
    if "--predict" in sys.argv:
        params = predictor.predict_optimal_parameters()
        print(json.dumps(params, ensure_ascii=False, indent=2))
    elif "--apply" in sys.argv:
        params = predictor.apply_predicted_parameters()
        print("已应用预测参数:")
        print(f"  熵衰减阈值: {params['entropy_threshold_days']}天")
        print(f"  可信度阈值: {params['trust_threshold']}")
        print(f"  系统状态: {len(params['system_state'])}个指标")
    else:
        # 默认：预测并显示
        params = predictor.predict_optimal_parameters()
        print(f"当前系统状态:")
        print(f"  链数: {params['system_state']['total_chains']}")
        print(f"  外部知识比例: {params['system_state']['external_ratio']}")
        print(f"  熵增链比例: {params['system_state']['entropy_ratio']}")
        print(f"  低可信度链比例: {params['system_state']['low_trust_ratio']}")
        print(f"\n预测最优参数:")
        print(f"  熵衰减阈值: {params['entropy_threshold_days']}天")
        print(f"  可信度阈值: {params['trust_threshold']}")
