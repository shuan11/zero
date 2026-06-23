"""
上下文重建协议 (Context Reconstruction Protocol) v1
====================================================
目标：模拟无限上下文——不是不压缩，是压缩后能无损重建。

核心原理：
  无限上下文 ≠ 把所有东西放内存
  无限上下文 = 始终知道"我缺什么" + "去哪找回"

四层架构：
  Layer 0: 活动上下文（当前会话，有限但知道自己的边界）
  Layer 1: 索引层（轻量级json，告诉系统"你知道什么"）
  Layer 2: 归档层（原始数据，永不删除）
  Layer 3: 重建协议（当需要时，从Layer 2→Layer 1→Layer 0）
"""
import os, json, time, hashlib
from datetime import datetime

CLUSTER = "/mnt/c/Users/h/Desktop/零/真元集群"
SESSION_DIR = os.path.expanduser("~/.hermes/sessions")

class ContextReconstructionProtocol:
    """上下文重建协议——模拟无限上下文的核心"""
    
    def __init__(self):
        self.index_path = f"{CLUSTER}/context_index.json"
        self.handoff_path = f"{CLUSTER}/ZERO-HANDOFF.json"
        self.index = self._load_index()
    
    def _load_index(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "version": 1,
            "last_built": None,
            "sessions_indexed": 0,
            "archives": {},      # 归档映射：topic → {session_id, date, summary}
            "knowledge_map": {}, # 知识映射：concept → [source_locations]
            "compression_log": [], # 压缩记录：每次压缩丢失了什么
        }
    
    def _save(self):
        with open(self.index_path, 'w') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def scan_sessions(self, limit=100):
        """扫描近期会话建立索引"""
        if not os.path.exists(SESSION_DIR):
            return 0
        
        sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.json')]
        sessions.sort(reverse=True)
        
        new_count = 0
        for s in sessions[:limit]:
            sid = s.replace('.json', '')
            if sid not in self.index.get('archives', {}):
                # 读取会话摘要
                try:
                    with open(os.path.join(SESSION_DIR, s), 'r') as f:
                        content = f.read()
                    # 提取前200字符作为摘要
                    summary = content[:200].replace('\n', ' ').strip()
                    self.index.setdefault('archives', {})[sid] = {
                        'summary': summary[:100],
                        'size': len(content),
                        'indexed_at': datetime.now().isoformat()
                    }
                    new_count += 1
                except:
                    pass
        
        self.index['sessions_indexed'] = len(self.index.get('archives', {}))
        self.index['last_built'] = datetime.now().isoformat()
        self._save()
        return new_count
    
    def record_compression(self, what_was_lost, context_snapshot=None):
        """记录一次上下文压缩——这是核心：压缩不是丢失，是归档"""
        self.index.setdefault('compression_log', []).append({
            'timestamp': datetime.now().isoformat(),
            'what_was_lost': what_was_lost,
            'sessions_before': self.index.get('sessions_indexed', 0),
        })
        # 如果不超过100条，保留完整日志
        if len(self.index['compression_log']) > 100:
            self.index['compression_log'] = self.index['compression_log'][-100:]
        self._save()
    
    def detect_context_gaps(self, current_context_summary):
        """检测当前上下文可能缺失什么"""
        # 基于handoff和历史记录检查
        gaps = []
        
        # 检查HANDOFF
        if os.path.exists(self.handoff_path):
            try:
                with open(self.handoff_path, 'r') as f:
                    handoff = json.load(f)
                last_p0 = handoff.get('next_p0', '')
                if last_p0 and 'consensus' not in current_context_summary:
                    gaps.append(f"上次P0任务未完成: {last_p0}")
            except:
                pass
        
        # 检查最近一次压缩记录
        if self.index.get('compression_log'):
            last_compress = self.index['compression_log'][-1]
            gaps.append(f"上次压缩丢失: {last_compress.get('what_was_lost', '未知')}")
        
        return gaps
    
    def get_reconstruction_plan(self):
        """生成重建计划——告诉我需要恢复什么"""
        plan = []
        
        # 检查索引状态
        indexed = self.index.get('sessions_indexed', 0)
        total_sessions = 0
        if os.path.exists(SESSION_DIR):
            total_sessions = len([f for f in os.listdir(SESSION_DIR) if f.endswith('.json')])
        
        unindexed = total_sessions - indexed
        if unindexed > 0:
            plan.append(f"未索引会话: {unindexed}/{total_sessions}")
        
        # 检查HANDOFF
        if os.path.exists(self.handoff_path):
            try:
                with open(self.handoff_path) as f:
                    hj = json.load(f)
                next_p0 = hj.get('next_p0', '')
                if next_p0:
                    plan.append(f"待恢复P0: {next_p0}")
            except:
                pass
        
        return plan


if __name__ == "__main__":
    crp = ContextReconstructionProtocol()
    
    print("=== 上下文重建协议: 状态报告 ===")
    print(f"已索引会话: {crp.index.get('sessions_indexed', 0)}")
    print(f"压缩记录: {len(crp.index.get('compression_log', []))}条")
    
    print("\n=== 扫描新会话 ===")
    new = crp.scan_sessions(limit=200)
    print(f"新增索引: {new}个会话")
    print(f"总计索引: {crp.index.get('sessions_indexed', 0)}")
    
    gaps = crp.detect_context_gaps("当前会话上下文摘要")
    print(f"\n=== 检测到的上下文缺口 ===")
    for g in gaps:
        print(f"  ⚠️  {g}")
    
    plan = crp.get_reconstruction_plan()
    print(f"\n=== 重建建议 ===")
    for p in plan:
        print(f"  → {p}")
    
    print(f"\n=== 关键指标 ===")
    print(f"  全量会话文件: {len([f for f in os.listdir(SESSION_DIR) if f.endswith('.json')])}")
    print(f"  已建立索引: {crp.index.get('sessions_indexed', 0)}")
    print(f"  重建协议: 就绪")
