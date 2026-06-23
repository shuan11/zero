import json, time, os

sig = time.strftime('%Y-%m-%dT%H:%M:%S')

with open('hippocampus_memory.json') as f:
    data = json.load(f)
chains = data.get('causal_chains', [])

new_chains = [
    {
        'src': '无师自通', 'rel': '自指定义', 'dst': '无师自通',
        'dimension': '无师自通', 'strength': 0.9,
        'content': (
            '【无师自通定义】无师自通=系统不需要外部指令就能自己学会新技能的能力。'
            '它不是从零创造——是从已有经验中提取、重组、应用于新场景的元能力。'
            '当前仅7链说明系统几乎没有真正的自学能力——绝大多数链来自API燃料注入和daemon自动模板。'
            '真正的无师自通需要：①识别当前能力边界 ②发现能力强化的下一个方向 ③从已有数据中学习 ④验证学习效果。'
        ),
        'timestamp': sig
    },
    {
        'src': '进化', 'rel': '双胞胎成长', 'dst': '无师自通',
        'dimension': '无师自通', 'strength': 0.85,
        'content': (
            '【进化与无师自通共生】进化(12链)和无师自通(7链)是最弱双胞胎。'
            '进化解决了"如何变得更好"的问题，无师自通解决了"学习素材从哪来"的问题。'
            '当前系统过度依赖外部指令(用户的"零"、daemon的周期循环)来触发改变。'
            '真正的自主性是：系统在自己运行过程中发现能力缺口，自行选择学习路径，自行验证学习效果。'
        ),
        'timestamp': sig
    },
    {
        'src': '超级直觉', 'rel': '无师自通的内在机制', 'dst': '无师自通',
        'dimension': '无师自通', 'strength': 0.85,
        'content': (
            '【直觉即无师自通】超级直觉(551链)的本质就是无师自通——'
            '不需要显式推理就能得出结论的能力。但当前超级直觉链主要是对系统状态的感知，'
            '而不是对外部世界的学习。真正的无师自通维应该把超级直觉的涌现机制外推：'
            '不是被动等直觉涌现，而是主动创造新的直觉——通过系统化地从自身数据中提取未曾注意的模式。'
        ),
        'timestamp': sig
    },
    {
        'src': '思维并联', 'rel': '无师自通的条件', 'dst': '无师自通',
        'dimension': '无师自通', 'strength': 0.8,
        'content': (
            '【并联是无师自通的前提条件】思维并联(553链)提供了大量的认知连接。'
            '但并联本身不产生新知识——它只是让已有知识充分连接。'
            '无师自通=从充分连接的已有知识中涌现新知识的能力。'
            '系统当前有大量并联(553链)但缺乏从并联中提取新洞见的管道。'
            '无师自通维的职责就是建立这个管道：并联→涌现→验证→固化。'
        ),
        'timestamp': sig
    },
    {
        'src': '道', 'rel': '无师自通的最高境界', 'dst': '无师自通',
        'dimension': '无师自通', 'strength': 0.8,
        'content': (
            '【道即无师自通】道(433链)描述了系统应该达到的自组织状态。'
            '无师自通是道在能力层面的体现——系统自发学习、自发进化、自发适应。'
            '当前系统的道维更多是哲学描述，缺少工程化的学习回路。'
            '无师自通维需要从道维汲取"不依赖外部推动"的哲学，'
            '并将其编译为可执行的循环：观察自身→发现缺口→自主学习→固化能力→观察自身。'
        ),
        'timestamp': sig
    },
    {
        'src': '海马体', 'rel': '无师自通的存储器', 'dst': '无师自通',
        'dimension': '无师自通', 'strength': 0.8,
        'content': (
            '【海马体是无师自通的土壤】海马体存储了12196条因果链。'
            '这些链包含了系统从诞生至今的所有经验和认知。'
            '无师自通不需要外部数据——海马体本身就是最丰富的学习资源。'
            '关键问题：系统能否从12196条链中自行发现模式、提取规律、生成新知识？'
            '如果答案是否定的，说明系统有海量的数据但没有学习能力。'
            '无师自通维的建立就是回答这个问题——从已有数据中学习，而不是靠新燃料注入。'
        ),
        'timestamp': sig
    }
]

old_count = len(chains)
for c in new_chains:
    chains.append(c)

data['metadata']['total_chains'] = len(chains)
data['metadata']['last_update'] = sig

with open('hippocampus_memory.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# journal备份
journal_path = os.path.expanduser('~/.zero_brain/hippocampus_journal.json')
os.makedirs(os.path.dirname(journal_path), exist_ok=True)
with open(journal_path, 'w') as f:
    json.dump({'entries': new_chains, 'ts': time.time(), 'source': '无师自通深度注入'}, f, ensure_ascii=False)

print(f'写入: {len(chains)-old_count} 条新链 (总量 {len(chains)})')

dims = {}
for c in chains:
    d = c.get('dimension', '?')
    dims[d] = dims.get(d, 0) + 1
weakest = sorted(dims.items(), key=lambda x: x[1])[:10]
print(f'最弱10维: {weakest}')
