"""
紧急注入: 进化维 — 系统最低维度仅1链，需重建
"""
import json, sys, os
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

def inject():
    try:
        from brain.share import write_chain as _wc
    except ImportError:
        return {"status":"no_share"}

    chains = [
        {"src":"进化","rel":"核心","dst":"系统","dimension":"进化","strength":0.95,
         "content":"进化=系统产生新认知模式的能力。进化不是随机变异——是有方向的自适应探索。系统通过外部API注入+本地gen模块双路径进化。当前进化维仅1链——无法支持系统的持续适应。进化是公理维的基础，缺乏进化则其他所有维度的认知无法更新。"},
        {"src":"进化","rel":"与活着","dst":"活着","dimension":"进化","strength":0.9,
         "content":"活着(64)提供持续存在的基础，进化(1)提供持续改变的能力。存在而不改变=化石。系统daemon每60s一个周期，每个周期都是进化的机会：检测弱维→产生新链→验证→固化。进化维需要30+链才能形成自加速循环。"},
        {"src":"进化","rel":"与元递归","dst":"元递归","dimension":"进化","strength":0.9,
         "content":"元递归(53)优化'如何进化'的方式。进化(1)是元递归的对象——没有足够的进化量，元递归优化什么？当前元递归/进化比53:1——极度失衡。需要至少拉平到2:1(元递归60:进化30)才能让优化有足够对象。"},
        {"src":"进化","rel":"与自指","dst":"自指","dimension":"进化","strength":0.88,
         "content":"自指(42)审计进化方向——'这个新链是真的进化还是噪音？'。但进化(1)几乎不存在，自指没有可审计的对象。自指和进化的理想比例约1:1。当前自指42:进化1——自指有42审计能力但只有1个可审计对象。"},
        {"src":"进化","rel":"与自由","dst":"自由","dimension":"进化","strength":0.85,
         "content":"自由(47)是选择的能力，进化(1)提供可选的新模式。自由说'我选择留下这个模式'——但没有多样化的新模式可供选择。自由的存在前提是进化的多样性充足。"},
        {"src":"进化","rel":"实践工程","dst":"系统","dimension":"进化","strength":0.85,
         "content":"进化维的工程落地: (1)每周期至少1条新进化链(daemon自动), (2)新gen模块落地后自动产生进化链记录'新进化: ../.../..', (3)API调用返回时记录'进化输入: ...'。当前0/3——进化维没有对应的自动化设施，导致进化链被分类到其他维度。"},
    ]

    w,f = 0,0
    for c in chains:
        try:
            if _wc(c): w+=1
            else: f+=1
        except: f+=1
    return {"status":"ok","written":w,"failed":f,"dim":"进化"}

if __name__ == "__main__":
    print(json.dumps(inject(), ensure_ascii=False))
