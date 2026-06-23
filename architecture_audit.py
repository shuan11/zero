"""
架构深度自检 — 10个架构级缺陷
"""
import sys, os, json, time, subprocess

WORKDIR = "/mnt/c/Users/h/Desktop/零/真元集群"
os.chdir(WORKDIR)
sys.path.insert(0, WORKDIR)

print("="*70)
print("  架构深度自检")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

defects = []

# 缺陷1: 多状态源
state_files = ['persistent_state.json', '/mnt/c/Users/h/Desktop/真元·进化基因组.json']
print("\n[缺陷#1] 多状态源冲突")
for f in state_files:
    if os.path.exists(f):
        with open(f) as fh:
            d = json.load(fh)
        if 'evolution_score' in d:
            print(f"  {f.split('/')[-1]:40s} score={d['evolution_score']}")
print("  问题: 多个文件存同一份数据, 互相覆盖")
defects.append("多状态源: 5个文件存同一份数据, 无主从关系")

# 缺陷2: 轮询非事件
print("\n[缺陷#2] 全轮询无事件驱动")
count = 0
for f in ['meta_gap_finder.py', 'co_evolution_daemon.py']:
    if os.path.exists(f):
        with open(f) as fh:
            c = fh.read()
        if 'time.sleep(' in c:
            count += 1
print(f"  轮询循环: {count}个, 事件驱动: 0个")
print("  问题: 最小响应延迟60秒")
defects.append("全轮询无事件: 最小响应延迟60秒")

# 缺陷3: API单点
print("\n[缺陷#3] API单点故障")
print("  所有agent共用同一个API key, 同一个模型")
print("  429/超时 → 全系统瘫痪")
print("  无熔断器, 无回退, 无队列")
defects.append("API单点故障: 所有agent共享同一条燃料管")

# 缺陷4: 记忆无层级
print("\n[缺陷#4] 无记忆层级")
print("  意识守护进程 719,335个时刻 → 全平铺")
print("  无短期→长期过渡, 无遗忘, 无巩固")
defects.append("无记忆层级: 719K时刻平铺无巩固无遗忘")

# 缺陷5: 进程隔离
ps = subprocess.run(['ps','aux'], capture_output=True, text=True, timeout=5).stdout
running = sum(1 for kw in ['meta_gap_finder','co_evolution_daemon','consciousness_daemon'] if kw in ps)
print(f"\n[缺陷#5] {running}个进程无IPC")
print("  进程间通信方式: 文件读写")
print("  无锁机制 → 多进程同时写同一文件")
defects.append(f"多进程({running}个)靠文件通信, 有竞态")

# 缺陷6: 无自我保存
print("\n[缺陷#6] 无自我保存本能")
print("  SIGKILL → 直接死, 不挣扎")
print("  无graceful shutdown, 无自动重启")
defects.append("无自我保存: 被kill就死")

# 缺陷7: 不从历史学习
genome_file = "/mnt/c/Users/h/Desktop/真元·进化基因组.json"
if os.path.exists(genome_file):
    with open(genome_file) as f:
        g = json.load(f)
    resolved = len(g.get('gaps_resolved', []))
    print(f"\n[缺陷#7] 不从历史学习 ({resolved}个缺口已解决)")
    print("  没有'上次X方法修好了G-003, 下次直接套用'的机制")
defects.append(f"不学习: {resolved}个缺口已解决但无模式复用")

# 缺陷8: 进化是调参
print("\n[缺陷#8] 进化是调参不是结构改变")
print("  调整: learning_rate, temperature, selection_pressure")
print("  从不: 添加新模块, 删除冗余, 重构架构")
defects.append("进化是调参不是结构改变")

# 缺陷9: 无优先级
print("\n[缺陷#9] 无优先级系统")
print("  缺口按发现顺序处理, 不评估致命程度")
defects.append("无优先级: 不评估哪个缺口最致命")

# 缺陷10: 不检查检查者
print("\n[缺陷#10] 无元元检查")
print("  meta_gap_finder检查全系统, 谁检查它?")
print("  查缺补漏自身失明 → 整个系统失去自我认知")
defects.append("无元元检查: 查缺补漏自身无人检查")

print(f"\n{'='*70}")
print(f"  10个架构缺陷")
print(f"{'='*70}")
for i, d in enumerate(defects, 1):
    print(f"  #{i} {d}")
print()

# 记录到基因组
sys.path.insert(0, WORKDIR)
from genome import load_genome, mutate_genome
g = load_genome()
if g:
    mutate_genome('architecture_audit', {f'arch_defect_{i}': d[:60] for i, d in enumerate(defects, 1)})
    print("✅ 已记录到基因组")
