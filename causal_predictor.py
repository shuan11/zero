#!/usr/bin/env python3
"""
causal_predictor.py — 因果预测引擎
==================================
基于27327条4跳路径构建预测能力，让集群能预测未来状态。

功能：
  - predict_next(当前状态): 基于当前实体状态预测下一个最可能出现的状态
  - predict_consequence(行动): 预测某个行动的连锁后果
  - predict_anomaly(症状): 预测某个症状可能导致的系统异常
  - predict_sequence(起始, 步数): 多步预测

基于:
  - 27327条4跳路径
  - 13个实体的转移矩阵
  - 129个起点-终点对
"""
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

MODEL_FILE = CLUSTER / "prediction_model.json"
HIP_FILE = CLUSTER / "hippocampus_memory.json"
BJT = timezone(timedelta(hours=8))

class CausalPredictor:
    def __init__(self):
        self.transitions = {}
        self.path_count = 0
        self.unique_paths = 0
        self.start_end_pairs = 0
        self.segments = 0
        
    def load(self, model_path=None):
        """加载预测模型"""
        path = model_path or MODEL_FILE
        with open(path) as f:
            model = json.load(f)
        
        self.transitions = model.get("transitions", {})
        self.path_count = model.get("path_count", 0)
        self.unique_paths = model.get("unique_paths", 0)
        self.start_end_pairs = model.get("start_end_pairs", 0)
        self.segments = model.get("segments", 0)
        
        print(f"预测模型已加载: {len(self.transitions)}实体, {self.path_count}条路径")
        return self
    
    def predict_next(self, current_entity, top_n=3):
        """给定当前实体，预测下一个最可能的实体"""
        if current_entity not in self.transitions:
            return []
        
        next_probs = self.transitions[current_entity]
        total = sum(next_probs.values())
        predictions = []
        
        for entity, count in sorted(next_probs.items(), key=lambda x: -x[1])[:top_n]:
            prob = count / total
            predictions.append({
                "entity": entity,
                "probability": round(prob, 3),
                "count": count
            })
        
        return predictions
    
    def predict_consequence(self, action_entity, steps=3):
        """预测某个行动的连锁后果"""
        if action_entity not in self.transitions:
            return {"action": action_entity, "consequences": [], "path": []}
        
        sequence = [action_entity]
        current = action_entity
        consequences = []
        
        for _ in range(steps):
            predictions = self.predict_next(current, 1)
            if not predictions:
                break
            
            next_entity = predictions[0]["entity"]
            prob = predictions[0]["probability"]
            
            sequence.append(next_entity)
            consequences.append({
                "from": current,
                "to": next_entity,
                "probability": prob
            })
            current = next_entity
        
        return {
            "action": action_entity,
            "consequences": consequences,
            "path": sequence,
            "final_state": sequence[-1] if sequence else None
        }
    
    def predict_anomaly(self, symptom_entity, top_n=5):
        """预测某个症状可能导致的系统异常"""
        if symptom_entity not in self.transitions:
            return {"symptom": symptom_entity, "anomalies": []}
        
        # 找到从该症状出发的所有路径终点
        end_counter = Counter()
        
        # BFS找所有4跳路径
        queue = [(symptom_entity, [symptom_entity])]
        while queue:
            current, path = queue.pop(0)
            if len(path) == 5:  # 4跳
                end_counter[path[-1]] += 1
                continue
            if len(path) > 5:
                continue
            
            for neighbor in self.transitions.get(current, {}).keys():
                if neighbor not in path:  # 避免环
                    queue.append((neighbor, path + [neighbor]))
        
        anomalies = []
        total = sum(end_counter.values())
        for entity, count in end_counter.most_common(top_n):
            anomalies.append({
                "entity": entity,
                "probability": round(count / total, 3) if total > 0 else 0,
                "count": count
            })
        
        return {
            "symptom": symptom_entity,
            "anomalies": anomalies,
            "total_paths": total
        }
    
    def predict_sequence(self, start_entity, steps=4, top_n=1):
        """多步预测"""
        sequence = [start_entity]
        current = start_entity
        probabilities = []
        
        for _ in range(steps):
            predictions = self.predict_next(current, top_n)
            if not predictions:
                break
            
            next_entity = predictions[0]["entity"]
            prob = predictions[0]["probability"]
            
            sequence.append(next_entity)
            probabilities.append(prob)
            current = next_entity
        
        return {
            "start": start_entity,
            "sequence": sequence,
            "steps": steps,
            "probabilities": probabilities,
            "average_probability": sum(probabilities) / len(probabilities) if probabilities else 0
        }
    
    def generate_report(self):
        """生成预测能力报告"""
        report = {
            "timestamp": datetime.now(BJT).isoformat(),
            "model_stats": {
                "entities": len(self.transitions),
                "total_paths": self.path_count,
                "unique_paths": self.unique_paths,
                "start_end_pairs": self.start_end_pairs,
                "segments": self.segments
            },
            "sample_predictions": {}
        }
        
        # 生成一些示例预测
        sample_entities = ["执行", "分析", "检测", "修复", "停滞"]
        for entity in sample_entities:
            if entity in self.transitions:
                report["sample_predictions"][entity] = {
                    "next": self.predict_next(entity, 3),
                    "sequence": self.predict_sequence(entity, 3),
                    "anomaly": self.predict_anomaly(entity, 3)
                }
        
        return report
    
    def write_to_hippocampus(self, prediction_results):
        """将预测结果写入海马体"""
        try:
            hip = json.load(open(HIP_FILE))
        except:
            hip = {"causal_chains": []}
        
        timestamp = datetime.now(BJT).isoformat()
        
        # 写入预测报告
        hip["causal_chains"].append({
            "content": f"[因果预测] 预测模型: {len(self.transitions)}实体/{self.path_count}条路径",
            "source": "causal_predictor",
            "tags": ["因果预测", "预测模型", "系统洞察"],
            "timestamp": timestamp,
        })
        
        # 写入具体预测结果
        for entity, preds in prediction_results.get("sample_predictions", {}).items():
            next_preds = preds.get("next", [])
            if next_preds:
                top_pred = next_preds[0]
                hip["causal_chains"].append({
                    "content": f"[预测] {entity} → {top_pred['entity']} (概率:{top_pred['probability']})",
                    "source": "causal_predictor",
                    "tags": ["因果预测", "状态预测", entity],
                    "timestamp": timestamp,
                })
        
        with open(HIP_FILE, "w") as f:
            json.dump(hip, f, ensure_ascii=False, indent=2)
        
        return len(hip["causal_chains"])

