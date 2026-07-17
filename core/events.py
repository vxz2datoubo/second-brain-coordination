"""
events.py - 事件引擎 (Jarvis 模式)
自动提取时间事件、判断重要性、检测冲突、计时器管理、智能建议

功能:
- 自然语言事件提取 (日期/时间/人物/地点)
- 重要性自动判断 (语义分析)
- 时间冲突检测
- 计时器管理 (煲汤/睡觉等)
- 跨知识库智能建议
"""
import json
import re
import uuid
import calendar
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


class EventEngine:
    """事件引擎 — Jarvis 模式核心"""

    IMPORTANCE_KEYWORDS = {
        5: ["约会", "面试", "客户", "合同", "交付", "汇款", "结婚", "葬礼", "开庭", "签证"],
        4: ["旅游", "出差", "会议", "开会", "看病", "签字", "签约", "航班", "火车", "医院", "手术"],
        3: ["聚会", "聚餐", "生日", "纪念日", "体检", "保养", "年检"],
        2: ["吃饭", "买菜", "取快递", "充电", "洗衣", "打扫", "购物"],
        1: ["看看", "试试", "随便", "好奇", "玩玩"],
    }

    TIMER_KEYWORDS = {
        "煮": 15, "煲": 20, "炖": 30, "蒸": 15, "烤": 25,
        "睡": 60, "休息": 30, "充电": 60, "洗": 40, "泡": 15,
    }

    DEFAULT_DURATIONS = {
        "social": 180,
        "travel": 1440,
        "business": 90,
        "health": 120,
        "career": 120,
        "finance": 60,
        "cooking": 30,
        "rest": 60,
        "reminder": 60,
    }

    def __init__(self, data_dir: Path, graph=None, memory=None):
        self.data_dir = data_dir
        self.path = data_dir / "events.json"
        self.graph = graph
        self.memory = memory
        self.events = self._load()

    def _load(self) -> list[dict]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.events, f, ensure_ascii=False, indent=2)

    # ========== 自然语言提取 ==========
    def extract(self, text: str) -> list[dict]:
        """从自然语言中提取事件。返回事件列表，每个事件含 extracted 字段。"""
        extracted = []
        now = datetime.now()

        # 1. 提取日期
        dates = self._extract_dates(text, now)

        # 2. 提取时间
        times = self._extract_times(text)

        # 3. 提取人物
        people = self._extract_people(text)

        # 4. 提取地点
        locations = self._extract_locations(text)

        # 5. 判定事件类型
        event_type = self._classify_event(text)

        # 6. 组装事件
        for d in dates:
            duration = self._estimate_duration(text, event_type)
            event = {
                "id": str(uuid.uuid4())[:8],
                "text": text[:200],
                "date": d,
                "time": times[0] if times else None,
                "duration_minutes": duration,
                "end_time": self._end_time(times[0], duration) if times else None,
                "all_day": not bool(times),
                "people": people,
                "location": locations[0] if locations else "",
                "type": event_type,
                "importance": self._judge_importance(text),
                "status": "pending",
                "context_ids": [],
                "reminders_sent": 0,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            extracted.append(event)

        # 7. 检测计时器
        timer = self._extract_timer(text, now)
        if timer:
            timer["type"] = "timer"
            extracted.append(timer)

        # 如果没提取到日期但有事件意图，创建一个待解析事件
        if not extracted and event_type != "unknown":
            extracted.append({
                "id": str(uuid.uuid4())[:8],
                "text": text[:200],
                "date": None,
                "time": times[0] if times else None,
                "duration_minutes": self._estimate_duration(text, event_type),
                "end_time": self._end_time(times[0], self._estimate_duration(text, event_type)) if times else None,
                "all_day": not bool(times),
                "people": people,
                "location": locations[0] if locations else "",
                "type": event_type,
                "importance": self._judge_importance(text),
                "status": "pending_date",
                "context_ids": [],
                "reminders_sent": 0,
                "created_at": now.isoformat(),
            })

        return extracted

    def _extract_dates(self, text: str, now: datetime) -> list[str]:
        """提取日期。支持: 今天/明天/后天/下周一/15号/6月15日/2026-06-15"""
        dates = []

        if "今天" in text:
            dates.append(now.strftime("%Y-%m-%d"))
        if "明天" in text:
            dates.append((now + timedelta(days=1)).strftime("%Y-%m-%d"))
        if "后天" in text:
            dates.append((now + timedelta(days=2)).strftime("%Y-%m-%d"))
        if "大后天" in text:
            dates.append((now + timedelta(days=3)).strftime("%Y-%m-%d"))

        # 星期几
        weekdays = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6,
                     "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3, "星期五": 4, "星期六": 5, "星期日": 6}
        for wd, target in weekdays.items():
            if f"下{wd}" in text:
                days_ahead = (target - now.weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                dates.append((now + timedelta(days=days_ahead)).strftime("%Y-%m-%d"))

        # X号 / X日
        for m in re.finditer(r'(\d{1,2})[号日]', text):
            day = int(m.group(1))
            if 1 <= day <= 31:
                dates.append(self._safe_date(now.year, now.month, day))

        # X月Y号 / X月Y日
        for m in re.finditer(r'(\d{1,2})月(\d{1,2})[号日]?', text):
            month = int(m.group(1))
            day = int(m.group(2))
            year = now.year
            if month < now.month:
                year += 1
            dates.append(self._safe_date(year, month, day))

        # 下月X号
        for m in re.finditer(r'下月(\d{1,2})[号日]', text):
            day = int(m.group(1))
            next_month = now.replace(day=1) + timedelta(days=32)
            dates.append(self._safe_date(next_month.year, next_month.month, day))

        # ISO日期
        for m in re.finditer(r'(\d{4}-\d{2}-\d{2})', text):
            dates.append(m.group(1))

        return list(set(dates))

    @staticmethod
    def _safe_date(year: int, month: int, day: int) -> str:
        if not (1 <= month <= 12):
            month = 1
        last = calendar.monthrange(year, month)[1]
        return datetime(year, month, min(max(day, 1), last)).strftime("%Y-%m-%d")

    def _extract_times(self, text: str) -> list[str]:
        """提取时间。支持: 3点/下午2点/14:30/半小时后"""
        times = []
        for m in re.finditer(r'(\d{1,2})[点:：](\d{2})?', text):
            hour = int(m.group(1))
            minute = int(m.group(2)) if m.group(2) else 0
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                times.append(f"{hour:02d}:{minute:02d}")
        # 上午/下午修正
        if "下午" in text and times:
            h = int(times[0][:2])
            if h < 12:
                times[0] = f"{h+12:02d}:{times[0][3:]}"
        return times

    def _estimate_duration(self, text: str, event_type: str) -> int:
        m = re.search(r'(\d+)\s*(分钟|小时|个?钟|天)', text)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            if unit == "分钟":
                return n
            if unit == "天":
                return n * 1440
            return n * 60
        if any(w in text for w in ["全天", "一整天", "整天"]):
            return 1440
        return self.DEFAULT_DURATIONS.get(event_type, 60)

    @staticmethod
    def _end_time(start: str, duration_minutes: int) -> Optional[str]:
        if not start:
            return None
        h, m = [int(x) for x in start.split(":")]
        total = h * 60 + m + duration_minutes
        return f"{(total // 60) % 24:02d}:{total % 60:02d}"

    @staticmethod
    def _time_range(event: dict) -> Optional[tuple[int, int]]:
        start = event.get("time")
        if not start:
            return None
        h, m = [int(x) for x in start.split(":")]
        start_min = h * 60 + m
        return start_min, start_min + int(event.get("duration_minutes") or 60)

    def _extract_people(self, text: str) -> list[str]:
        """简易人物提取。后续可接知识库中的联系人。"""
        people = []
        for m in re.finditer(r'(?:和|跟|找|见)([\u4e00-\u9fff]{1,4})(?=[有在去到吃饭见约，。,\s]|$)', text):
            name = re.sub(r'(有个|有|个)$', '', m.group(1))
            if name not in ["我们", "他们", "大家", "自己", "明天", "后天"]:
                people.append(name)
        for m in re.finditer(r'约(?:了)?([\u4e00-\u9fff]{1,4})(?=[有在去到吃饭见，。,\s]|$)', text):
            name = re.sub(r'(有个|有|个)$', '', m.group(1))
            if name not in ["会", "我们", "他们", "大家", "自己", "明天", "后天"]:
                people.append(name)
        return list(dict.fromkeys(people))

    def _extract_locations(self, text: str) -> list[str]:
        """简易地点提取"""
        locs = []
        for m in re.finditer(r'(在|去|到|往)([\u4e00-\u9fff]{2,6})(?=[的了吃饭，。\s]|$)', text):
            loc = re.sub(r'(吃饭|吃|饭)$', '', m.group(2))
            if loc:
                locs.append(loc)
        return locs[:3]

    def _classify_event(self, text: str) -> str:
        """事件分类"""
        if any(w in text for w in ["约会", "聚会", "见面", "约了", "吃饭"]):
            return "social"
        if any(w in text for w in ["出差", "旅游", "航班", "火车", "酒店"]):
            return "travel"
        if any(w in text for w in ["客户", "合同", "开会", "会议", "提案"]):
            return "business"
        if any(w in text for w in ["看病", "体检", "医院", "手术", "药"]):
            return "health"
        if any(w in text for w in ["面试", "简历", "入职"]):
            return "career"
        if any(w in text for w in ["煮", "煲", "炖", "烤", "蒸"]):
            return "cooking"
        if any(w in text for w in ["睡", "休息", "躺"]):
            return "rest"
        if any(w in text for w in ["股票", "买入", "卖出", "盯盘"]):
            return "finance"
        return "reminder"

    def _judge_importance(self, text: str) -> int:
        """自动判断重要性 1-5"""
        for level in [5, 4, 3, 2, 1]:
            for kw in self.IMPORTANCE_KEYWORDS[level]:
                if kw in text:
                    return level
        return 2  # 默认中等

    def _extract_timer(self, text: str, now: datetime) -> Optional[dict]:
        """检测计时器。如「煲汤15分钟」「睡一会儿」"""
        for action, default_minutes in self.TIMER_KEYWORDS.items():
            if action in text:
                # 尝试提取具体时间
                duration = default_minutes
                m = re.search(r'(\d+)\s*(分钟|小时|个?钟)', text)
                if m:
                    n = int(m.group(1))
                    duration = n * 60 if m.group(2) in ("小时", "钟", "个钟") else n
                expire_at = (now + timedelta(minutes=duration)).isoformat()
                return {
                    "id": str(uuid.uuid4())[:8],
                    "text": f"计时器: {action} ({duration}分钟)",
                    "type": "timer",
                    "action": action,
                    "duration_minutes": duration,
                    "expire_at": expire_at,
                    "importance": 3,
                    "status": "active",
                    "created_at": now.isoformat(),
                }
        return None

    # ========== 事件管理 ==========
    def record(self, text: str) -> list[dict]:
        """录入事件（自动提取+存储）。返回所有提取到的事件。"""
        extracted = self.extract(text)
        if not extracted:
            return []

        for event in extracted:
            # 去重: 同一天同类型不重复
            if event.get("date"):
                dup = False
                for e in self.events:
                    if e.get("date") == event["date"] and e.get("type") == event.get("type"):
                        dup = True
                        break
                if dup:
                    continue
            # 计时器去重
            if event.get("type") == "timer":
                dup = False
                for e in self.events:
                    if e.get("type") == "timer" and e.get("action") == event.get("action"):
                        dup = True
                        break
                if dup:
                    continue

            self.events.append(event)

        self._save()
        return extracted

    def check(self, date: str = None) -> list[dict]:
        """检查某日事件。默认今天。"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return [e for e in self.events if e.get("date") == date]

    def conflicts(self) -> list[dict]:
        """检测所有时间冲突 (7种类型)

        1. time_overlap    — 精确时间重叠
        2. same_day        — 同日多事件
        3. adjacent        — 相邻高优先级
        4. commitment      — 承诺冲突 (同一个人/同类型安排过分密集)
        5. resource        — 资源冲突 (同地点/同人物/同设备)
        6. energy          — 精力过载 (高精力事件聚集)
        7. priority        — 优先级倒置 (低优先级挤占高优先级)
        """
        conflicts = []
        active = [e for e in self.events if e.get("status") in ("pending", "active", "confirmed")]
        dates = {}
        for e in active:
            d = e.get("date")
            if d:
                dates.setdefault(d, []).append(e)

        # ── 1. time_overlap: 精确时间重叠 ──
        for d, evts in dates.items():
            timed = [e for e in evts if self._time_range(e)]
            for i in range(len(timed)):
                for j in range(i + 1, len(timed)):
                    a, b = timed[i], timed[j]
                    ar, br = self._time_range(a), self._time_range(b)
                    if ar and br and max(ar[0], br[0]) < min(ar[1], br[1]):
                        conflicts.append({
                            "date": d,
                            "type": "time_overlap",
                            "severity": max(a.get("importance", 1), b.get("importance", 1)),
                            "events": [a, b],
                            "suggestion": f"{a.get('time')} 和 {b.get('time')} 的安排时间重叠，建议改期或确认是否同一件事",
                        })

        # ── 2. same_day: 同日多事件 ──
        for d, evts in dates.items():
            high = [e for e in evts if e.get("importance", 1) >= 4]
            if len(evts) >= 2 and (len(high) >= 1 or any(e.get("all_day") for e in evts)):
                conflicts.append({
                    "date": d,
                    "type": "same_day",
                    "severity": max(e.get("importance", 1) for e in evts),
                    "events": evts,
                    "suggestion": self._suggest_conflict(evts),
                })

        # ── 3. adjacent: 相邻高优先级 ──
        sorted_dates = sorted(dates.keys())
        for i in range(len(sorted_dates) - 1):
            d1, d2 = sorted_dates[i], sorted_dates[i + 1]
            try:
                dt1 = datetime.fromisoformat(d1)
                dt2 = datetime.fromisoformat(d2)
                gap_days = (dt2 - dt1).days
                if gap_days <= 1:
                    evts1, evts2 = dates[d1], dates[d2]
                    max_imp = max(
                        max((e.get("importance", 1) for e in evts1), default=1),
                        max((e.get("importance", 1) for e in evts2), default=1),
                    )
                    if max_imp >= 4:
                        types = {e.get("type", "") for e in evts1 + evts2}
                        suggestion = f"相邻日期有 {len(evts1)+len(evts2)} 个事件，注意时间管理"
                        if "travel" in types:
                            suggestion = "旅行前后相邻日期有高优先级安排，建议预留交通、行李、休息和迟到缓冲"
                        elif "social" in types and ("business" in types or "career" in types):
                            suggestion = "社交安排与工作/面试相邻，建议确认精力、通勤和准备时间"
                        conflicts.append({
                            "date_range": f"{d1} ~ {d2}",
                            "type": "adjacent",
                            "severity": max_imp,
                            "events": evts1 + evts2,
                            "suggestion": suggestion,
                        })
            except:
                pass

        # ── 4. commitment: 承诺冲突 (同人/同类型安排过于密集) ──
        # 检测 7 天窗口内同一类型事件 ≥3 个
        for i, e in enumerate(active):
            e_type = e.get("type", "")
            e_date_str = e.get("date", "")
            if not e_type or not e_date_str or e_type in ("timer", "reminder", "unknown"):
                continue
            try:
                e_dt = datetime.fromisoformat(e_date_str)
            except:
                continue
            window_end = e_dt + timedelta(days=7)
            same_type_window = []
            for other in active:
                if other is e:
                    continue
                if other.get("type") == e_type:
                    try:
                        od = datetime.fromisoformat(other.get("date", ""))
                        if e_dt <= od <= window_end:
                            same_type_window.append(other)
                    except:
                        pass
            if len(same_type_window) >= 2:  # e + 2 others = 3 in window
                conflicts.append({
                    "type": "commitment",
                    "severity": max(e.get("importance", 1), max((o.get("importance", 1) for o in same_type_window), default=1)),
                    "events": [e] + same_type_window,
                    "window_days": 7,
                    "event_type": e_type,
                    "suggestion": self._commitment_suggestion(e_type, len(same_type_window) + 1),
                })

        # ── 5. resource: 资源冲突 (同地点/同人物/同设备) ──
        for d, evts in dates.items():
            locations = [e.get("location", "") for e in evts if e.get("location")]
            if len(locations) != len(set(locations)):
                dup_loc = [loc for loc in locations if locations.count(loc) > 1]
                conflicts.append({
                    "date": d,
                    "type": "resource",
                    "severity": max(e.get("importance", 1) for e in evts),
                    "resource": "location",
                    "duplicates": list(set(dup_loc)),
                    "events": [e for e in evts if e.get("location") in dup_loc],
                    "suggestion": f"同一天在 {'、'.join(set(dup_loc))} 有多个安排，建议确认是否冲突或可以一并处理",
                })
            people = [e.get("people") for e in evts if e.get("people")]
            # Flatten people lists
            all_people = []
            for p in people:
                if isinstance(p, list):
                    all_people.extend(p)
            if len(all_people) != len(set(all_people)):
                dup_p = [p for p in all_people if all_people.count(p) > 1]
                conflicts.append({
                    "date": d,
                    "type": "resource",
                    "severity": max(e.get("importance", 1) for e in evts),
                    "resource": "people",
                    "duplicates": list(set(dup_p)),
                    "events": evts,
                    "suggestion": f"{'、'.join(set(dup_p))} 当天被多个事件引用，建议确认是否要协调",
                })

        # ── 6. energy: 精力过载 ──
        ENERGY_COST = {"business": 5, "career": 5, "social": 3, "travel": 4, "health": 3, "cooking": 2, "rest": 0, "reminder": 0}
        for d, evts in dates.items():
            total_energy = sum(ENERGY_COST.get(e.get("type", ""), 1) * e.get("importance", 1) for e in evts)
            if len(evts) >= 3 and total_energy >= 12:
                conflicts.append({
                    "date": d,
                    "type": "energy",
                    "severity": min(5, total_energy // 3),
                    "events": evts,
                    "energy_score": total_energy,
                    "suggestion": f"当天 {len(evts)} 个事件精力消耗大(评分{total_energy})，建议精简或拆分到其他日期",
                })

        # ── 7. priority: 优先级倒置 ──
        # 低优先级事件占据了高优先级事件的黄金时段
        for d, evts in dates.items():
            high_p = [e for e in evts if e.get("importance", 1) >= 4]
            low_p = [e for e in evts if e.get("importance", 1) <= 2 and e.get("time")]
            if high_p and low_p:
                # 如果低优先级有精确时间，高优先级没有，可能存在倒置
                for hp in high_p:
                    if not hp.get("time"):
                        conflicts.append({
                            "date": d,
                            "type": "priority",
                            "severity": max(e.get("importance", 1) for e in evts),
                            "events": [hp] + low_p,
                            "high_priority_event": hp,
                            "blocking_low_priority": low_p,
                            "suggestion": f"高优先级事件「{hp.get('text','')[:30]}」未设具体时间，低优先级事件已占时段，建议优先为重要事项预留时间",
                        })
                        break

        # 去重: 同一类型 + 同事件集合去重
        seen = set()
        unique = []
        for c in conflicts:
            key = (c["type"], tuple(sorted(e.get("id", "") for e in c.get("events", []))))
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return unique

    def _commitment_suggestion(self, event_type: str, count: int) -> str:
        """生成承诺冲突建议"""
        type_names = {
            "social": "社交", "business": "商务", "career": "工作",
            "travel": "旅行", "health": "健康", "cooking": "做饭",
        }
        name = type_names.get(event_type, event_type)
        if count >= 5:
            return f"7天内 {name} 类活动达 {count} 次，过于频繁容易疲劳，建议合并或减少"
        if count >= 3:
            return f"7天内 {name} 类活动 {count} 次，注意精力和时间分配"
        return f"{name} 类活动较密集，注意协调"

    def upcoming(self, days: int = 7) -> list[dict]:
        """未来N天内的事件"""
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        upcoming = []
        for e in self.events:
            if e.get("date"):
                try:
                    d = datetime.fromisoformat(e["date"])
                    if now <= d <= cutoff:
                        upcoming.append(e)
                except: pass
        upcoming.sort(key=lambda x: x.get("date", ""))
        return upcoming

    def active_timers(self) -> list[dict]:
        """活跃的计时器"""
        expired = []
        active = []
        now = datetime.now()
        for e in self.events:
            if e.get("type") != "timer":
                continue
            if e.get("expire_at"):
                try:
                    exp = datetime.fromisoformat(e["expire_at"])
                    if exp <= now:
                        expired.append(e)
                    else:
                        active.append(e)
                except: pass
            else:
                active.append(e)
        return {"active": active, "expired": expired}

    def _suggest_conflict(self, events: list[dict]) -> str:
        """生成冲突建议"""
        if not events:
            return "无建议"
        types = set(e.get("type", "") for e in events)
        max_imp = max(e.get("importance", 1) for e in events)
        if "social" in types and "travel" in types:
            return "约会和旅游日期相近，是否是一起的？如果不是，建议确认时间安排"
        if "social" in types and ("business" in types or "career" in types):
            return "社交安排和工作/面试安排在同一天，建议确认通勤、准备时间和精力是否够"
        if "business" in types and max_imp >= 4:
            return "有高优先级商务事件，建议优先处理"
        return f"同一天有 {len(events)} 个事件，注意时间分配"

    # ========== 综合提醒 ==========
    def remind(self) -> dict:
        """综合提醒: 近期事件 + 冲突 + 过期计时器"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        # 今日事件
        today_events = self.check(today)
        # 明日事件
        tomorrow_events = self.check(tomorrow)
        # 冲突
        conflict_list = self.conflicts()
        # 计时器
        timers = self.active_timers()
        # 未来
        upcoming_list = self.upcoming(7)

        # 生成提醒文本
        reminders = []
        if today_events:
            for e in today_events:
                reminders.append(f"今天: {e.get('text','')[:60]}")
        if timers.get("expired"):
            for e in timers["expired"]:
                reminders.append(f"⚠️ 计时器到期: {e.get('action','')} ({e.get('duration_minutes',0)}分钟前)")
        if conflict_list:
            reminders.append(f"冲突: {len(conflict_list)} 个时间冲突需要关注")
        if tomorrow_events:
            reminders.append(f"明天: {len(tomorrow_events)} 个事件")

        return {
            "today": today_events,
            "tomorrow": tomorrow_events,
            "conflicts": conflict_list,
            "timers": timers,
            "upcoming": upcoming_list,
            "reminders": reminders,
            "summary": " | ".join(reminders) if reminders else "近期无事件",
        }

    # ========== 统计 ==========
    def stats(self) -> dict:
        return {
            "total": len(self.events),
            "active": len([e for e in self.events if e.get("status") in ("pending", "active")]),
            "types": {t: len([e for e in self.events if e.get("type") == t])
                       for t in set(e.get("type", "") for e in self.events)},
        }

    # ========== 状态管理 (P2.8: 确认→更新闭环) ==========

    VALID_STATUSES = ("pending", "active", "confirmed", "cancelled", "rescheduled", "done", "expired")

    def update_status(self, event_id: str, new_status: str, note: str = "", resolve_conflicting: list[str] = None) -> dict:
        """P2.8: 更新事件状态。

        用途: 用户确认冲突后更新旧事件状态（如 cancelled/rescheduled），
        或确认新事件（confirmed）。

        Args:
            event_id: 事件 ID（或模糊文本搜索）
            new_status: 新状态 (confirmed | cancelled | rescheduled | done)
            note: 更新说明（如"用户确认已取消"）
            resolve_conflicting: 同批次需要一起更新的冲突事件 ID 列表

        Returns:
            {"updated": [...], "not_found": [...], "conflict_ids_resolved": [...]}
        """
        if new_status not in self.VALID_STATUSES:
            return {"error": f"Invalid status: {new_status}. Valid: {self.VALID_STATUSES}"}

        now = datetime.now().isoformat()
        updated = []
        not_found = []

        # 主事件 ID 查找
        target = self._find_event(event_id)
        if target is not None:
            self.events[target]["status"] = new_status
            self.events[target]["updated_at"] = now
            if note:
                self.events[target].setdefault("notes", []).append(
                    {"text": note, "timestamp": now}
                )
            updated.append(self.events[target])
        else:
            not_found.append(event_id)

        # 关联冲突事件批量更新
        resolved_ids = []
        if resolve_conflicting:
            for cid in resolve_conflicting:
                idx = self._find_event(cid)
                if idx is not None:
                    self.events[idx]["status"] = "cancelled"
                    self.events[idx]["updated_at"] = now
                    if note:
                        self.events[idx].setdefault("notes", []).append(
                            {"text": f"因冲突解决而取消: {note}", "timestamp": now}
                        )
                    updated.append(self.events[idx])
                    resolved_ids.append(cid)
                else:
                    not_found.append(cid)

        if updated:
            self._save()

        return {
            "updated": [{"id": e["id"], "text": e.get("text", "")[:80], "status": e["status"], "date": e.get("date")} for e in updated],
            "not_found": not_found,
            "conflict_ids_resolved": resolved_ids,
            "note": note,
        }

    def _find_event(self, event_id: str) -> Optional[int]:
        """按 ID 或文本模糊匹配查找事件索引"""
        for i, e in enumerate(self.events):
            if e.get("id") == event_id:
                return i
        # 模糊匹配: 文本中包含 event_id
        for i, e in enumerate(self.events):
            if event_id in e.get("text", ""):
                return i
        return None
