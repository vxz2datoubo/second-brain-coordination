from retrieval.retriever import WisdomRetriever

retriever = WisdomRetriever()

print('检索「追高」结果:')
results = retriever.retrieve('追高')
for r in results:
    print(f'  分数:{r["score"]} 标题:{r["node"]["title"]}')

print()
print('检索「昆仑」结果:')
results2 = retriever.retrieve('昆仑')
for r in results2:
    print(f'  分数:{r["score"]} 标题:{r["node"]["title"]}')

print()
print('按类别检索:')
results3 = retriever.retrieve_by_category('因果洞察')
for r in results3:
    print(f'  {r["title"]}')
