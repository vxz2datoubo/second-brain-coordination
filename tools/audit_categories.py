import json
from collections import Counter

with open('F:/ai/data/knowledge-graph.json', 'r', encoding='utf-8') as f:
    kg = json.load(f)

nodes = kg['nodes']
total = len(nodes)
print(f'总节点数: {total}')

cats = Counter()
sources = Counter()
bad_tags = Counter()
for nid, n in nodes.items():
    cats[n.get('category', 'unknown')] += 1
    sources[n.get('source', 'unknown')] += 1
    for t in n.get('tags', []):
        if len(t) <= 1:
            bad_tags[t] += 1

print(f'\n=== 分类分布(实际) ===')
for c, cnt in cats.most_common():
    pct = cnt/total*100
    print(f'  {c}: {cnt} ({pct:.1f}%)')

print(f'\n=== 来源分布 ===')
for s, cnt in sources.most_common():
    print(f'  {s}: {cnt}')

print(f'\n=== 单字垃圾标签 Top20 ===')
for t, cnt in bad_tags.most_common(20):
    print(f'  "{t}": {cnt}')

all_tags = Counter()
for nid, n in nodes.items():
    for t in n.get('tags', []):
        all_tags[t] += 1
print(f'\n=== 标签统计 ===')
print(f'  唯一标签数: {len(all_tags)}')
print(f'  标签总出现: {sum(all_tags.values())}')
useful = [(t,c) for t,c in all_tags.most_common(50) if len(t) >= 2]
print(f'  双字+标签 Top50:')
for t, c in useful:
    print(f'    {t}: {c}')

# 来源x分类交叉
print(f'\n=== 来源x分类交叉 ===')
cross = Counter()
for nid, n in nodes.items():
    cross[(n.get('source','?'), n.get('category','?'))] += 1
for k, v in cross.most_common():
    print(f'  {k[0]} -> {k[1]}: {v}')
