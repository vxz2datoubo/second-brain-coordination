# A股进化引擎 - 自学习、自迭代、自检验
import json
import os
from pathlib import Path
from datetime import datetime, date
import statistics

LOG_DIR = Path(r'F:\aidanao\core\logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f'[EVOLVE {ts}] {msg}'
    print(line, flush=True)
    with open(LOG_DIR / 'evolution.log', 'a', encoding='utf-8') as f:
        f.write(line + '\n')

class EvolutionEngine:
    def __init__(self):
        self.stats_file = LOG_DIR / 'trade_stats.json'
        self.learnings_file = LOG_DIR / 'learnings.json'
        self.stats = self._load(self.stats_file, {
            'total_trades': 0, 'win': 0, 'loss': 0,
            'total_pnl': 0, 'daily_pnl': {},
            'by_stock': {'kunlun': {'win':0,'loss':0,'pnl':0}, 'lanbiao': {'win':0,'loss':0,'pnl':0}},
            'by_conditions': {},
            'best_buy_time': {}, 'best_sell_time': {},
            'rule_effectiveness': {},
        })
        self.learnings = self._load(self.learnings_file, [])

    def _load(self, path, default):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding='utf-8'))
            except:
                pass
        return default

    def _save(self, path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def record_trade(self, stock, direction, price, amount, pnl, conditions):
        self.stats['total_trades'] += 1
        if pnl > 0:
            self.stats['win'] += 1
        else:
            self.stats['loss'] += 1
        self.stats['total_pnl'] += pnl

        key = stock
        self.stats['by_stock'][key]['pnl'] += pnl
        if pnl > 0:
            self.stats['by_stock'][key]['win'] += 1
        else:
            self.stats['by_stock'][key]['loss'] += 1

        # 记录条件有效性
        for cond in conditions:
            if cond not in self.stats['rule_effectiveness']:
                self.stats['rule_effectiveness'][cond] = {'win': 0, 'loss': 0}
            if pnl > 0:
                self.stats['rule_effectiveness'][cond]['win'] += 1
            else:
                self.stats['rule_effectiveness'][cond]['loss'] += 1

        today = str(date.today())
        if today not in self.stats['daily_pnl']:
            self.stats['daily_pnl'][today] = 0
        self.stats['daily_pnl'][today] += pnl

        self._save(self.stats_file, self.stats)
        log(f'recorded trade: {stock} {direction} pnl={pnl:.2f} total={self.stats[total_pnl]:.2f}')

    def get_insights(self):
        insights = []
        # 胜率
        total = self.stats['total_trades']
        if total > 0:
            win_rate = self.stats['win'] / total
            insights.append(f'总胜率: {win_rate*100:.1f}% ({self.stats[win]}胜/{self.stats[loss]}负)')

        # 各股票表现
        for stock, data in self.stats['by_stock'].items():
            if data['win'] + data['loss'] > 0:
                wr = data['win'] / (data['win'] + data['loss'])
                insights.append(f'{stock}: 胜率{wr*100:.1f}% 净收益{data[pnl]:.2f}')

        # 规则有效性
        rules = []
        for rule, res in self.stats['rule_effectiveness'].items():
            total = res['win'] + res['loss']
            if total >= 3:
                wr = res['win'] / total
                rules.append((rule, wr, total))

        rules.sort(key=lambda x: -x[1])
        for rule, wr, total in rules[:5]:
            insights.append(f'规则「{rule}」胜率: {wr*100:.1f}% (样本{total})')

        # 每日收益趋势
        daily = self.stats['daily_pnl']
        if len(daily) >= 5:
            recent = list(daily.items())[-5:]
            avg = statistics.mean([v for _, v in recent])
            insights.append(f'最近5日均值: {avg:.0f}元')

        return insights

    def evolve_rules(self):
        # 基于交易统计自动调整规则
        changes = []
        rules_file = Path(r'F:\aidanao\second-brain\rules.md')
        rules_text = rules_file.read_text(encoding='utf-8') if rules_file.exists() else ''

        # 检查规则有效性
        for rule, res in self.stats['rule_effectiveness'].items():
            total = res['win'] + res['loss']
            if total >= 5:
                wr = res['win'] / total
                if wr < 0.3:
                    changes.append(f'【规则调整】{rule}胜率仅{wr*100:.0f}%，建议加强条件或暂停使用')
                    self.learnings.append({
                        'date': str(date.today()),
                        'type': 'rule_adjust',
                        'content': f'规则「{rule}」胜率{was:.0f}%低于30%，标记为低效',
                        'action': 'need_review'
                    })
                elif wr > 0.7:
                    changes.append(f'【规则强化】{rule}胜率{was:.0f}%，可考虑推广使用')

        # 分析最佳买卖时机
        if self.stats['daily_pnl']:
            days = sorted(self.stats['daily_pnl'].items(), key=lambda x: x[0])
            if len(days) >= 3:
                last_days = dict(days[-3:])
                for d, pnl in last_days.items():
                    changes.append(f'【每日复盘】{d}: 收益{pnl:.0f}元')

        self._save(self.learnings_file, self.learnings)
        log(f'evolve_rules: generated {len(changes)} suggestions')
        return changes

    def get_status(self):
        total = self.stats['total_trades']
        if total == 0:
            return '系统初始化中，暂无交易数据'
        wr = self.stats['win'] / total * 100
        pnl = self.stats['total_pnl']
        return f'总交易{total}笔 | 胜率{wr:.1f}% | 累计收益{pnl:.0f}元'

engine = EvolutionEngine()
