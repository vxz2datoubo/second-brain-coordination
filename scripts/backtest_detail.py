import json

with open('data/kl_300418_1y.json', 'r') as f:
    data = json.load(f)

# Top 5 closest matches
matches_data = [
    {"date":"20260202","open_chg":-3.4,"high_from":4.9,"hi2lo":-6.7,"amp":6.8,"rebound":0.0,"next":6.0,"two":11.7,"vol":0.7},
    {"date":"20260320","open_chg":-2.4,"high_from":4.8,"hi2lo":-5.2,"amp":5.3,"rebound":0.8,"next":-6.9,"two":-9.8,"vol":1.2},
    {"date":"20260115","open_chg":-1.7,"high_from":5.5,"hi2lo":-6.7,"amp":6.9,"rebound":2.8,"next":-10.5,"two":-12.9,"vol":1.7},
    {"date":"20260323","open_chg":-2.7,"high_from":2.8,"hi2lo":-7.4,"amp":7.4,"rebound":0.6,"next":-3.2,"two":1.9,"vol":1.0},
    {"date":"20260309","open_chg":-1.5,"high_from":6.4,"hi2lo":-6.7,"amp":7.0,"rebound":5.7,"next":2.0,"two":-2.1,"vol":0.7},
]

print('Top 5 最相似日详情:')
print()
for i,m in enumerate(matches_data):
    nd = f'{m["next"]:+.1f}%' 
    td = f'{m["two"]:+.1f}%'
    print(f'#{i+1} {m["date"]}: 开{m["open_chg"]:+.0f}%→冲{m["high_from"]:+.0f}%→跌{m["hi2lo"]:+.0f}%→弹{m["rebound"]:+.1f}% | 次日{nd} 2日{td}')

# Quick check: sector context for these dates
print()
print('场景特征分析:')
print('- 低开急拉深跌后: 日内弹回的概率92%, 但次日上涨概率仅42%')
print('- 这意味着: 今天大概率能收回部分跌幅, 但明天大概率续跌')  
print('- 胜者次日均涨+5.0%, 败者次日均跌-4.8% → 次日波幅剧烈')
print('- 量比1.3x意味着这种日子的成交量高于20日均值, 是"事件驱动型"而非"随机波动型"')

# 今日预测区间
print()
print('='*50)
print('今日昆仑操作参考:')
print(f'  高46.69 → 低43.41 = 跌幅3.28元')
print(f'  38.2%反弹 → 44.66元 ✅ 保守目标')
print(f'  50.0%反弹 → 45.05元 ⚠️ 中等目标(历史42%概率达到)')  
print(f'  61.8%反弹 → 45.44元 🔴 激进目标(历史33%概率达到)')
print()
print(f'  你的双槽: 44.00 / 45.81')
print(f'  44.00 → 到44.66就有+1.5% → 槽2目标区 44.50-44.70 合理')
print(f'  45.81 → 到44.66还亏-2.5% → 槽1今天无望平出')
print()
print(f'  建议: 槽2到44.5-44.7走, 槽1等明天(历史规律:次日大概率续跌)')