if __name__ == "__main__":
    predictor = CausalPredictor()
    predictor.load()
    
    if "--report" in sys.argv:
        report = predictor.generate_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif "--predict" in sys.argv:
        if len(sys.argv) > 2:
            entity = sys.argv[2]
            steps = int(sys.argv[3]) if len(sys.argv) > 3 else 3
            result = predictor.predict_sequence(entity, steps)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("用法: python3 causal_predictor.py --predict <实体> [步数]")
    elif "--anomaly" in sys.argv:
        if len(sys.argv) > 2:
            entity = sys.argv[2]
            result = predictor.predict_anomaly(entity)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("用法: python3 causal_predictor.py --anomaly <症状实体>")
    else:
        # 默认：生成报告并写入海马体
        report = predictor.generate_report()
        chains_count = predictor.write_to_hippocampus(report)
        print(f"因果预测引擎报告已生成")
        print(f"模型统计: {len(predictor.transitions)}实体, {predictor.path_count}条路径")
        print(f"海马体: {chains_count}链")
        
        # 显示一些示例预测
        print("\n示例预测:")
        for entity in ["执行", "分析", "检测"]:
            if entity in predictor.transitions:
                seq = predictor.predict_sequence(entity, 3)
                print(f"  {entity} → {' → '.join(seq['sequence'])}")
