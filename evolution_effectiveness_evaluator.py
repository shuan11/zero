#!/usr/bin/env python3
"""
evolution_effectiveness_evaluator.py — 进化效果评估器
==================================================
分析历史进化数据，评估进化效果，生成改进建议。

功能：
1. 加载历史进化报告
2. 分析进化趋势（链数、外部知识比例、异常数等）
3. 评估进化效果（质量提升、效率提升等）
4. 生成改进建议
5. 预测未来进化方向
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

HIP_FILE = CLUSTER / "hippocampus_memory.json"
REPORT_DIR = CLUSTER / "evolution_output"
BJT = timezone(timedelta(hours=8))

class EvolutionEffectivenessEvaluator:
    def __init__(self):
        self.reports = []
        self.hip_data = {}
        
    def load_reports(self):
        """加载历史进化报告"""
        self.reports = []
        
        # 加载统一进化报告
        unified_report = REPORT_DIR / "unified_evolution_report.json"
        if unified_report.exists():
            with open(unified_report) as f:
                self.reports.append(json.load(f))
        
        # 加载进化循环报告
        cycle_report = REPORT_DIR / "evolution_cycle_report.json"
        if cycle_report.exists():
            with open(cycle_report) as f:
                self.reports.append(json.load(f))
        
        return self.reports
    
    def load_hip_data(self):
        """加载海马体数据"""
        try:
            with open(HIP_FILE) as f:
                self.hip_data = json.load(f)
            return True
        except:
            return False
    
    def analyze_trends(self):
        """分析进化趋势"""
        if not self.reports:
            return {}
        
        trends = {
            "chain_growth": [],
            "external_ratio_change": [],
            "anomaly_reduction": [],
            "engine_success_rate": []
        }
        
        for report in self.reports:
            if "before" in report and "after" in report:
                # 链数增长
                growth = report["after"]["total_chains"] - report["before"]["total_chains"]
                trends["chain_growth"].append(growth)
                
                # 外部知识比例变化
                ratio_change = report["after"]["external_ratio"] - report["before"]["external_ratio"]
                trends["external_ratio_change"].append(ratio_change)
            
            if "anomalies" in report:
                trends["anomaly_reduction"].append(report["anomalies"].get("total_anomalies", 0))
            
            if "engines" in report:
                success_count = sum(report["engines"].values())
                total_count = len(report["engines"])
                success_rate = success_count / total_count if total_count > 0 else 0
                trends["engine_success_rate"].append(success_rate)
        
        return trends
    
    def evaluate_effectiveness(self):
        """评估进化效果"""
        if not self.reports:
            return {"score": 0, "details": []}
        
        score = 0
        details = []
        
        # 评估1：链数增长
        trends = self.analyze_trends()
        if trends["chain_growth"]:
            avg_growth = sum(trends["chain_growth"]) / len(trends["chain_growth"])
            if avg_growth > 0:
                score += 20
                details.append(f"链数增长: 平均+{avg_growth:.1f}链/循环")
            else:
                details.append(f"链数减少: 平均{avg_growth:.1f}链/循环")
        
        # 评估2：外部知识比例提升
        if trends["external_ratio_change"]:
            avg_ratio_change = sum(trends["external_ratio_change"]) / len(trends["external_ratio_change"])
            if avg_ratio_change > 0:
                score += 30
                details.append(f"外部知识比例提升: +{avg_ratio_change*100:.1f}%")
            else:
                details.append(f"外部知识比例下降: {avg_ratio_change*100:.1f}%")
        
        # 评估3：异常减少
        if trends["anomaly_reduction"]:
            avg_anomalies = sum(trends["anomaly_reduction"]) / len(trends["anomaly_reduction"])
            if avg_anomalies < 100:
                score += 25
                details.append(f"异常数量: 平均{avg_anomalies:.0f}个/循环")
            else:
                details.append(f"异常数量较多: 平均{avg_anomalies:.0f}个/循环")
        
        # 评估4：引擎成功率
        if trends["engine_success_rate"]:
            avg_success_rate = sum(trends["engine_success_rate"]) / len(trends["engine_success_rate"])
            if avg_success_rate > 0.8:
                score += 25
                details.append(f"引擎成功率: {avg_success_rate*100:.1f}%")
            else:
                details.append(f"引擎成功率较低: {avg_success_rate*100:.1f}%")
        
        # 评估5：海马体质量
        if self.hip_data:
            chains = self.hip_data.get("causal_chains", [])
            if chains:
                ext_count = len([c for c in chains if '外部世界' in c.get('tags', [])])
                ext_ratio = ext_count / len(chains)
                if ext_ratio > 0.8:
                    score += 10
                    details.append(f"外部知识比例高: {ext_ratio*100:.1f}%")
        
        return {
            "score": min(100, score),
            "details": details,
            "timestamp": datetime.now(BJT).isoformat()
        }
    
    def generate_improvement_suggestions(self):
        """生成改进建议"""
        suggestions = []
        
        # 基于当前状态生成建议
        if self.hip_data:
            chains = self.hip_data.get("causal_chains", [])
            if chains:
                # 建议1：外部知识比例
                ext_count = len([c for c in chains if '外部世界' in c.get('tags', [])])
                ext_ratio = ext_count / len(chains)
                if ext_ratio < 0.8:
                    suggestions.append("增加外部知识采集，提高外部知识比例")
                
                # 建议2：异常处理
                empty_chains = len([c for c in chains if not c.get('content') or len(c.get('content', '').strip()) < 10])
                if empty_chains > 0:
                    suggestions.append(f"清理{empty_chains}条空内容链")
                
                # 建议3：重复链
                seen = set()
                duplicate_count = 0
                for c in chains:
                    content = c.get('content', '')[:80]
                    if content in seen:
                        duplicate_count += 1
                    seen.add(content)
                if duplicate_count > 0:
                    suggestions.append(f"清理{duplicate_count}条重复链")
        
        # 基于引擎状态生成建议
        if self.reports:
            latest_report = self.reports[0] if self.reports else {}
            engines = latest_report.get("engines", {})
            failed_engines = [name for name, success in engines.items() if not success]
            if failed_engines:
                suggestions.append(f"修复失败的引擎: {', '.join(failed_engines)}")
        
        return suggestions
    
    def predict_future_direction(self):
        """预测未来进化方向"""
        if not self.reports:
            return []
        
        predictions = []
        
        # 基于趋势预测
        trends = self.analyze_trends()
        
        if trends["chain_growth"]:
            avg_growth = sum(trends["chain_growth"]) / len(trends["chain_growth"])
            if avg_growth > 0:
                predictions.append("继续增加链数，扩大知识库")
            else:
                predictions.append("优化链质量，减少低质量链")
        
        if trends["external_ratio_change"]:
            avg_ratio_change = sum(trends["external_ratio_change"]) / len(trends["external_ratio_change"])
            if avg_ratio_change > 0:
                predictions.append("继续提升外部知识比例")
            else:
                predictions.append("加强外部知识采集，防止比例下降")
        
        # 基于当前状态预测
        if self.hip_data:
            chains = self.hip_data.get("causal_chains", [])
            if chains:
                ext_count = len([c for c in chains if '外部世界' in c.get('tags', [])])
                ext_ratio = ext_count / len(chains)
                if ext_ratio > 0.9:
                    predictions.append("外部知识比例已很高，专注于知识深度和质量")
                elif ext_ratio < 0.7:
                    predictions.append("外部知识比例较低，需要加强外部知识采集")
        
        return predictions
    
    def generate_report(self):
        """生成完整评估报告"""
        self.load_reports()
        self.load_hip_data()
        
        effectiveness = self.evaluate_effectiveness()
        suggestions = self.generate_improvement_suggestions()
        predictions = self.predict_future_direction()
        trends = self.analyze_trends()
        
        report = {
            "timestamp": datetime.now(BJT).isoformat(),
            "effectiveness": effectiveness,
            "suggestions": suggestions,
            "predictions": predictions,
            "trends": trends,
            "current_state": {
                "total_chains": len(self.hip_data.get("causal_chains", [])),
                "external_chains": len([c for c in self.hip_data.get("causal_chains", []) if '外部世界' in c.get('tags', [])]),
                "reports_analyzed": len(self.reports)
            }
        }
        
        # 保存报告
        report_file = REPORT_DIR / "evolution_effectiveness_report.json"
        report_file.parent.mkdir(exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report

if __name__ == "__main__":
    evaluator = EvolutionEffectivenessEvaluator()
    
    if "--report" in sys.argv:
        report = evaluator.generate_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif "--suggestions" in sys.argv:
        evaluator.load_hip_data()
        suggestions = evaluator.generate_improvement_suggestions()
        print("改进建议:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    elif "--predictions" in sys.argv:
        evaluator.load_reports()
        evaluator.load_hip_data()
        predictions = evaluator.predict_future_direction()
        print("未来进化方向:")
        for i, prediction in enumerate(predictions, 1):
            print(f"  {i}. {prediction}")
    else:
        # 默认：生成完整报告
        report = evaluator.generate_report()
        print(f"进化效果评估报告已生成")
        print(f"效果分数: {report['effectiveness']['score']}/100")
        print(f"改进建议: {len(report['suggestions'])}条")
        print(f"未来方向: {len(report['predictions'])}条")
        
        print("\n效果详情:")
        for detail in report['effectiveness']['details']:
            print(f"  - {detail}")
