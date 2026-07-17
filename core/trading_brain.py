"""
trading_brain.py — 交易知识库专用模块
集成到第二大脑，提供交易决策支持
"""
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict


class TradingBrain:
    """交易知识库核心类
    
    提供：
    - 规则查询
    - 教训检索
    - 决策前自检
    - 信号评分辅助
    - 市场状态判断
    """
    
    # 交易分类
    CATEGORIES = {
        "trading-rules": "交易规则",
        "decision-lessons": "决策教训",
        "market-analysis": "市场分析",
        "stock-knowledge": "股票知识",
        "strategy": "策略",
        "risk-management": "风险管理",
    }
    
    # 股票信息
    STOCKS = {
        "300418": {"name": "昆仑万维", "concept": "AI+游戏", "weight": 0.6},
        "300058": {"name": "蓝色光标", "concept": "营销+AI", "weight": 0.4},
    }
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.rules_path = data_dir.parent / "second-brain" / "rules.md"
        self.lessons_path = data_dir.parent / "second-brain" / "lessons.md"
        self.log_path = data_dir.parent / "second-brain" / "daily_log.md"
        self.knowledge_graph_path = data_dir / "knowledge-graph.json"
        
    # ========== 规则查询 ==========
    def get_rules(self) -> Dict:
        """获取所有交易规则"""
        try:
            content = self.rules_path.read_text(encoding="utf-8")
            return {"success": True, "rules": self._parse_rules_md(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_rules_md(self, content: str) -> Dict:
        """解析规则Markdown"""
        rules = {
            "仓位管理": [],
            "买入规则": [],
            "卖出规则": [],
            "做T规则": [],
            "风控规则": [],
        }
        
        current_section = None
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("## "):
                current_section = line.replace("## ", "").strip()
            elif line.startswith("- [x]") or line.startswith("- "):
                rule_text = line.replace("- [x] ", "").replace("- ", "")
                if current_section and current_section in rules:
                    rules[current_section].append(rule_text)
        
        return rules
    
    def check_rule_violation(self, action: str, context: Dict) -> Dict:
        """检查是否违反规则
        
        Args:
            action: 操作类型 (buy/sell/hold)
            context: 上下文 (股票, 价格, 大盘状态等)
        """
        violations = []
        warnings = []
        
        stock = context.get("stock", "")
        price = context.get("price", 0)
        change_pct = context.get("change_pct", 0)
        market_trend = context.get("market_trend", "unknown")  # up/down/neutral
        time_of_day = context.get("time", "unknown")
        has_position = context.get("has_position", False)
        profit_pct = context.get("profit_pct", 0)
        
        # === 买入规则检查 ===
        if action == "buy":
            # 大盘下跌禁止追高
            if market_trend == "down" and change_pct > 1:
                violations.append("大盘下跌趋势禁止追高买入")
            
            # 开盘30分钟内禁止（除非已有持仓做T）
            if "09:3" <= time_of_day <= "09:59" and not has_position:
                violations.append("开盘30分钟内禁止买入（除非已有持仓做T）")
            
            # 跌幅超5%禁止补仓
            if has_position and change_pct < -5:
                violations.append("持仓当日跌幅超5%禁止补仓")
            
            # 跌幅超7%必须检查止损
            if has_position and change_pct < -7:
                warnings.append("跌幅超7%必须检查是否止损")
            
            # 涨停次日不追高
            if context.get("yesterday_limit_up", False):
                violations.append("涨停板次日不追高")
            
            # 追涨次日只卖不买
            if context.get("yesterday_rally", False):
                violations.append("追涨次日只卖不买")
        
        # === 卖出规则检查 ===
        elif action == "sell":
            # 大盘大跌禁止恐慌性卖出
            if market_trend == "down" and change_pct < -2:
                warnings.append("大盘大跌禁止恐慌性卖出，注意是否应该等待")
            
            # 盈利未达2%禁止卖出
            if profit_pct < 2 and not context.get("stop_loss", False):
                violations.append("盈利未达2%禁止卖出（除非止损）")
            
            # 卖出后30分钟内禁止接回
            last_sell_time = context.get("last_sell_time")
            if last_sell_time:
                time_diff = datetime.now() - last_sell_time
                if time_diff < timedelta(minutes=30):
                    violations.append("卖出后30分钟内禁止接回")
            
            # 连续3日下跌才考虑止损
            consecutive_down = context.get("consecutive_down_days", 0)
            if consecutive_down < 3 and context.get("is_stop_loss", False):
                warnings.append("连续3日下跌才考虑止损，当前仅连续下跌{}日".format(consecutive_down))
        
        return {
            "action": action,
            "violations": violations,
            "warnings": warnings,
            "can_proceed": len(violations) == 0,
            "risk_level": "HIGH" if violations else ("MEDIUM" if warnings else "LOW")
        }
    
    # ========== 教训检索 ==========
    def get_lessons(self, stock: Optional[str] = None) -> List[Dict]:
        """获取历史教训"""
        try:
            content = self.lessons_path.read_text(encoding="utf-8")
            lessons = self._parse_lessons_md(content)
            
            if stock:
                lessons = [l for l in lessons if stock in l.get("content", "")]
            
            return lessons
        except Exception as e:
            return []
    
    def _parse_lessons_md(self, content: str) -> List[Dict]:
        """解析教训Markdown"""
        lessons = []
        current_date = ""
        
        for line in content.split("\n"):
            line = line.strip()
            
            if line.startswith("## 教训:"):
                current_date = line.replace("## 教训: ", "").strip()
            elif line.startswith("## 正向"):
                current_date = ""
            elif line.startswith("教训:") and current_date:
                lesson_text = line.replace("教训:", "").strip()
                lessons.append({
                    "type": "negative",
                    "date": current_date,
                    "lesson": lesson_text
                })
            elif line.startswith("## 教训") or line.startswith("现象:"):
                pass  # 忽略
            elif line.startswith("教训:") and not current_date:
                lessons.append({
                    "type": "negative",
                    "lesson": line.replace("教训:", "").strip()
                })
        
        return lessons
    
    def search_lessons(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索相关教训"""
        all_lessons = self.get_lessons()
        query_lower = query.lower()
        
        scored = []
        for lesson in all_lessons:
            content = (lesson.get("lesson", "") + lesson.get("content", "")).lower()
            score = 0
            
            # 关键词匹配
            for keyword in query_lower.split():
                if keyword in content:
                    score += 1
            
            if score > 0:
                scored.append((score, lesson))
        
        scored.sort(key=lambda x: -x[0])
        return [l for _, l in scored[:limit]]
    
    # ========== 决策前自检 ==========
    def pre_decision_check(self, decision: str, context: Dict) -> Dict:
        """决策前自动检查
        
        Args:
            decision: 决策描述，如"在开盘追高买入昆仑"
            context: 上下文信息
        """
        # 解析决策类型
        action = "buy" if "买入" in decision or "买" in decision else \
                 "sell" if "卖出" in decision or "卖" in decision else "hold"
        
        # 检查规则违反
        rule_check = self.check_rule_violation(action, context)
        
        # 搜索相关教训
        related_lessons = self.search_lessons(decision, limit=3)
        
        # 生成警告
        warnings = []
        if rule_check["violations"]:
            warnings.append(f"🚨 违反规则: {', '.join(rule_check['violations'])}")
        
        if rule_check["warnings"]:
            warnings.append(f"⚠️ 警告: {', '.join(rule_check['warnings'])}")
        
        for lesson in related_lessons:
            warnings.append(f"📚 历史教训: {lesson.get('lesson', '')[:100]}")
        
        # 建议
        suggestions = []
        if rule_check["violations"]:
            suggestions.append("建议取消当前操作")
        elif rule_check["warnings"]:
            suggestions.append("谨慎操作，密切观察")
        else:
            suggestions.append("当前操作符合规则")
        
        # 判断是否有红线教训
        has_red_line = any("禁止" in v for v in rule_check["violations"])
        
        return {
            "decision": decision,
            "action": action,
            "can_proceed": not rule_check["violations"],
            "risk_level": rule_check["risk_level"],
            "rule_violations": rule_check["violations"],
            "rule_warnings": rule_check["warnings"],
            "related_lessons": related_lessons,
            "warnings": warnings,
            "suggestions": suggestions,
            "has_red_line_lesson": has_red_line,
            "check_timestamp": datetime.now().isoformat()
        }
    
    # ========== 日志管理 ==========
    def add_daily_log(self, log_entry: Dict) -> Dict:
        """添加每日交易日志"""
        try:
            date = datetime.now().strftime("%Y-%m-%d")
            lines = [
                f"\n### {date}",
                f"**市场状态**: {log_entry.get('market_status', '待记录')}",
                f"**大盘情绪**: {log_entry.get('market_sentiment', '待观察')}",
                "",
                f"**昆仑万维(300418)**",
                f"- 开盘: {log_entry.get('kunlun_open', '待记录')}",
                f"- 收盘: {log_entry.get('kunlun_close', '待记录')}",
                f"- 涨跌: {log_entry.get('kunlun_change', '待记录')}",
                f"- 交易: {log_entry.get('kunlun_trades', '待记录')}",
                f"- T仓次数: {log_entry.get('kunlun_t_count', 0)}笔",
                f"- 当日盈亏: {log_entry.get('kunlun_pnl', '待计算')}",
                "",
                f"**蓝色光标(300058)**",
                f"- 开盘: {log_entry.get('blue_open', '待记录')}",
                f"- 收盘: {log_entry.get('blue_close', '待记录')}",
                f"- 涨跌: {log_entry.get('blue_change', '待记录')}",
                f"- 交易: {log_entry.get('blue_trades', '待记录')}",
                f"- T仓次数: {log_entry.get('blue_t_count', 0)}笔",
                f"- 当日盈亏: {log_entry.get('blue_pnl', '待计算')}",
                "",
                "---",
                f"**日总结**: {log_entry.get('summary', '待记录')}",
                f"**教训与经验**: {log_entry.get('lessons', '待记录')}",
                f"**明日计划**: {log_entry.get('tomorrow_plan', '待记录')}",
                "",
            ]
            
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            return {"success": True, "date": date}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_recent_logs(self, days: int = 7) -> List[Dict]:
        """获取近期日志"""
        try:
            content = self.log_path.read_text(encoding="utf-8")
            logs = []
            
            for line in content.split("\n"):
                if line.startswith("### 20"):
                    date = line.replace("### ", "").strip()
                    logs.append({"date": date})
            
            return logs[-days:]
        except Exception as e:
            return []
    
    # ========== 信号辅助 ==========
    def get_signal_context(self, stock: str) -> Dict:
        """获取信号评分上下文"""
        stock_info = self.STOCKS.get(stock, {})
        
        return {
            "stock": stock,
            "stock_name": stock_info.get("name", ""),
            "concept": stock_info.get("concept", ""),
            "priority": "HIGH" if stock == "300418" else "MEDIUM",
            "relevant_lessons": self.get_lessons(stock)[:3],
            "rules_summary": self._get_stock_rules(stock),
        }
    
    def _get_stock_rules(self, stock: str) -> Dict:
        """获取股票特定规则"""
        base_rules = {
            "单笔金额": "5000元",
            "日T仓上限": "3笔",
            "止损线": "单笔亏损>1%无条件平仓",
            "熔断线": "日亏>2%全天停止",
        }
        
        if stock == "300418":
            base_rules.update({
                "风格": "趋势跟随",
                "止损时间": "40分钟",
                "最低止盈": "0.3%",
                "贪心止盈": "0.6%",
            })
        elif stock == "300058":
            base_rules.update({
                "风格": "逆势抄底",
                "止损时间": "50分钟",
                "最低止盈": "0.4%",
                "贪心止盈": "0.8%",
            })
        
        return base_rules
    
    # ========== 市场状态 ==========
    def judge_market_regime(self, market_data: Dict) -> Dict:
        """判断市场状态"""
        index_change = market_data.get("index_change", 0)
        up_count = market_data.get("up_count", 0)
        down_count = market_data.get("down_count", 0)
        volatility = market_data.get("volatility", "medium")
        
        # 判断趋势
        if index_change > 1.5:
            trend = "TREND_UP"
        elif index_change < -1.5:
            trend = "TREND_DOWN"
        else:
            trend = "RANGE"
        
        # 判断波动性
        if volatility == "high":
            regime = f"HIGH_VOL_{trend}"
        elif volatility == "low":
            regime = "LOW_VOL_RANGE"
        else:
            regime = f"{trend}"
        
        # 判断上涨/下跌家数
        if up_count > down_count * 1.2:
            sentiment = "做多"
        elif down_count > up_count * 1.2:
            sentiment = "做空"
        else:
            sentiment = "观望"
        
        # 极端行情判断
        if abs(index_change) > 3:
            regime = "EXTREME"
        
        return {
            "regime": regime,
            "trend": trend,
            "sentiment": sentiment,
            "recommendations": self._get_regime_recommendations(regime)
        }
    
    def _get_regime_recommendations(self, regime: str) -> List[str]:
        """获取状态对应建议"""
        recommendations = {
            "TREND_UP": ["减少做T，持有底仓", "优先买入，谨慎卖出"],
            "TREND_DOWN": ["倒T为主，控制仓位", "优先卖出，减少新开仓"],
            "HIGH_VOL_RANGE": ["做T黄金期", "积极操作，把握波动"],
            "LOW_VOL_RANGE": ["减少操作", "仅强信号执行"],
            "EXTREME": ["全天停止", "所有仓位平掉"],
        }
        return recommendations.get(regime, ["观望为主"])
    
    # ========== 统计 ==========
    def get_stats(self) -> Dict:
        """获取交易知识库统计"""
        try:
            # 规则统计
            rules = self._parse_rules_md(self.rules_path.read_text(encoding="utf-8"))
            rules_count = sum(len(v) for v in rules.values())
            
            # 教训统计
            lessons = self._parse_lessons_md(self.lessons_path.read_text(encoding="utf-8"))
            lessons_count = len(lessons)
            
            # 日志统计
            logs = self.get_recent_logs(days=30)
            
            return {
                "total_rules": rules_count,
                "total_lessons": lessons_count,
                "recent_trading_days": len(logs),
                "categories": list(self.CATEGORIES.values()),
                "stocks": list(self.STOCKS.keys()),
                "last_updated": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}


# 全局实例
_trading_brain = None

def get_trading_brain(data_dir: Path):
    """获取交易知识库实例"""
    global _trading_brain
    if _trading_brain is None:
        _trading_brain = TradingBrain(data_dir)
    return _trading_brain
