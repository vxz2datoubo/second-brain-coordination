"""
Spaced Repetition System - 间隔复习系统
基于艾宾浩斯遗忘曲线和 SM-2 算法
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

class SpacedRepetition:
    """
    间隔复习系统
    
    核心算法: SM-2 (SuperMemo 2)
    
    复习间隔:
    - 第1次复习: 1天后
    - 第2次复习: 6天后
    - 第3次复习: 间隔 * ease_factor
    - ...
    
    遗忘曲线: Ebbinghaus
    - 20分钟后: 遗忘58%
    - 1小时后: 遗忘44%
    - 8小时后: 遗忘36%
    - 1天后: 遗忘67%
    - 2天后: 遗忘72%
    - 6天后: 遗忘75%
    - 31天后: 遗忘79%
    """
    
    # 遗忘曲线关键点 (时间 -> 记忆保持率)
    FORGETTING_CURVE = {
        20 / 60: 0.42,      # 20分钟
        1: 0.56,            # 1小时
        8: 0.64,            # 8小时
        24: 0.33,           # 1天
        48: 0.28,           # 2天
        144: 0.25,          # 6天
        744: 0.21           # 31天
    }
    
    # 复习质量等级
    QUALITY_GRADES = {
        0: "完全不记得",
        1: "有印象但不记得",
        2: "记得但很困难",
        3: "需要一点提示",
        4: "记得但稍慢",
        5: "完全记得"
    }
    
    def __init__(self, base_path: str = "F:/aidanao/wisdom-brain"):
        self.base_path = Path(base_path)
        self.review_dir = self.base_path / "knowledge" / "reviews"
        self.review_dir.mkdir(parents=True, exist_ok=True)
        
        # 复习记录文件
        self.review_log_file = self.review_dir / "_review_log.json"
        self.schedule_file = self.review_dir / "_schedule.json"
        
        self._load_data()
    
    def _load_data(self):
        """加载复习数据"""
        # 复习日志
        if self.review_log_file.exists():
            with open(self.review_log_file, "r", encoding="utf-8-sig") as f:
                self.review_log = json.load(f)
        else:
            self.review_log = {
                "records": [],  # 每次复习的记录
                "by_node": {},  # 按节点索引
                "stats": {
                    "total_reviews": 0,
                    "total_correct": 0,
                    "avg_quality": 0
                }
            }
        
        # 复习计划
        if self.schedule_file.exists():
            with open(self.schedule_file, "r", encoding="utf-8-sig") as f:
                self.schedule = json.load(f)
        else:
            self.schedule = {
                "due_now": [],      # 现在需要复习的
                "due_today": [],    # 今天需要复习的
                "upcoming": {}      # 未来复习计划 {date: [node_ids]}
            }
    
    def _save_data(self):
        """保存复习数据"""
        with open(self.review_log_file, "w", encoding="utf-8") as f:
            json.dump(self.review_log, f, ensure_ascii=False, indent=2)
        
        with open(self.schedule_file, "w", encoding="utf-8") as f:
            json.dump(self.schedule, f, ensure_ascii=False, indent=2)
    
    def calculate_sm2(self, quality: int, n: int, ef: float, interval: int) -> Dict:
        """
        SM-2 算法计算
        
        参数:
        - quality: 回忆质量 0-5
        - n: 复习次数
        - ef: 简单因子 (ease factor)
        - interval: 前一次间隔(天)
        
        返回:
        - next_interval: 下次复习间隔(天)
        - next_ef: 新的简单因子
        - next_review: 下次复习时间
        """
        # 计算新的简单因子
        new_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(1.3, new_ef)  # 最低1.3
        
        # 计算间隔
        if quality < 3:
            # 失败: 从头开始
            next_interval = 1
        elif n == 0:
            next_interval = 1
        elif n == 1:
            next_interval = 6
        else:
            next_interval = int(interval * new_ef)
        
        # 限制最大间隔
        next_interval = min(next_interval, 365)  # 最多一年
        
        # 计算下次复习时间
        next_review = datetime.now() + timedelta(days=next_interval)
        
        return {
            "interval": next_interval,
            "ease_factor": round(new_ef, 2),
            "next_review": next_review.isoformat(),
            "repetitions": n + 1 if quality >= 3 else 0
        }
    
    def record_review(self, node_id: str, quality: int, 
                     current_ef: float = 2.5,
                     current_interval: int = 1,
                     review_count: int = 0) -> Dict:
        """
        记录一次复习
        
        参数:
        - node_id: 节点ID
        - quality: 回忆质量 0-5
        - current_ef: 当前简单因子
        - current_interval: 当前复习间隔
        - review_count: 已复习次数
        """
        # 计算 SM-2
        result = self.calculate_sm2(
            quality=quality,
            n=review_count,
            ef=current_ef,
            interval=current_interval
        )
        
        # 记录复习
        record = {
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
            "quality": quality,
            "grade_text": self.QUALITY_GRADES.get(quality, "未知"),
            "new_interval": result["interval"],
            "new_ef": result["ease_factor"],
            "next_review": result["next_review"],
            "repetitions": result["repetitions"]
        }
        
        # 添加到日志
        self.review_log["records"].append(record)
        
        # 更新节点索引
        if node_id not in self.review_log["by_node"]:
            self.review_log["by_node"][node_id] = []
        self.review_log["by_node"][node_id].append(record)
        
        # 更新统计
        self.review_log["stats"]["total_reviews"] += 1
        if quality >= 3:
            self.review_log["stats"]["total_correct"] += 1
        
        # 更新计划
        self._update_schedule(node_id, result["next_review"])
        
        # 保存
        self._save_data()
        
        return result
    
    def _update_schedule(self, node_id: str, next_review: str):
        """更新复习计划"""
        # 从"现在复习"移除
        if node_id in self.schedule["due_now"]:
            self.schedule["due_now"].remove(node_id)
        if node_id in self.schedule["due_today"]:
            self.schedule["due_today"].remove(node_id)
        
        # 添加到未来计划
        review_date = datetime.fromisoformat(next_review).date().isoformat()
        
        if review_date not in self.schedule["upcoming"]:
            self.schedule["upcoming"][review_date] = []
        
        if node_id not in self.schedule["upcoming"][review_date]:
            self.schedule["upcoming"][review_date].append(node_id)
    
    def get_due_nodes(self) -> Dict[str, List[str]]:
        """
        获取需要复习的节点
        """
        self._refresh_schedule()
        
        return {
            "overdue": self.schedule["due_now"],
            "due_today": self.schedule["due_today"]
        }
    
    def _refresh_schedule(self):
        """刷新复习计划"""
        now = datetime.now()
        today = now.date().isoformat()
        
        # 检查过期的
        for date_str, node_ids in list(self.schedule["upcoming"].items()):
            review_date = datetime.fromisoformat(date_str).date()
            
            if review_date <= now.date():
                # 过期了
                for node_id in node_ids:
                    if review_date < now.date():
                        self.schedule["due_now"].append(node_id)
                    else:
                        self.schedule["due_today"].append(node_id)
                
                # 从 upcoming 移除
                del self.schedule["upcoming"][date_str]
        
        # 去重
        self.schedule["due_now"] = list(set(self.schedule["due_now"]))
        self.schedule["due_today"] = list(set(self.schedule["due_today"]))
        
        self._save_data()
    
    def get_review_stats(self, node_id: str = None) -> Dict:
        """
        获取复习统计
        """
        if node_id:
            records = self.review_log["by_node"].get(node_id, [])
            if not records:
                return {"message": "No review history"}
            
            total = len(records)
            correct = sum(1 for r in records if r["quality"] >= 3)
            avg_quality = sum(r["quality"] for r in records) / total
            avg_interval = sum(r["new_interval"] for r in records) / total
            
            return {
                "node_id": node_id,
                "total_reviews": total,
                "correct_rate": round(correct / total, 2) if total > 0 else 0,
                "avg_quality": round(avg_quality, 2),
                "avg_interval": round(avg_interval, 1),
                "last_review": records[-1]["timestamp"] if records else None,
                "last_quality": records[-1]["quality"] if records else None
            }
        else:
            return self.review_log["stats"]
    
    def predict_forgetting(self, node_id: str, hours_ahead: int = 24) -> Dict:
        """
        预测遗忘曲线
        """
        records = self.review_log["by_node"].get(node_id, [])
        if not records:
            return {"message": "No review data"}
        
        last_review = records[-1]
        last_time = datetime.fromisoformat(last_review["timestamp"])
        quality = last_review["quality"]
        
        # 基于上次复习后经过的时间预测记忆保持率
        predictions = {}
        for hours in range(0, hours_ahead + 1, 4):
            check_time = last_time + timedelta(hours=hours)
            hours_passed = (check_time - last_time).total_seconds() / 3600
            
            # 根据遗忘曲线计算保持率
            # 简单模型: 基于上次复习质量调整
            retention = self._calculate_retention(hours_passed, quality)
            predictions[f"{hours}h"] = round(retention, 3)
        
        return {
            "node_id": node_id,
            "last_review": last_review["timestamp"],
            "predictions": predictions
        }
    
    def _calculate_retention(self, hours: float, quality: int) -> float:
        """
        计算在特定时间点的记忆保持率
        """
        # 质量影响遗忘速度
        quality_factor = 1 + (quality - 3) * 0.1
        
        # 基础遗忘曲线 (简化版)
        # 使用指数衰减模型
        import math
        
        # 半衰期约1天
        half_life = 24  # 小时
        retention = math.exp(-0.693 * hours / (half_life * quality_factor))
        
        return max(0.1, min(1.0, retention))
    
    def get_learning_curve(self, node_id: str) -> Dict:
        """
        获取学习曲线数据
        """
        records = self.review_log["by_node"].get(node_id, [])
        if len(records) < 2:
            return {"message": "Not enough data"}
        
        curve = []
        cumulative_correct = 0
        
        for i, record in enumerate(records):
            if record["quality"] >= 3:
                cumulative_correct += 1
            
            curve.append({
                "review_num": i + 1,
                "quality": record["quality"],
                "interval": record["new_interval"],
                "cumulative_correct_rate": round(cumulative_correct / (i + 1), 2)
            })
        
        return {
            "node_id": node_id,
            "curve": curve,
            "total_reviews": len(records)
        }
    
    def get_recommended_review_order(self) -> List[str]:
        """
        获取推荐的复习顺序
        基于: 遗忘风险 > 重要度 > 上次复习时间
        """
        # 获取所有需要复习的节点
        due = self.get_due_nodes()
        all_due = due["overdue"] + due["due_today"]
        
        if not all_due:
            return []
        
        # 简单的优先级排序
        # 1. 过期的优先
        # 2. 重要度高的优先
        # 3. 复习间隔长的优先
        
        priorities = []
        for node_id in all_due:
            priority = 0
            
            if node_id in due["overdue"]:
                priority += 100  # 过期的最高优先级
            
            # TODO: 接入 KnowledgeNode 获取重要度
            
            priorities.append((node_id, priority))
        
        # 排序
        priorities.sort(key=lambda x: x[1], reverse=True)
        
        return [node_id for node_id, _ in priorities]
    
    def generate_review_schedule(self, days: int = 7) -> Dict:
        """
        生成未来N天的复习计划
        """
        schedule = {}
        now = datetime.now()
        
        for day in range(days):
            date = (now + timedelta(days=day)).date().isoformat()
            
            if date in self.schedule["upcoming"]:
                schedule[date] = {
                    "count": len(self.schedule["upcoming"][date]),
                    "node_ids": self.schedule["upcoming"][date]
                }
            else:
                schedule[date] = {"count": 0, "node_ids": []}
        
        return schedule
    
    def get_stats(self) -> Dict:
        """获取复习统计概览"""
        total_reviews = self.review_log["stats"]["total_reviews"]
        total_correct = self.review_log["stats"]["total_correct"]
        
        return {
            "total_reviews": total_reviews,
            "correct_rate": round(total_correct / total_reviews, 2) if total_reviews > 0 else 0,
            "due_now": len(self.schedule["due_now"]),
            "due_today": len(self.schedule["due_today"]),
            "upcoming_count": sum(len(ids) for ids in self.schedule["upcoming"].values()),
            "unique_nodes_reviewed": len(self.review_log["by_node"])
        }


# 测试
if __name__ == "__main__":
    sr = SpacedRepetition()
    
    # 模拟复习
    print("=== SM-2 Algorithm Test ===")
    
    result = sr.calculate_sm2(quality=4, n=0, ef=2.5, interval=1)
    print(f"First review (quality=4): interval={result['interval']} days, EF={result['ease_factor']}")
    
    result = sr.calculate_sm2(quality=5, n=1, ef=result["ease_factor"], interval=result["interval"])
    print(f"Second review (quality=5): interval={result['interval']} days, EF={result['ease_factor']}")
    
    result = sr.calculate_sm2(quality=3, n=2, ef=result["ease_factor"], interval=result["interval"])
    print(f"Third review (quality=3): interval={result['interval']} days, EF={result['ease_factor']}")
    
    # 统计
    print("\n=== Stats ===")
    print(sr.get_stats())