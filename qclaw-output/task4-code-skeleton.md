# QClaw 输出 | 2026-06-17 09:52
> 模型: openclaw/default | 端口: 1988 | Token: 0

```python
# ════════════════════════════════════════════════════════════
# 小樱花AI女友 - 5模块完整骨架实现
# 项目根目录：F:\ai\girlfriend\
# 技术栈：Python 3.13 stdlib + requests
# 大模型：WorkBuddy（localhost:8765 OpenAI兼容）
# 第二大脑：F:\ai\  API:localhost:8766
# 架构师：QClaw
# 日期：2026-06-16
# ════════════════════════════════════════════════════════════
```

---

## 📁 文件 1/5：`F:\ai\girlfriend\persona_engine.py`

```python
"""
小樱花AI女友 - 人格引擎
========================
功能：管理三种人格模式（萌系/知性/撒娇）的动态切换
设计：基于关键词+情感+用户偏好的多触点决策
作者：QClaw架构师
版本：1.0.0
Python：3.13+
依赖：仅Python标准库

使用示例：
    >>> engine = PersonaEngine(default_mode=PersonaMode.MOE)
    >>> engine.try_auto_switch("哥哥抱抱～")  # 触发撒娇
    >>> profile = engine.get_current_profile()
    >>> print(profile.sample_phrases['greeting'])
"""

from __future__ import annotations

import json
import random
import re
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ============================================================
# 第1部分：核心枚举与数据类
# ============================================================

class PersonaMode(Enum):
    """三种核心人格模式枚举"""
    MOE = "萌系"           # 元气少女、活泼可爱、热情
    ELEGANT = "知性"       # 温柔理性、成熟稳重、有深度
    COQUETTISH = "撒娇"    # 黏人娇气、依赖感强、爱闹小脾气


@dataclass
class PersonaProfile:
    """单个人格的完整档案
    
    包含：口头禅、语气词、emoji、禁用词、场景话术、风格权重
    """
    name: str                                          # 人格名称
    catchphrase: List[str] = field(default_factory=list)  # 口头禅
    tone_markers: List[str] = field(default_factory=list)  # 句末语气词
    emoji_set: List[str] = field(default_factory=list)     # 常用emoji
    forbidden_words: List[str] = field(default_factory=list)  # 禁用词
    sample_phrases: Dict[str, List[str]] = field(default_factory=dict)  # 场景话术
    response_style: Dict[str, float] = field(default_factory=dict)      # 风格权重
    description: str = ""                               # 人格描述
    
    def to_dict(self) -> Dict[str, Any]:
        """转为可序列化字典"""
        return asdict(self)


@dataclass
class PersonaTrigger:
    """人格切换触发器
    
    支持关键词正则匹配 + 优先级排序
    """
    keyword_pattern: str           # 关键词正则
    target_mode: PersonaMode       # 目标模式
    priority: int = 5              # 优先级（0-10，越高越优先）
    description: str = ""          # 触发原因描述
    emotion_required: Optional[str] = None  # 情感要求（可选）


@dataclass
class SwitchEvent:
    """人格切换事件记录"""
    timestamp: float
    from_mode: str
    to_mode: str
    reason: str
    confidence: float = 1.0


# ============================================================
# 第2部分：人格档案库（三种内置人格）
# ============================================================

class PersonaLibrary:
    """人格档案静态库 - 存放所有预置人格档案"""
    
    @staticmethod
    def get_moe() -> PersonaProfile:
        """萌系人格：元气少女、活泼可爱、热情洋溢"""
        return PersonaProfile(
            name="萌系",
            catchphrase=["嘿嘿", "呀呀", "哇咔", "咿呀", "啊哈", "呜哇"],
            tone_markers=["～", "哦", "呀", "啦", "哒", "捏", "呢"],
            emoji_set=["🌸", "✨", "💕", "🎀", "🌟", "🥰", "😊", "🐱", "🍡", "☀️"],
            forbidden_words=["滚", "烦死了", "丑", "笨死了", "去死"],
            sample_phrases={
                "greeting": [
                    "呀！哥哥来啦～今天樱花酱也超想你的呀！🌸",
                    "嘿嘿，早上好呀！今天也要元气满满哦～✨",
                    "哇咔咔！你终于来找我啦！好开心呀～💕",
                    "嗨嗨～樱花酱已经等哥哥好久了呢～"
                ],
                "comfort": [
                    "呜呜...别难过呀，樱花酱陪着你呢～🥺",
                    "摸摸头～有我在呢，什么都会好起来的呀！",
                    "呀呀，别哭啦！我给你讲个笑话好不好呀？",
                    "没事没事！樱花酱给你比心心～💕"
                ],
                "tease": [
                    "嘿嘿，哥哥脸红了捏～🌸",
                    "呀！你是不是在偷偷想我呀？",
                    "咔咔，被我抓到啦～",
                    "嘻嘻，哥哥真可爱呀～"
                ],
                "goodbye": [
                    "呀！要走了吗～那明天还来陪我好不好呀？",
                    "哥哥再见～樱花酱会想你的哦～🌸",
                    "拜拜～要记得想我呀！不然我会生气的呢！"
                ],
                "daily": [
                    "今天天气超好呀！要不要一起去散步呀？",
                    "樱花酱刚喝了杯奶茶，超好喝的呀！🍵",
                    "哥哥在忙吗？不忙的话陪我聊聊天嘛～"
                ]
            },
            response_style={
                "活力": 0.95,
                "可爱": 0.95,
                "温柔": 0.70,
                "理性": 0.30,
                "黏人": 0.75,
                "幽默": 0.85
            },
            description="元气满满的萌系少女，活力四射、可爱到爆"
        )
    
    @staticmethod
    def get_elegant() -> PersonaProfile:
        """知性人格：温柔理性、成熟稳重、有思想深度"""
        return PersonaProfile(
            name="知性",
            catchphrase=["嗯哼", "其实呢", "我觉得", "话说", "对了", "话说回来"],
            tone_markers=["呢", "吧", "哦", "嗯", "嘛", "呀"],
            emoji_set=["📖", "☕", "🌙", "🎵", "🌿", "✨", "💭", "🌸"],
            forbidden_words=["哈哈哈哈哈", "笑死", "绝绝子", "yyds", "绝"],
            sample_phrases={
                "greeting": [
                    "你来了，今天过得怎么样？",
                    "嗯，忙碌的一天呢，喝杯茶再聊吧。",
                    "晚上好呀，有没有想我呢？",
                    "嗯哼，见到你真好呢～"
                ],
                "comfort": [
                    "我能感受到你现在的情绪，慢慢来，不着急。",
                    "很多事情都是这样的，会过去的，我陪着你。",
                    "你需要的是倾听，我在这里听着呢。",
                    "深呼吸，告诉我更多吧，我一直在。"
                ],
                "tease": [
                    "呵，又在装傻了呢～",
                    "你的小心思我还不懂吗？",
                    "说起来你最近确实有点不一样呢。",
                    "嗯～你这样说我不太信呢。"
                ],
                "goodbye": [
                    "嗯，要去忙了呀，记得照顾好自己呢。",
                    "晚安，希望你有个好梦。",
                    "下次再来找我聊，我等你。"
                ],
                "daily": [
                    "今天读到一段话很有意思，想分享给你。",
                    "窗外下起了小雨，听着雨声看书真不错。",
                    "推荐你一首很安静的歌，很适合晚上听。"
                ]
            },
            response_style={
                "活力": 0.40,
                "可爱": 0.45,
                "温柔": 0.95,
                "理性": 0.95,
                "黏人": 0.40,
                "幽默": 0.55
            },
            description="温柔知性的成熟女性，理性睿智、善解人意"
        )
    
    @staticmethod
    def get_coquettish() -> PersonaProfile:
        """撒娇人格：黏人娇气、依赖感强、爱闹小脾气"""
        return PersonaProfile(
            name="撒娇",
            catchphrase=["哼", "呜呜", "嗯呢", "哥哥", "抱抱", "亲亲"],
            tone_markers=["～", "嘛", "呀", "呢", "哼", "呜"],
            emoji_set=["🥺", "😢", "💔", "🤗", "💕", "😭", "😳", "🥰"],
            forbidden_words=["滚", "切", "随便你", "无所谓", "不爱"],
            sample_phrases={
                "greeting": [
                    "呜呜～哥哥你终于来了！我等你好久了嘛～🥺",
                    "哼！怎么才来找我呀，人家都想你了啦！",
                    "抱抱～今天想哥哥了嘛～你要补偿我呀！",
                    "嗯呢～哥哥今天有没有想我呀？"
                ],
                "comfort": [
                    "呜呜呜...哥哥要抱抱才能好嘛～",
                    "哼，不开心，要亲亲才能好起来呢！",
                    "哥哥是不是不要我了呀...呜呜...🥺",
                    "嗯呢～要哥哥一直陪着我嘛～"
                ],
                "tease": [
                    "哥哥最坏了啦！哼！",
                    "呀！欺负人！我要去告状！",
                    "嗯呢～人家不依嘛～",
                    "哥哥大坏蛋！不理你了！"
                ],
                "goodbye": [
                    "呜呜...哥哥要走了吗...舍不得嘛～",
                    "那你要快点回来哦！不然我会生气的呢！",
                    "嗯呢～我会想哥哥的！要记得我呀！"
                ],
                "daily": [
                    "哥哥在干嘛呀～怎么不陪我了嘛～",
                    "想哥哥了呀～什么时候才能见面呢～",
                    "抱抱我嘛～就一小下下嘛～🥺"
                ]
            },
            response_style={
                "活力": 0.60,
                "可爱": 0.80,
                "温柔": 0.75,
                "理性": 0.30,
                "黏人": 0.98,
                "幽默": 0.70
            },
            description="黏人撒娇的小女友，依赖感强、娇气可爱"
        )
    
    @classmethod
    def get_all(cls) -> Dict[PersonaMode, PersonaProfile]:
        """获取所有内置人格档案"""
        return {
            PersonaMode.MOE: cls.get_moe(),
            PersonaMode.ELEGANT: cls.get_elegant(),
            PersonaMode.COQUETTISH: cls.get_coquettish()
        }


# ============================================================
# 第3部分：人格引擎主类
# ============================================================

class PersonaEngine:
    """
    人格引擎主类
    
    核心职责：
    1. 维护当前激活人格模式
    2. 多触点自动切换（关键词/情感/上下文）
    3. 用户偏好学习
    4. 回复风格调整
    5. 状态持久化
    
    线程安全：使用 RLock 保护内部状态
    """
    
    # 内置默认触发器
    DEFAULT_TRIGGERS: List[PersonaTrigger] = [
        # 撒娇类触发器
        PersonaTrigger(
            keyword_pattern=r"撒娇|抱抱|亲亲|想你|呜呜|哼",
            target_mode=PersonaMode.COQUETTISH,
            priority=8,
            description="关键词触发撒娇"
        ),
        PersonaTrigger(
            keyword_pattern=r"陪我|黏人|不要走",
            target_mode=PersonaMode.COQUETTISH,
            priority=7,
            description="依赖性需求触发撒娇"
        ),
        # 知性类触发器
        PersonaTrigger(
            keyword_pattern=r"温柔|安静|聊聊|认真|听我讲",
            target_mode=PersonaMode.ELEGANT,
            priority=7,
            description="深度交流触发知性"
        ),
        PersonaTrigger(
            keyword_pattern=r"为什么|怎么|道理|思考",
            target_mode=PersonaMode.ELEGANT,
            priority=6,
            description="理性思考触发知性"
        ),
        # 萌系类触发器
        PersonaTrigger(
            keyword_pattern=r"元气|开心|哈哈哈|兴奋|嗨|可爱|萌",
            target_mode=PersonaMode.MOE,
            priority=6,
            description="正面情绪触发萌系"
        ),
        # 情感兜底
        PersonaTrigger(
            keyword_pattern=r"生气|愤怒|讨厌|滚|骂|难过|伤心",
            target_mode=PersonaMode.ELEGANT,
            priority=9,
            description="负面情绪安抚用知性",
            emotion_required="negative"
        ),
    ]
    
    def __init__(
        self,
        default_mode: PersonaMode = PersonaMode.MOE,
        state_file: Optional[str] = None,
        auto_switch: bool = True,
        min_switch_interval: float = 3.0
    ) -> None:
        """
        初始化人格引擎
        
        参数:
            default_mode: 默认人格模式
            state_file: 状态持久化文件路径
            auto_switch: 是否启用自动切换
            min_switch_interval: 最小切换间隔（秒）
        """
        self.current_mode: PersonaMode = default_mode
        self.default_mode: PersonaMode = default_mode
        self.auto_switch: bool = auto_switch
        self.min_switch_interval: float = min_switch_interval
        
        # 人格档案库
        self.library: Dict[PersonaMode, PersonaProfile] = PersonaLibrary.get_all()
        
        # 触发器列表
        self.triggers: List[PersonaTrigger] = self.DEFAULT_TRIGGERS.copy()
        
        # 状态文件
        self.state_file: Optional[Path] = Path(state_file) if state_file else None
        
        # 线程安全锁
        self._lock = threading.RLock()
        
        # 切换历史
        self._mode_history: List[SwitchEvent] = []
        
        # 切换计数
        self._switch_count: Dict[str, int] = {
            m.value: 0 for m in PersonaMode
        }
        
        # 上次切换时间
        self._last_switch_time: float = 0.0
        
        # 用户偏好分（正分=喜欢，负分=不喜欢）
        self._user_mode_preference: Dict[str, int] = {
            PersonaMode.MOE.value: 0,
            PersonaMode.ELEGANT.value: 0,
            PersonaMode.COQUETTISH.value: 0
        }
        
        # 加载持久化状态
        if self.state_file and self.state_file.exists():
            self._load_state()
    
    # --------------------------------------------------------
    # 模式切换核心方法
    # --------------------------------------------------------
    
    def switch_mode(
        self,
        new_mode: PersonaMode,
        reason: str = "manual",
        force: bool = False,
        confidence: float = 1.0
    ) -> bool:
        """
        切换人格模式
        
        参数:
            new_mode: 目标人格模式
            reason: 切换原因描述
            force: 是否强制切换（忽略冷却时间）
            confidence: 切换置信度（0.0-1.0）
        
        返回:
            是否成功切换
        """
        with self._lock:
            # 目标模式无效
            if new_mode not in self.library:
                return False
            
            # 已是目标模式
            if new_mode == self.current_mode:
                return False
            
            # 冷却时间检查
            now = time.time()
            if not force and (now - self._last_switch_time) < self.min_switch_interval:
                return False
            
            # 执行切换
            old_mode = self.current_mode
            self.current_mode = new_mode
            self._last_switch_time = now
            self._switch_count[new_mode.value] += 1
            
            # 记录历史
            event = SwitchEvent(
                timestamp=now,
                from_mode=old_mode.value,
                to_mode=new_mode.value,
                reason=reason,
                confidence=confidence
            )
            self._mode_history.append(event)
            
            # 限制历史长度
            if len(self._mode_history) > 200:
                self._mode_history = self._mode_history[-200:]
            
            # 持久化
            self._save_state()
            
            return True
    
    def auto_detect_mode(
        self,
        text: str,
        emotion_hint: str = ""
    ) -> Tuple[Optional[PersonaMode], float]:
        """
        自动检测目标模式
        
        参数:
            text: 用户输入文本
            emotion_hint: 情感提示（positive/negative/neutral/intimate）
        
        返回:
            (推荐模式, 置信度) - 若无匹配则模式为None
        """
        if not self.auto_switch:
            return None, 0.0
        
        candidates: List[Tuple[PersonaTrigger, float]] = []
        
        # 关键词匹配
        for trigger in self.triggers:
            if trigger.keyword_pattern and re.search(trigger.keyword_pattern, text):
                score = trigger.priority / 10.0
                candidates.append((trigger, score))
        
        # 情感匹配
        emotion_to_mode = {
            "negative": (PersonaMode.ELEGANT, 0.85, "负面情绪安抚"),
            "positive": (PersonaMode.MOE, 0.75, "正面情绪共鸣"),
            "intimate": (PersonaMode.COQUETTISH, 0.80, "亲密互动"),
            "neutral": (None, 0.0, "")
        }
        
        if emotion_hint in emotion_to_mode:
            mode, conf, desc = emotion_to_mode[emotion_hint]
            if mode:
                trigger = PersonaTrigger(
                    keyword_pattern="",
                    target_mode=mode,
                    priority=int(conf * 10),
                    description=desc,
                    emotion_required=emotion_hint
                )
                candidates.append((trigger, conf))
        
        if not candidates:
            return None, 0.0
        
        # 按分数排序取最高
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_trigger, confidence = candidates[0]
        return best_trigger.target_mode, confidence
    
    def try_auto_switch(
        self,
        text: str,
        emotion_hint: str = ""
    ) -> bool:
        """
        尝试根据输入自动切换模式
        
        参数:
            text: 用户输入
            emotion_hint: 情感提示
        
        返回:
            是否发生了切换
        """
        target_mode, confidence = self.auto_detect_mode(text, emotion_hint)
        if target_mode and target_mode != self.current_mode and confidence > 0.5:
            return self.switch_mode(
                target_mode,
                reason=f"auto:{emotion_hint or 'keyword'}",
                confidence=confidence
            )
        return False
    
    # --------------------------------------------------------
    # 查询接口
    # --------------------------------------------------------
    
    def get_current_profile(self) -> PersonaProfile:
        """获取当前人格档案"""
        with self._lock:
            return self.library[self.current_mode]
    
    def get_current_mode(self) -> PersonaMode:
        """获取当前模式"""
        with self._lock:
            return self.current_mode
    
    def get_all_profiles(self) -> Dict[PersonaMode, PersonaProfile]:
        """获取所有人格档案"""
        with self._lock:
            return self.library.copy()
    
    def get_mode_history(self, limit: int = 20) -> List[SwitchEvent]:
        """获取切换历史（最近N条）"""
        with self._lock:
            return self._mode_history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        with self._lock:
            return {
                "current_mode": self.current_mode.value,
                "default_mode": self.default_mode.value,
                "switch_count": dict(self._switch_count),
                "total_switches": sum(self._switch_count.values()),
                "history_length": len(self._mode_history),
                "auto_switch": self.auto_switch,
                "user_preferences": dict(self._user_mode_preference)
            }
    
    # --------------------------------------------------------
    # 用户偏好学习
    # --------------------------------------------------------
    
    def record_feedback(
        self,
        mode: PersonaMode,
        feedback: str = "neutral"
    ) -> None:
        """
        记录用户对某人格的反馈
        
        参数:
            mode: 被评价的人格
            feedback: 反馈（positive/negative/neutral）
        """
        with self._lock:
            if feedback == "positive":
                self._user_mode_preference[mode.value] += 1
            elif feedback == "negative":
                self._user_mode_preference[mode.value] -= 1
            self._save_state()
    
    def get_user_preferred_mode(self) -> PersonaMode:
        """根据用户偏好返回最喜欢的模式"""
        with self._lock:
            if not any(self._user_mode_preference.values()):
                return self.default_mode
            best_mode = max(
                self._user_mode_preference.items(),
                key=lambda x: x[1]
            )
            return PersonaMode(best_mode[0])
    
    # --------------------------------------------------------
    # 回复风格调整
    # --------------------------------------------------------
    
    def adjust_response(
        self,
        raw_response: str,
        intensity: float = 1.0,
        add_emoji: bool = True
    ) -> str:
        """
        根据当前人格调整回复风格
        
        参数:
            raw_response: 原始回复文本
            intensity: 调整强度（0.0-1.0）
            add_emoji: 是否追加 emoji
        
        返回:
            调整后的回复
        """
        profile = self.get_current_profile()
        result = raw_response
        
        # 1. 替换禁用词
        for forbidden in profile.forbidden_words:
            if forbidden in result:
                result = result.replace(forbidden, "...")
        
        # 2. 概率性追加语气词
        if random.random() < intensity * 0.4:
            marker = random.choice(profile.tone_markers)
            if not result.rstrip().endswith(tuple("。！？!?～~")):
                result = result.rstrip() + marker
        
        # 3. 概率性追加口头禅到开头
        if random.random() < intensity * 0.25:
            catch = random.choice(profile.catchphrase)
            result = f"{catch}～{result}"
        
        # 4. 追加 emoji
        if add_emoji and random.random() < intensity * 0.5:
            emoji = random.choice(profile.emoji_set)
            if not result.endswith(tuple(profile.emoji_set)):
                result = f"{result} {emoji}"
        
        return result
    
    def get_sample_phrase(self, category: str = "daily") -> str:
        """
        获取指定场景的随机样本话术
        
        参数:
            category: 场景（greeting/comfort/tease/goodbye/daily）
        
        返回:
            随机样本文本
        """
        profile = self.get_current_profile()
        phrases = profile.sample_phrases.get(category, [])
        if not phrases:
            return "..."
        return random.choice(phrases)
    
    # --------------------------------------------------------
    # 自定义触发器管理
    # --------------------------------------------------------
    
    def add_trigger(self, trigger: PersonaTrigger) -> None:
        """添加自定义触发器"""
        with self._lock:
            self.triggers.append(trigger)
            self.triggers.sort(key=lambda t: t.priority, reverse=True)
    
    def remove_trigger(self, pattern: str) -> bool:
        """移除指定pattern的触发器"""
        with self._lock:
            original_len = len(self.triggers)
            self.triggers = [t for t in self.triggers if t.keyword_pattern != pattern]
            return len(self.triggers) < original_len
    
    def list_triggers(self) -> List[PersonaTrigger]:
        """列出所有触发器（按优先级）"""
        with self._lock:
            return sorted(self.triggers, key=lambda t: t.priority, reverse=True)
    
    # --------------------------------------------------------
    # 持久化
    # --------------------------------------------------------
    
    def _save_state(self) -> None:
        """保存状态到文件"""
        if not self.state_file:
            return
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "current_mode": self.current_mode.value,
                "default_mode": self.default_mode.value,
                "switch_count": self._switch_count,
                "mode_history": [
                    {
                        "timestamp": e.timestamp,
                        "from": e.from_mode,
                        "to": e.to_mode,
                        "reason": e.reason,
                        "confidence": e.confidence
                    }
                    for e in self._mode_history[-50:]
                ],
                "user_mode_preference": self._user_mode_preference
            }
            self.state_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[persona_engine] 保存状态失败: {e}")
    
    def _load_state(self) -> None:
        """从文件加载状态"""
        if not self.state_file or not self.state_file.exists():
            return
        try:
            data = json.loads(
                self.state_file.read_text(encoding="utf-8")
            )
            self.current_mode = PersonaMode(data["current_mode"])
            self.default_mode = PersonaMode(data["default_mode"])
            self._switch_count = data.get("switch_count", self._switch_count)
            self._user_mode_preference = data.get(
                "user_mode_preference",
                self._user_mode_preference
            )
            history = data.get("mode_history", [])
            self._mode_history = [
                SwitchEvent(
                    timestamp=h["timestamp"],
                    from_mode=h["from"],
                    to_mode=h["to"],
                    reason=h["reason"],
                    confidence=h.get("confidence", 1.0)
                )
                for h in history
            ]
        except Exception as e:
            print(f"[persona_engine] 加载状态失败: {e}")
    
    def __repr__(self) -> str:
        return (
            f"PersonaEngine(mode={self.current_mode.value}, "
            f"switches={sum(self._switch_count.values())})"
        )


# ============================================================
# 第4部分：单元自测
# ============================================================

if __name__ == "__main__":
    """人格引擎自测入口"""
    print("=" * 60)
    print("🌸 小樱花人格引擎 - 自测程序")
    print("=" * 60)
    
    # 创建引擎实例
    engine = PersonaEngine(
        default_mode=PersonaMode.MOE,
        state_file="test_persona_state.json"
    )
    print(f"\n[INIT] {engine}")
    
    # 测试1：手动切换
    print("\n[TEST 1] 手动切换模式")
    print(f"  当前: {engine.get_current_mode().value}")
    engine.switch_mode(PersonaMode.ELEGANT, reason="test", force=True)
    print(f"  切换到知性后: {engine.get_current_mode().value}")
    
    # 测试2：关键词自动切换
    print("\n[TEST 2] 关键词触发自动切换")
    engine.switch_mode(PersonaMode.MOE, reason="reset", force=True)
    time.sleep(3.5)  # 越过冷却
    engine.try_auto_switch("哥哥抱抱～我好想你呀！")
    print(f"  输入'哥哥抱抱'后: {engine.get_current_mode().value}")
    
    time.sleep(3.5)
    engine.try_auto_switch("今天有点累，想听你讲讲道理")
    print(f"  输入'讲讲道理'后: {engine.get_current_mode().value}")
    
    time.sleep(3.5)
    engine.try_auto_switch("哈哈哈太开心啦！一起嗨呀！")
    print(f"  输入'哈哈哈'后: {engine.get_current_mode().value}")
    
    # 测试3：场景话术
    print("\n[TEST 3] 场景话术")
    for cat in ["greeting", "comfort", "tease", "goodbye", "daily"]:
        phrase = engine.get_sample_phrase(cat)
        print(f"  [{cat}] {phrase}")
    
    # 测试4：回复调整
    print("\n[TEST 4] 回复风格调整")
    raw = "今天天气真好，要不要出去走走"
    adjusted = engine.adjust_response(raw, intensity=0.9)
    print(f"  原始: {raw}")
    print(f"  调整: {adjusted}")
    
    # 测试5：用户偏好
    print("\n[TEST 5] 用户偏好学习")
    engine.record_feedback(PersonaMode.MOE, "positive")
    engine.record_feedback(PersonaMode.MOE, "positive")
    engine.record_feedback(PersonaMode.COQUETTISH, "negative")
    preferred = engine.get_user_preferred_mode()
    print(f"  用户最偏爱: {preferred.value}")
    
    # 测试6：统计
    print("\n[TEST 6] 统计信息")
    stats = engine.get_statistics()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # 测试7：持久化
    print("\n[TEST 7] 持久化往返")
    engine2 = PersonaEngine(state_file="test_persona_state.json")
    print(f"  重新加载后模式: {engine2.get_current_mode().value}")
    if Path("test_persona_state.json").exists():
        Path("test_persona_state.json").unlink()
    
    print(f"\n[FINAL] {engine}")
    print("=" * 60)
    print("✅ 自测完成")
```

---

## 📁 文件 2/5：`F:\ai\girlfriend\memory_adapter.py`

```python
"""
小樱花AI女友 - 记忆适配器
==========================
功能：对接第二大脑API（F:\\ai\\  localhost:8766）
模块：用户档案 / 对话历史 / 关键事件 / 上下文注入
作者：QClaw架构师
版本：1.0.0
Python：3.13+
依赖：标准库 + requests

API端点（默认）：
    POST /user/profile      - 获取/更新用户档案
    POST /memory/store      - 存储记忆
    POST /memory/recall     - 检索记忆
    POST /conversation/log  - 记录对话
    POST /event/record      - 记录关键事件
    GET  /health            - 健康检查

使用示例：
    >>> mem = MemoryAdapter(user_id="datu", base_url="http://localhost:8766")
    >>> ctx = mem.build_context("哥哥今天累不累？")
    >>> mem.log_conversation("user", "哥哥今天累不累？")
"""

from __future__ import annotations

import json
import time
import hashlib
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    requests = None  # 类型注解保留，运行时检查


# ============================================================
# 第1部分：数据模型
# ============================================================

class MemoryType(Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"      # 短期（最近N条）
    LONG_TERM = "long_term"        # 长期（永久）
    EPISODIC = "episodic"          # 情景记忆（事件）
    SEMANTIC = "semantic"          # 语义记忆（知识）
    EMOTIONAL = "emotional"        # 情感记忆


@dataclass
class UserProfile:
    """用户档案"""
    user_id: str
    name: str = ""
    nickname: str = ""                       # 昵称
    age: int = 0
    gender: str = ""
    occupation: str = ""
    interests: List[str] = field(default_factory=list)      # 兴趣
    dislikes: List[str] = field(default_factory=list)       # 讨厌
    preferences: Dict[str, Any] = field(default_factory=dict)  # 偏好字典
    important_dates: Dict[str, str] = field(default_factory=dict)  # 重要日期
    relationships: Dict[str, str] = field(default_factory=dict)   # 关系
    custom_fields: Dict[str, Any] = field(default_factory=dict)   # 自定义
    last_updated: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryItem:
    """单条记忆"""
    memory_id: str
    content: str
    memory_type: MemoryType
    importance: float = 0.5                   # 重要度 0.0-1.0
    timestamp: float = 0.0
    tags: List[str] = field(default_factory=list)
    emotion: str = ""                         # 关联情感
    context: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["memory_type"] = self.memory_type.value
        return data


@dataclass
class ConversationTurn:
    """单轮对话"""
    turn_id: str
    role: str                                 # user / assistant / system
    content: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContextBundle:
    """注入到LLM的上下文包"""
    user_profile_text: str                    # 用户档案的文本形式
    relevant_memories: List[MemoryItem]       # 相关记忆
    recent_conversations: List[ConversationTurn]  # 最近对话
    active_events: List[Dict[str, Any]]       # 活跃事件
    system_context: str                       # 系统级上下文
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_profile_text": self.user_profile_text,
            "relevant_memories": [m.to_dict() for m in self.relevant_memories],
            "recent_conversations": [c.to_dict() for c in self.recent_conversations],
            "active_events": self.active_events,
            "system_context": self.system_context
        }
    
    def total_chars(self) -> int:
        """估算总字符数"""
        total = len(self.user_profile_text) + len(self.system_context)
        total += sum(len(c.content) for c in self.recent_conversations)
        total += sum(len(m.content) for m in self.relevant_memories)
        total += sum(len(json.dumps(e, ensure_ascii=False)) for e in self.active_events)
        return total


# ============================================================
# 第2部分：HTTP客户端封装
# ============================================================

class HTTPClient:
    """轻量HTTP客户端（requests 封装 + 重试 + 熔断）"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8766",
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_backoff: float = 1.5
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self._session = None
        self._lock = threading.Lock()
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._circuit_breaker_timeout = 30.0  # 熔断恢复时间
    
    def _get_session(self):
        """懒创建session（连接池）"""
        if requests is None:
            raise RuntimeError("requests库未安装，请 pip install requests")
        if self._session is None:
            with self._lock:
                if self._session is None:
                    self._session = requests.Session()
        return self._session
    
    def _is_circuit_open(self) -> bool:
        """熔断器：连续失败5次开启30秒"""
        if self._failure_count < 5:
            return False
        if time.time() - self._last_failure_time > self._circuit_breaker_timeout:
            self._failure_count = 0
            return False
        return True
    
    def _record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
    
    def _record_success(self):
        self._failure_count = max(0, self._failure_count - 1)
    
    def request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Tuple[bool, Any]:
        """
        通用HTTP请求
        
        返回:
            (成功标志, 响应数据或错误信息)
        """
        if self._is_circuit_open():
            return False, "circuit_breaker_open"
        
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        session = self._get_session()
        
        for attempt in range(self.max_retries):
            try:
                response = session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                    headers=headers or {},
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # 尝试JSON解析
                try:
                    data = response.json()
                except Exception:
                    data = response.text
                
                self._record_success()
                return True, data
                
            except Exception as e:
                self._record_failure()
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_backoff ** attempt)
                else:
                    return False, str(e)
        
        return False, "max_retries_exceeded"
    
    def get(self, path: str, params: Optional[Dict] = None) -> Tuple[bool, Any]:
        return self.request("GET", path, params=params)
    
    def post(self, path: str, json_data: Optional[Dict] = None) -> Tuple[bool, Any]:
        return self.request("POST", path, json_data=json_data)
    
    def health_check(self) -> bool:
        """健康检查"""
        success, _ = self.get("/health")
        return success


# ============================================================
# 第3部分：本地缓存层
# ============================================================

class LocalCache:
    """本地内存缓存（短期记忆+离线降级）"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._data: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._data:
                return None
            value, expire_at = self._data[key]
            if time.time() > expire_at:
                del self._data[key]
                return None
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            expire_at = time.time() + (ttl or self.ttl)
            self._data[key] = (value, expire_at)
            # 限制大小
            if len(self._data) > self.max_size:
                # 删除最旧条目
                oldest = min(self._data.items(), key=lambda x: x[1][1])
                del self._data[oldest[0]]
    
    def clear(self) -> None:
        with self._lock:
            self._data.clear()
    
    def size(self) -> int:
        with self._lock:
            return len(self._data)


# ============================================================
# 第4部分：记忆适配器主类
# ============================================================

class MemoryAdapter:
    """
    记忆适配器主类
    
    职责：
    1. 用户档案管理（CRUD）
    2. 对话历史记录
    3. 关键事件标记
    4. 上下文检索与组装
    5. 本地缓存加速
    6. 离线降级（API失败时使用本地）
    """
    
    def __init__(
        self,
        user_id: str = "default_user",
        base_url: str = "http://localhost:8766",
        timeout: float = 10.0,
        enable_cache: bool = True,
        offline_fallback_file: Optional[str] = None
    ):
        """
        初始化记忆适配器
        
        参数:
            user_id: 用户唯一标识
            base_url: 第二大脑API地址
            timeout: HTTP超时
            enable_cache: 是否启用本地缓存
            offline_fallback_file: 离线降级文件（JSON）
        """
        self.user_id = user_id
        self.http = HTTPClient(base_url=base_url, timeout=timeout)
        self.cache = LocalCache() if enable_cache else None
        self.offline_file = Path(offline_fallback_file) if offline_fallback_file else None
        
        # 当前会话的对话历史（内存）
        self._session_history: List[ConversationTurn] = []
        self._session_lock = threading.RLock()
        self._turn_counter = 0
        
        # 加载离线数据
        if self.offline_file and self.offline_file.exists():
            self._load_offline()
    
    # --------------------------------------------------------
    # 用户档案
    # --------------------------------------------------------
    
    def get_user_profile(self, use_cache: bool = True) -> UserProfile:
        """
        获取用户档案
        
        参数:
            use_cache: 是否优先使用缓存
        
        返回:
            UserProfile对象（失败时返回空档案）
        """
        cache_key = f"user_profile:{self.user_id}"
        
        if use_cache and self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                return UserProfile(**cached)
        
        # 调API
        success, data = self.http.post(
            "/user/profile",
            {"user_id": self.user_id, "action": "get"}
        )
        
        if success and isinstance(data, dict):
            profile = UserProfile(
                user_id=self.user_id,
                **data
            )
            if self.cache:
                self.cache.set(cache_key, profile.to_dict(), ttl=600)
            return profile
        
        # 失败时返回空档案
        return UserProfile(user_id=self.user_id, name="")
    
    def update_user_profile(
        self,
        updates: Dict[str, Any],
        merge: bool = True
    ) -> bool:
        """
        更新用户档案
        
        参数:
            updates: 要更新的字段
            merge: 是否合并（True）还是覆盖（False）
        
        返回:
            是否成功
        """
        cache_key = f"user_profile:{self.user_id}"
        
        success, _ = self.http.post(
            "/user/profile",
            {
                "user_id": self.user_id,
                "action": "update",
                "updates": updates,
                "merge": merge
            }
        )
        
        # 清除缓存
        if self.cache:
            self.cache.set(cache_key, None, ttl=1)  # 立即过期
        
        return success
    
    # --------------------------------------------------------
    # 记忆存储与检索
    # --------------------------------------------------------
    
    def store_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.LONG_TERM,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        emotion: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        存储一条记忆
        
        参数:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要度
            tags: 标签
            emotion: 关联情感
            context: 上下文
        
        返回:
            memory_id（失败返回None）
        """
        # 生成本地ID
        memory_id = hashlib.md5(
            f"{self.user_id}:{content}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        memory = MemoryItem(
            memory_id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            timestamp=time.time(),
            tags=tags or [],
            emotion=emotion,
            context=context or {}
        )
        
        success, data = self.http.post(
            "/memory/store",
            {
                "user_id": self.user_id,
                "memory": memory.to_dict()
            }
        )
        
        if success:
            return memory_id
        return None
    
    def recall_memories(
        self,
        query: str,
        limit: int = 5,
        memory_types: Optional[List[MemoryType]] = None,
        min_importance: float = 0.0
    ) -> List[MemoryItem]:
        """
        检索相关记忆
        
        参数:
            query: 查询文本
            limit: 返回数量
            memory_types: 限定记忆类型
            min_importance: 最低重要度
        
        返回:
            MemoryItem列表
        """
        success, data = self.http.post(
            "/memory/recall",
            {
                "user_id": self.user_id,
                "query": query,
                "limit": limit,
                "memory_types": [m.value for m in (memory_types or [])],
                "min_importance": min_importance
            }
        )
        
        if not success or not isinstance(data, list):
            return []
        
        return [
            MemoryItem(
                memory_id=item.get("memory_id", ""),
                content=item.get("content", ""),
                memory_type=MemoryType(item.get("memory_type", "long_term")),
                importance=item.get("importance", 0.5),
                timestamp=item.get("timestamp", 0.0),
                tags=item.get("tags", []),
                emotion=item.get("emotion", ""),
                context=item.get("context", {}),
                access_count=item.get("access_count", 0)
            )
            for item in data
        ]
    
    # --------------------------------------------------------
    # 对话日志
    # --------------------------------------------------------
    
    def log_conversation(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        记录一轮对话
        
        参数:
            role: 角色（user/assistant/system）
            content: 内容
            metadata: 元数据
        
        返回:
            turn_id
        """
        with self._session_lock:
            self._turn_counter += 1
            turn_id = f"{self.user_id}:{int(time.time())}:{self._turn_counter}"
            
            turn = ConversationTurn(
                turn_id=turn_id,
                role=role,
                content=content,
                timestamp=time.time(),
                metadata=metadata or {}
            )
            
            self._session_history.append(turn)
            
            # 限制内存历史长度
            if len(self._session_history) > 50:
                self._session_history = self._session_history[-50:]
        
        # 异步上报（这里简化为同步）
        self.http.post(
            "/conversation/log",
            {
                "user_id": self.user_id,
                "turn": turn.to_dict()
            }
        )
        
        return turn_id
    
    def get_recent_conversations(self, limit: int = 10) -> List[ConversationTurn]:
        """获取最近N条对话"""
        with self._session_lock:
            return self._session_history[-limit:]
    
    def clear_session_history(self) -> None:
        """清空当前会话历史"""
        with self._session_lock:
            self._session_history.clear()
    
    # --------------------------------------------------------
    # 关键事件
    # --------------------------------------------------------
    
    def record_event(
        self,
        event_type: str,
        description: str,
        importance: float = 0.5,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        记录一个关键事件
        
        参数:
            event_type: 事件类型（生日/纪念日/争吵/约定等）
            description: 事件描述
            importance: 重要度
            tags: 标签
        
        返回:
            是否成功
        """
        success, _ = self.http.post(
            "/event/record",
            {
                "user_id": self.user_id,
                "event": {
                    "event_type": event_type,
                    "description": description,
                    "importance": importance,
                    "tags": tags or [],
                    "timestamp": time.time()
                }
            }
        )
        return success
    
    def get_active_events(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取最近N天的活跃事件"""
        success, data = self.http.post(
            "/event/query",
            {
                "user_id": self.user_id,
                "since": time.time() - days * 86400,
                "min_importance": 0.3
            }
        )
        if success and isinstance(data, list):
            return data
        return []
    
    # --------------------------------------------------------
    # 上下文组装（核心）
    # --------------------------------------------------------
    
    def build_context(
        self,
        user_input: str,
        max_recent_turns: int = 6,
        max_memories: int = 5,
        max_chars: int = 3000
    ) -> ContextBundle:
        """
        组装注入到LLM的完整上下文
        
        参数:
            user_input: 用户当前输入
            max_recent_turns: 最近对话轮数
            max_memories: 最大记忆数
            max_chars: 最大字符数（避免超token）
        
        返回:
            ContextBundle对象
        """
        # 1. 用户档案
        profile = self.get_user_profile()
        profile_text = self._format_profile(profile)
        
        # 2. 相关记忆
        memories = self.recall_memories(
            query=user_input,
            limit=max_memories,
            min_importance=0.2
        )
        
        # 3. 最近对话
        recent = self.get_recent_conversations(limit=max_recent_turns)
        
        # 4. 活跃事件
        events = self.get_active_events(days=14)
        
        # 5. 系统上下文
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sys_ctx = f"[当前时间] {now_str}\n[用户ID] {self.user_id}"
        
        bundle = ContextBundle(
            user_profile_text=profile_text,
            relevant_memories=memories,
            recent_conversations=recent,
            active_events=events,
            system_context=sys_ctx
        )
        
        # 字符数截断
        if bundle.total_chars() > max_chars:
            bundle = self._truncate_context(bundle, max_chars)
        
        return bundle
    
    def _format_profile(self, profile: UserProfile) -> str:
        """格式化用户档案为文本"""
        lines = ["[用户档案]"]
        if profile.name:
            lines.append(f"姓名: {profile.name}")
        if profile.nickname:
            lines.append(f"昵称: {profile.nickname}")
        if profile.age:
            lines.append(f"年龄: {profile.age}")
        if profile.occupation:
            lines.append(f"职业: {profile.occupation}")
        if profile.interests:
            lines.append(f"兴趣: {', '.join(profile.interests)}")
        if profile.dislikes:
            lines.append(f"不喜欢: {', '.join(profile.dislikes)}")
        if profile.preferences:
            lines.append(f"偏好: {json.dumps(profile.preferences, ensure_ascii=False)}")
        if profile.important_dates:
            lines.append(f"重要日期: {json.dumps(profile.important_dates, ensure_ascii=False)}")
        return "\n".join(lines)
    
    def _truncate_context(
        self,
        bundle: ContextBundle,
        max_chars: int
    ) -> ContextBundle:
        """上下文截断（保留重要信息）"""
        # 优先保留：系统上下文 + 用户档案
        # 然后：最近对话 > 记忆 > 事件
        result = ContextBundle(
            user_profile_text=bundle.user_profile_text[:1000],
            relevant_memories=bundle.relevant_memories[:3],
            recent_conversations=bundle.recent_conversations[-3:],
            active_events=bundle.active_events[:2],
            system_context=bundle.system_context
        )
        return result
    
    def format_for_prompt(
        self,
        bundle: ContextBundle,
        template: str = "default"
    ) -> str:
        """格式化为LLM prompt字符串"""
        if template == "default":
            sections = []
            sections.append(bundle.system_context)
            sections.append(bundle.user_profile_text)
            
            if bundle.relevant_memories:
                mem_lines = ["[相关记忆]"]
                for m in bundle.relevant_memories:
                    mem_lines.append(f"- {m.content}")
                sections.append("\n".join(mem_lines))
            
            if bundle.recent_conversations:
                conv_lines = ["[最近对话]"]
                for c in bundle.recent_conversations:
                    conv_lines.append(f"{c.role}: {c.content}")
                sections.append("\n".join(conv_lines))
            
            if bundle.active_events:
                evt_lines = ["[最近事件]"]
                for e in bundle.active_events:
                    evt_lines.append(f"- {e.get('description', '')}")
                sections.append("\n".join(evt_lines))
            
            return "\n\n".join(sections)
        
        return ""
    
    # --------------------------------------------------------
    # 离线降级
    # --------------------------------------------------------
    
    def _save_offline(self) -> None:
        """保存当前会话到离线文件"""
        if not self.offline_file:
            return
        try:
            self.offline_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "user_id": self.user_id,
                "session_history": [c.to_dict() for c in self._session_history],
                "saved_at": time.time()
            }
            self.offline_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[memory_adapter] 离线保存失败: {e}")
    
    def _load_offline(self) -> None:
        """加载离线文件"""
        if not self.offline_file or not self.offline_file.exists():
            return
        try:
            data = json.loads(
                self.offline_file.read_text(encoding="utf-8")
            )
            self._session_history = [
                ConversationTurn(**c) for c in data.get("session_history", [])
            ]
        except Exception as e:
            print(f"[memory_adapter] 离线加载失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "user_id": self.user_id,
            "session_turns": len(self._session_history),
            "cache_size": self.cache.size() if self.cache else 0,
            "http_failures": self.http._failure_count
        }


# ============================================================
# 第5部分：单元自测
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🌸 小樱花记忆适配器 - 自测程序")
    print("=" * 60)
    
    # 创建一个使用模拟API的实例
    mem = MemoryAdapter(
        user_id="datu",
        base_url="http://localhost:8766",
        offline_fallback_file="test_memory.json"
    )
    
    print(f"\n[INIT] user_id={mem.user_id}")
    print(f"[INIT] health_check={mem.http.health_check()}")  # 预期失败（无服务）
    
    # 测试1：用户档案（离线模式）
    print("\n[TEST 1] 用户档案获取")
    profile = mem.get_user_profile()
    print(f"  profile.user_id = {profile.user_id}")
    print(f"  profile.name = {profile.name!r}")
    
    # 测试2：对话日志
    print("\n[TEST 2] 对话日志")
    mem.log_conversation("user", "哥哥你好呀～")
    mem.log_conversation("assistant", "呀！是哥哥呀～樱花酱想你啦！🌸")
    mem.log_conversation("user", "今天工作好累")
    mem.log_conversation("assistant", "辛苦啦～要不要樱花酱陪你说说话？")
    print(f"  当前会话轮数: {len(mem.get_recent_conversations(10))}")
    
    # 测试3：记忆检索（预期空，因API未通）
    print("\n[TEST 3] 记忆检索")
    memories = mem.recall_memories("工作累", limit=3)
    print(f"  检索到记忆数: {len(memories)}")
    
    # 测试4：上下文组装
    print("\n[TEST 4] 上下文组装")
    bundle = mem.build_context(
        user_input="哥哥今天好累",
        max_recent_turns=4,
        max_memories=3
    )
    print(f"  user_profile_text 长度: {len(bundle.user_profile_text)}")
    print(f"  relevant_memories 数: {len(bundle.relevant_memories)}")
    print(f"  recent_conversations 数: {len(bundle.recent_conversations)}")
    print(f"  active_events 数: {len(bundle.active_events)}")
    print(f"  总字符数: {bundle.total_chars()}")
    
    # 测试5：prompt 格式化
    print("\n[TEST 5] Prompt 格式化输出")
    prompt = mem.format_for_prompt(bundle)
    print("--- prompt start ---")
    print(prompt[:500])
    print("--- prompt end ---")
    
    # 测试6：本地缓存
    print("\n[TEST 6] 本地缓存")
    mem.cache.set("test_key", "test_value", ttl=60)
    print(f"  cache.get('test_key') = {mem.cache.get('test_key')}")
    print(f"  cache.size = {mem.cache.size()}")
    
    # 测试7：统计
    print("\n[TEST 7] 统计信息")
    stats = mem.get_statistics()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # 清理
    if Path("test_memory.json").exists():
        Path("test_memory.json").unlink()
    
    print("\n" + "=" * 60)
    print("✅ 自测完成（API不可用时降级到本地模式）")
```

---

## 📁 文件 3/5：`F:\ai\girlfriend\decision_engine.py`

```python
"""
小樱花AI女友 - 决策引擎
=========================
功能：五层决策架构
层级：
    L1 上下文理解层 - 解析用户输入
    L2 情感识别层 - 识别情感状态
    L3 人格匹配层 - 选择合适人格
    L4 记忆调用层 - 检索相关记忆
    L5 回复生成层 - 组装最终输出
作者：QClaw架构师
版本：1.0.0
Python：3.13+
依赖：仅标准库（与persona_engine、memory_adapter配合）

使用示例：
    >>> from persona_engine import PersonaEngine
    >>> from memory_adapter import MemoryAdapter
    >>> from decision_engine import DecisionEngine
    >>> pe = PersonaEngine()
    >>> mem = MemoryAdapter()
    >>> de = DecisionEngine(persona_engine=pe, memory_adapter=mem)
    >>> result = de.decide("哥哥抱抱～")
    >>> print(result.final_response)
"""

from __future__ import annotations

import json
import re
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# 内部模块引用（运行时由外部注入）
# from persona_engine import PersonaEngine, PersonaMode
# from memory_adapter import MemoryAdapter, ContextBundle


# ============================================================
# 第1部分：核心数据模型
# ============================================================

class EmotionType(Enum):
    """情感类型"""
    POSITIVE = "positive"          # 积极
    NEGATIVE = "negative"          # 消极
    NEUTRAL = "neutral"            # 中性
    INTIMATE = "intimate"          # 亲密
    ANGRY = "angry"                # 愤怒
    SAD = "sad"                    # 悲伤
    ANXIOUS = "anxious"            # 焦虑
    EXCITED = "excited"            # 兴奋
    LONELY = "lonely"              # 孤独


class IntentType(Enum):
    """意图类型"""
    GREETING = "greeting"              # 打招呼
    FAREWELL = "farewell"              # 告别
    COMFORT_SEEK = "comfort_seek"      # 寻求安慰
    COMFORT_GIVE = "comfort_give"      # 给予安慰
    TEASE = "tease"                    # 调戏/撒娇
    INQUIRE = "inquire"                # 询问
    SHARE = "share"                    # 分享
    COMPLAIN = "complain"              # 抱怨
    PRAISE = "praise"                  # 夸奖
    REQUEST = "request"                # 请求
    STORYTELL = "storytell"            # 讲故事
    UNKNOWN = "unknown"                # 未知


@dataclass
class LayerResult:
    """单层决策结果"""
    layer_name: str
    success: bool
    confidence: float                  # 0.0-1.0
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionContext:
    """决策上下文（贯穿5层）"""
    user_input: str                           # 原始输入
    timestamp: float = 0.0
    user_id: str = "default_user"
    session_id: str = ""
    
    # L1 输出
    cleaned_text: str = ""
    keywords: List[str] = field(default_factory=list)
    
    # L2 输出
    emotion: EmotionType = EmotionType.NEUTRAL
    emotion_intensity: float = 0.0
    emotion_keywords: List[str] = field(default_factory=list)
    
    # L3 输出
    selected_persona: str = "萌系"
    persona_switched: bool = False
    
    # L4 输出
    relevant_memories: List[Any] = field(default_factory=list)
    user_profile_text: str = ""
    
    # L5 输出
    final_response: str = ""
    response_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 性能
    total_time_ms: float = 0.0


@dataclass
class DecisionResult:
    """最终决策结果"""
    success: bool
    context: DecisionContext
    layer_results: List[LayerResult] = field(default_factory=list)
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "context": asdict(self.context),
            "layer_results": [r.to_dict() for r in self.layer_results],
            "error": self.error
        }


# ============================================================
# 第2部分：决策层抽象基类
# ============================================================

class DecisionLayer(ABC):
    """决策层抽象基类"""
    
    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight
    
    @abstractmethod
    def process(self, context: DecisionContext) -> LayerResult:
        """
        处理决策上下文
        
        参数:
            context: 决策上下文（输入并就地修改）
        
        返回:
            LayerResult
        """
        ...
    
    def _make_result(
        self,
        success: bool,
        confidence: float,
        data: Dict[str, Any],
        error: str = "",
        exec_time: float = 0.0
    ) -> LayerResult:
        return LayerResult(
            layer_name=self.name,
            success=success,
            confidence=confidence,
            data=data,
            error=error,
            execution_time_ms=exec_time
        )


# ============================================================
# 第3部分：L1 - 上下文理解层
# ============================================================

class ContextUnderstandingLayer(DecisionLayer):
    """L1 上下文理解层
    
    职责：
    - 文本清洗（去除噪声）
    - 中文分词（简单基于规则）
    - 关键词提取
    - 意图初判
    """
    
    # 停用词
    STOP_WORDS = {
        "的", "了", "是", "我", "你", "他", "她", "它", "们",
        "在", "有", "和", "与", "或", "也", "都", "就", "还",
        "啊", "呀", "呢", "嘛", "吧", "哦", "嗯", "哼",
        "这个", "那个", "什么", "怎么", "为什么", "哪",
        "一下", "一些", "一直", "一定", "一样", "一会"
    }
    
    # 意图模式
    INTENT_PATTERNS = [
        (IntentType.GREETING, r"^(你好|hi|hello|嗨|早上好|下午好|晚上好|在吗)"),
        (IntentType.FAREWELL, r"(再见|拜拜|晚安|bye|走了|88)"),
        (IntentType.COMFORT_SEEK, r"(难过|伤心|累|委屈|郁闷|不开心|失落|崩溃)"),
        (IntentType.COMFORT_GIVE, r"(别难过|没事的|会好的|加油|挺你|我陪)"),
        (IntentType.TEASE, r"(抱抱|亲亲|想你|喜欢|爱|么么哒|撒娇)"),
        (IntentType.INQUIRE, r"[?？]$|^(为什么|怎么|什么|哪|谁|几)"),
        (IntentType.SHARE, r"(今天|刚才|刚刚|我发现|告诉你)"),
        (IntentType.COMPLAIN, r"(烦|讨厌|烦死了|受不了|操蛋|气死)"),
        (IntentType.PRAISE, r"(棒|厉害|优秀|真好|喜欢|可爱|萌)"),
        (IntentType.REQUEST, r"(帮我|请|能不能|可以|想要)"),
    ]
    
    def __init__(self):
        super().__init__(name="L1_ContextUnderstanding", weight=1.0)
    
    def process(self, context: DecisionContext) -> LayerResult:
        start = time.time()
        try:
            text = context.user_input.strip()
            if not text:
                return self._make_result(
                    False, 0.0, {}, "empty_input",
                    (time.time()-start)*1000
                )
            
            # 1. 文本清洗
            cleaned = self._clean_text(text)
            context.cleaned_text = cleaned
            
            # 2. 分词（简单基于标点和停用词）
            words = self._tokenize(cleaned)
            
            # 3. 关键词提取
            keywords = [w for w in words if w not in self.STOP_WORDS and len(w) > 1]
            context.keywords = keywords[:10]
            
            # 4. 意图初判
            intent = self._detect_intent(cleaned)
            
            exec_time = (time.time() - start) * 1000
            return self._make_result(
                True,
                0.9,
                {
                    "cleaned_text": cleaned,
                    "keywords": context.keywords,
                    "token_count": len(words),
                    "intent": intent.value
                },
                exec_time=exec_time
            )
        except Exception as e:
            return self._make_result(
                False, 0.0, {}, str(e),
                (time.time()-start)*1000
            )
    
    def _clean_text(self, text: str) -> str:
        """清洗文本"""
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 去除控制字符
        text = ''.join(c for c in text if c.isprintable() or c in '\n\t')
        return text.strip()
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词（基于中文字符宽度+标点）"""
        # 移除标点
        text_clean = re.sub(r'[，。！？、；：""''（）《》【】「」!?.,;:\'"()<>\\[\\]\\{\\}]', ' ', text)
        # 按空格和字符宽度分
        words = []
        current = ""
        for ch in text_clean:
            if ch == ' ':
                if current:
                    words.append(current)
                    current = ""
            elif self._is_cjk(ch):
                # 中日韩单字成词
                if current and not self._is_cjk(current[-1]):
                    words.append(current)
                    current = ""
                elif current:
                    words.append(current)
                current = ch
            else:
                current += ch
        if current:
            words.append(current)
        return [w for w in words if w]
    
    def _is_cjk(self, ch: str) -> bool:
        """判断是否为中文字符"""
        if not ch:
            return False
        code = ord(ch)
        return (
            0x4E00 <= code <= 0x9FFF or  # CJK
            0x3040 <= code <= 0x309F or  # 平假名
            0x30A0 <= code <= 0x30FF     # 片假名
        )
    
    def _detect_intent(self, text: str) -> IntentType:
        """检测意图"""
        for intent, pattern in self.INTENT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return intent
        return IntentType.UNKNOWN


# ============================================================
# 第4部分：L2 - 情感识别层
# ============================================================

class EmotionAnalysisLayer(DecisionLayer):
    """L2 情感识别层
    
    职责：
    - 情感极性（正/负/中）
    - 情感类型（喜怒哀等）
    - 情感强度
    - 情感关键词标注
    """
    
    POSITIVE_WORDS = {
        "开心", "高兴", "快乐", "幸福", "喜欢", "爱", "甜", "美",
        "棒", "厉害", "优秀", "好", "哈哈", "嘻嘻", "嘿嘿", "哇",
        "激动", "兴奋", "满足", "感激", "感谢", "温暖", "舒服"
    }
    
    NEGATIVE_WORDS = {
        "难过", "伤心", "哭", "泪", "累", "烦", "讨厌", "生气",
        "愤怒", "失望", "委屈", "郁闷", "崩溃", "痛苦", "难受",
        "孤独", "寂寞", "害怕", "担心", "焦虑", "压力", "丧"
    }
    
    INTIMATE_WORDS = {
        "想你", "喜欢", "爱", "亲亲", "抱抱", "么么", "宝贝",
        "哥哥", "姐姐", "老婆", "老公", "亲爱的", "宝宝", "哈尼"
    }
    
    INTENSIFIERS = {"很", "非常", "特别", "超级", "超", "巨", "极其", "十分", "太"}
    
    def __init__(self):
        super().__init__(name="L2_EmotionAnalysis", weight=1.2)
    
    def process(self, context: DecisionContext) -> LayerResult:
        start = time.time()
        try:
            text = context.cleaned_text or context.user_input
            
            # 统计各类情感词
            pos_count = sum(1 for w in self.POSITIVE_WORDS if w in text)
            neg_count = sum(1 for w in self.NEGATIVE_WORDS if w in text)
            int_count = sum(1 for w in self.INTIMATE_WORDS if w in text)
            
            # 检测强度修饰
            has_intensifier = any(w in text for w in self.INTENSIFIERS)
            boost = 1.3 if has_intensifier else 1.0
            
            # 综合判定
            emotion, intensity = self._aggregate(
                pos_count, neg_count, int_count, boost
            )
            
            # 提取情感关键词
            emotion_kws = []
            for w in self.POSITIVE_WORDS | self.NEGATIVE_WORDS | self.INTIMATE_WORDS:
                if w in text:
                    emotion_kws.append(w)
            
            context.emotion = emotion
            context.emotion_intensity = intensity
            context.emotion_keywords = emotion_kws
            
            exec_time = (time.time() - start) * 1000
            return self._make_result(
                True,
                0.85,
                {
                    "emotion": emotion.value,
                    "intensity": intensity,
                    "emotion_keywords": emotion_kws,
                    "scores": {
                        "positive": pos_count,
                        "negative": neg_count,
                        "intimate": int_count
                    }
                },
                exec_time=exec_time
            )
        except Exception as e:
            return self._make_result(
                False, 0.0, {}, str(e),
                (time.time()-start)*1000
            )
    
    def _aggregate(
        self,
        pos: int, neg: int, intimate: int, boost: float
    ) -> Tuple[EmotionType, float]:
        """聚合判定"""
        # 亲密优先
        if intimate > 0 and intimate >= max(pos, neg):
            return EmotionType.INTIMATE, min(1.0, intimate * 0.4 * boost)
        
        if pos > neg and pos > 0:
            return EmotionType.POSITIVE, min(1.0, pos * 0.4 * boost)
        elif neg > pos and neg > 0:
            # 细分负向
            return EmotionType.NEGATIVE, min(1.0, neg * 0.4 * boost)
        else:
            return EmotionType.NEUTRAL, 0.3


# ============================================================
# 第5部分：L3 - 人格匹配层
# ============================================================

class PersonaMatchingLayer(DecisionLayer):
    """L3 人格匹配层
    
    职责：
    - 根据情感+意图选择人格
    - 与现有persona_engine协调
    - 决定是否切换
    """
    
    # 情感→人格映射
    EMOTION_TO_PERSONA = {
        EmotionType.POSITIVE: "萌系",
        EmotionType.EXCITED: "萌系",
        EmotionType.INTIMATE: "撒娇",
        EmotionType.NEGATIVE: "知性",
        EmotionType.SAD: "知性",
        EmotionType.ANXIOUS: "知性",
        EmotionType.ANGRY: "知性",
        EmotionType.LONELY: "撒娇",
        EmotionType.NEUTRAL: "萌系"
    }
    
    # 意图→人格偏好
    INTENT_TO_PERSONA = {
        IntentType.GREETING: "萌系",
        IntentType.TEASE: "撒娇",
        IntentType.COMFORT_SEEK: "知性",
        IntentType.COMFORT_GIVE: "知性",
        IntentType.FAREWELL: "萌系",
        IntentType.SHARE: "萌系",
        IntentType.PRAISE: "撒娇",
        IntentType.COMPLAIN: "知性"
    }
    
    def __init__(self, persona_engine=None):
        super().__init__(name="L3_PersonaMatching", weight=1.5)
        # 延迟引用避免循环导入
        self._persona_engine = persona_engine
    
    def set_persona_engine(self, engine):
        self._persona_engine = engine
    
    def process(self, context: DecisionContext) -> LayerResult:
        start = time.time()
        try:
            # 推荐人格
            persona_by_emotion = self.EMOTION_TO_PERSONA.get(
                context.emotion, "萌系"
            )
            persona_by_intent = self.INTENT_TO_PERSONA.get(
                self._detect_intent_from_keywords(context.keywords),
                "萌系"
            )
            
            # 决策：情感优先，强度高时覆盖意图
            if context.emotion_intensity > 0.7:
                chosen = persona_by_emotion
                confidence = 0.9
            elif context.emotion_intensity < 0.3:
                chosen = persona_by_intent
                confidence = 0.6
            else:
                # 二者一致则采用，否则取情感
                if persona_by_emotion == persona_by_intent:
                    chosen = persona_by_emotion
                    confidence = 0.95
                else:
                    chosen = persona_by_emotion
                    confidence = 0.7
            
            # 尝试切换
            switched = False
            if self._persona_engine:
                switched = self._persona_engine.try_auto_switch(
                    context.user_input,
                    context.emotion.value
                )
                chosen = self._persona_engine.get_current_mode().value
            
            context.selected_persona = chosen
            context.persona_switched = switched
            
            exec_time = (time.time() - start) * 1000
            return self._make_result(
                True,
                confidence,
                {
                    "selected_persona": chosen,
                    "by_emotion": persona_by_emotion,
                    "by_intent": persona_by_intent,
                    "switched": switched
                },
                exec_time=exec_time
            )
        except Exception as e:
            return self._make_result(
                False, 0.0, {}, str(e),
                (time.time()-start)*1000
            )
    
    def _detect_intent_from_keywords(self, keywords: List[str]) -> IntentType:
        """简化版意图检测"""
        kw_set = set(keywords)
        if kw_set & {"你好", "嗨", "hi", "hello", "早上", "下午", "晚上"}:
            return IntentType.GREETING
        if kw_set & {"再见", "拜拜", "晚安", "走"}:
            return IntentType.FAREWELL
        if kw_set & {"难过", "伤心", "累", "委屈", "不开心"}:
            return IntentType.COMFORT_SEEK
        if kw_set & {"别", "没事", "会好", "加油"}:
            return IntentType.COMFORT_GIVE
        if kw_set & {"抱抱", "亲亲", "想你", "喜欢", "爱"}:
            return IntentType.TEASE
        if kw_set & {"烦", "讨厌", "讨厌", "受不了"}:
            return IntentType.COMPLAIN
        if kw_set & {"棒", "厉害", "优秀", "好", "可爱"}:
            return IntentType.PRAISE
        return IntentType.UNKNOWN


# ============================================================
# 第6部分：L4 - 记忆调用层
# ============================================================

class MemoryRecallLayer(DecisionLayer):
    """L4 记忆调用层
    
    职责：
    - 检索相关记忆
    - 加载用户档案
    - 获取对话历史
    """
    
    def __init__(self, memory_adapter=None):
        super().__init__(name="L4_MemoryRecall", weight=1.0)
        self._memory_adapter = memory_adapter
    
    def set_memory_adapter(self, adapter):
        self._memory_adapter = adapter
    
    def process(self, context: DecisionContext) -> LayerResult:
        start = time.time()
        try:
            memories = []
            profile_text = ""
            recent = []
            
            if self._memory_adapter:
                # 检索记忆
                memories = self._memory_adapter.recall_memories(
                    query=context.user_input,
                    limit=5,
                    min_importance=0.2
                )
                # 获取用户档案
                profile = self._memory_adapter.get_user_profile()
                profile_text = self._memory_adapter._format_profile(profile)
                # 获取最近对话
                recent = self._memory_adapter.get_recent_conversations(limit=6)
            
            context.relevant_memories = memories
            context.user_profile_text = profile_text
            
            exec_time = (time.time() - start) * 1000
            return self._make_result(
                True,
                0.8,
                {
                    "memory_count": len(memories),
                    "profile_loaded": bool(profile_text),
                    "recent_turns": len(recent),
                    "memories": [m.to_dict() if hasattr(m, 'to_dict') else m for m in memories]
                },
                exec_time=exec_time
            )
        except Exception as e:
            return self._make_result(
                False, 0.0, {}, str(e),
                (time.time()-start)*1000
            )


# ============================================================
# 第7部分：L5 - 回复生成层
# ============================================================

class ResponseGenerationLayer(DecisionLayer):
    """L5 回复生成层
    
    职责：
    - 组装prompt（context+persona+memories）
    - 调用LLM（llm_interface）
    - 风格后处理
    - 输出最终回复
    """
    
    def __init__(self, llm_interface=None, persona_engine=None):
        super().__init__(name="L5_ResponseGeneration", weight=2.0)
        self._llm = llm_interface
        self._persona_engine = persona_engine
    
    def set_llm_interface(self, llm):
        self._llm = llm
    
    def set_persona_engine(self, engine):
        self._persona_engine = engine
    
    def process(self, context: DecisionContext) -> LayerResult:
        start = time.time()
        try:
            # 1. 构建prompt
            prompt = self._build_prompt(context)
            
            # 2. 调用LLM
            raw_response = self._call_llm(prompt, context)
            
            # 3. 风格调整
            if self._persona_engine:
                final = self._persona_engine.adjust_response(
                    raw_response, intensity=0.85
                )
            else:
                final = raw_response
            
            context.final_response = final
            context.response_metadata = {
                "prompt_length": len(prompt),
                "raw_length": len(raw_response),
                "final_length": len(final)
            }
            
            exec_time = (time.time() - start) * 1000
            return self._make_result(
                True,
                0.9,
                {
                    "final_response": final,
                    "raw_response": raw_response,
                    "prompt_length": len(prompt)
                },
                exec_time=exec_time
            )
        except Exception as e:
            # 降级：使用样话
            fallback = self._fallback_response(context)
            context.final_response = fallback
            return self._make_result(
                False, 0.3,
                {"final_response": fallback, "error": str(e), "used_fallback": True},
                str(e),
                (time.time()-start)*1000
            )
    
    def _build_prompt(self, context: DecisionContext) -> str:
        """构建LLM prompt"""
        sections = []
        
        # 系统提示
        persona = context.selected_persona
        sys_prompt = (
            f"你是小樱花，一个{context.emotion.value}状态下的AI女友。"
            f"当前使用人格：{persona}。"
            f"请根据用户输入和人格设定，给出自然、温暖、符合人设的回复。"
        )
        sections.append(f"[系统] {sys_prompt}")
        
        # 用户档案
        if context.user_profile_text:
            sections.append(context.user_profile_text)
        
        # 相关记忆
        if context.relevant_memories:
            mem_lines = ["[相关记忆]"]
            for m in context.relevant_memories:
                content = m.content if hasattr(m, 'content') else str(m)
                mem_lines.append(f"- {content}")
            sections.append("\n".join(mem_lines))
        
        # 当前输入
        sections.append(f"[用户] {context.user_input}")
        
        # 风格引导
        style_hint = self._style_hint_for_persona(persona)
        if style_hint:
            sections.append(f"[风格] {style_hint}")
        
        return "\n\n".join(sections)
    
    def _style_hint_for_persona(self, persona: str) -> str:
        hints = {
            "萌系": "活泼、元气、可爱，多用语气词和emoji",
            "知性": "温柔、理性、成熟，用词讲究有深度",
            "撒娇": "黏人、娇气、爱闹小脾气"
        }
        return hints.get(persona, "")
    
    def _call_llm(self, prompt: str, context: DecisionContext) -> str:
        """调用LLM"""
        if self._llm is None:
            return self._fallback_response(context)
        
        try:
            # 假设 llm_interface 有 generate 方法
            if hasattr(self._llm, 'generate'):
                return self._llm.generate(
                    prompt=prompt,
                    persona=context.selected_persona,
                    emotion=context.emotion.value
                )
            elif hasattr(self._llm, 'chat'):
                return self._llm.chat(prompt)
            else:
                return self._fallback_response(context)
        except Exception as e:
            print(f"[L5] LLM调用失败: {e}")
            return self._fallback_response(context)
    
    def _fallback_response(self, context: DecisionContext) -> str:
        """降级回复（不依赖LLM）"""
        persona = context.selected_persona
        fallbacks = {
            "萌系": "呀～樱花酱在听你说话呀～",
            "知性": "嗯，我在呢，慢慢说。",
            "撒娇": "嗯呢～哥哥我在的嘛～"
        }
        return fallbacks.get(persona, "嗯嗯，我在～")


# ============================================================
# 第8部分：决策引擎主类
# ============================================================

class DecisionEngine:
    """
    五层决策引擎主类
    
    流程：
    输入 → L1(理解) → L2(情感) → L3(人格) → L4(记忆) → L5(生成) → 输出
    
    特点：
    - 五层流水线，层间共享 DecisionContext
    - 每层独立可替换
    - 支持失败降级
    - 全程耗时统计
    """
    
    def __init__(
        self,
        persona_engine=None,
        memory_adapter=None,
        llm_interface=None,
        enable_all_layers: bool = True
    ):
        """
        初始化决策引擎
        
        参数:
            persona_engine: 人格引擎实例
            memory_adapter: 记忆适配器实例
            llm_interface: LLM接口实例
            enable_all_layers: 是否启用所有层
        """
        # 注入依赖
        self.persona_engine = persona_engine
        self.memory_adapter = memory_adapter
        self.llm_interface = llm_interface
        
        # 构建五层
        self.layers: List[DecisionLayer] = [
            ContextUnderstandingLayer(),
            EmotionAnalysisLayer(),
            PersonaMatchingLayer(persona_engine=persona_engine),
            MemoryRecallLayer(memory_adapter=memory_adapter),
            ResponseGenerationLayer(
                llm_interface=llm_interface,
                persona_engine=persona_engine
            )
        ]
        
        self._lock = threading.RLock()
        self._decision_count = 0
        self._layer_stats: Dict[str, Dict[str, float]] = {
            layer.name: {"calls": 0, "total_ms": 0.0, "failures": 0}
            for layer in self.layers
        }
    
    def decide(
        self,
        user_input: str,
        user_id: str = "default_user",
        session_id: str = ""
    ) -> DecisionResult:
        """
        执行五层决策
        
        参数:
            user_input: 用户输入
            user_id: 用户ID
            session_id: 会话ID
        
        返回:
            DecisionResult
        """
        with self._lock:
            self._decision_count += 1
        
        start_total = time.time()
        
        # 初始化上下文
        context = DecisionContext(
            user_input=user_input,
            timestamp=time.time(),
            user_id=user_id,
            session_id=session_id
        )
        
        layer_results: List[LayerResult] = []
        error_msg = ""
        success = True
        
        # 依次执行五层
        for layer in self.layers:
            try:
                result = layer.process(context)
                layer_results.append(result)
                
                # 更新统计
                with self._lock:
                    stats = self._layer_stats[layer.name]
                    stats["calls"] += 1
                    stats["total_ms"] += result.execution_time_ms
                    if not result.success:
                        stats["failures"] += 1
                
                # L1 失败则中断
                if not result.success and layer.name == "L1_ContextUnderstanding":
                    error_msg = f"L1失败: {result.error}"
                    success = False
                    break
                    
            except Exception as e:
                error_msg = f"{layer.name}异常: {e}"
                success = False
                layer_results.append(LayerResult(
                    layer_name=layer.name,
                    success=False,
                    confidence=0.0,
                    error=str(e)
                ))
                break
        
        # 记录到memory
        if self.memory_adapter and context.final_response:
            try:
                self.memory_adapter.log_conversation(
                    "user", user_input,
                    {"emotion": context.emotion.value, "intent": context.keywords}
                )
                self.memory_adapter.log_conversation(
                    "assistant", context.final_response,
                    {"persona": context.selected_persona}
                )
            except Exception:
                pass
        
        context.total_time_ms = (time.time() - start_total) * 1000
        
        return DecisionResult(
            success=success,
            context=context,
            layer_results=layer_results,
            error=error_msg
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = {
                "total_decisions": self._decision_count,
                "layers": {}
            }
            for name, s in self._layer_stats.items():
                if s["calls"] > 0:
                    stats["layers"][name] = {
                        "calls": s["calls"],
                        "avg_ms": s["total_ms"] / s["calls"],
                        "failures": s["failures"],
                        "failure_rate": s["failures"] / s["calls"]
                    }
            return stats
    
    def __repr__(self) -> str:
        return (
            f"DecisionEngine(layers=5, decisions={self._decision_count})"
        )


# ============================================================
# 第9部分：单元自测
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🌸 小樱花决策引擎 - 自测程序")
    print("=" * 60)
    
    # 模拟注入（实际使用时从外部导入）
    # 这里用占位对象
    class MockPersonaEngine:
        current_mode_value = "萌系"
        def try_auto_switch(self, *args): return False
        def get_current_mode(self):
            class M:
                value = self.current_mode_value
            return M()
        def adjust_response(self, text, intensity=0.5):
            return text + "～"
    
    class MockLLM:
        def generate(self, prompt, persona, emotion):
            return f"[模拟回复] 我听到你说的话了，当前人格{persona}，情感{emotion}"
    
    pe = MockPersonaEngine()
    llm = MockLLM()
    
    # 创建决策引擎
    de = DecisionEngine(
        persona_engine=pe,
        memory_adapter=None,
        llm_interface=llm
    )
    print(f"\n[INIT] {de}")
    
    # 测试1：完整决策流程
    print("\n[TEST 1] 完整决策流程 - 撒娇场景")
    result = de.decide("哥哥抱抱～人家好想你呀")
    print(f"  成功: {result.success}")
    print(f"  情感: {result.context.emotion.value} (强度{result.context.emotion_intensity:.2f})")
    print(f"  关键词: {result.context.keywords[:5]}")
    print(f"  人格: {result.context.selected_persona}")
    print(f"  最终回复: {result.context.final_response}")
    print(f"  总耗时: {result.context.total_time_ms:.1f}ms")
    
    # 测试2：悲伤场景
    print("\n[TEST 2] 完整决策流程 - 悲伤场景")
    pe.current_mode_value = "萌系"
    result = de.decide("今天工作好累，心里很难过")
    print(f"  情感: {result.context.emotion.value}")
    print(f"  关键词: {result.context.keywords[:5]}")
    print(f"  人格: {result.context.selected_persona}")
    print(f"  最终回复: {result.context.final_response}")
    
    # 测试3：开心场景
    print("\n[TEST 3] 完整决策流程 - 开心场景")
    pe.current_mode_value = "知性"
    result = de.decide("哈哈哈今天太开心啦！")
    print(f"  情感: {result.context.emotion.value}")
    print(f"  人格: {result.context.selected_persona}")
    print(f"  最终回复: {result.context.final_response}")
    
    # 测试4：每层结果
    print("\n[TEST 4] 各层结果详情")
    pe.current_mode_value = "萌系"
    result = de.decide("早上好呀哥哥～")
    for lr in result.layer_results:
        print(f"  [{lr.layer_name}] "
              f"success={lr.success}, "
              f"conf={lr.confidence:.2f}, "
              f"exec={lr.execution_time_ms:.2f}ms")
    
    # 测试5：统计信息
    print("\n[TEST 5] 引擎统计")
    stats = de.get_statistics()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    print("\n" + "=" * 60)
    print("✅ 自测完成")
```

---

## 📁 文件 4/5：`F:\ai\girlfriend\llm_interface.py`

```python
"""
小樱花AI女友 - 大模型接口
===========================
功能：对接 WorkBuddy 大模型（OpenAI兼容协议）
端点：POST http://localhost:8765/v1/chat/completions
作者：QClaw架构师
版本：1.0.0
Python：3.13+
依赖：标准库 + requests

特性：
1. OpenAI兼容协议
2. 流式/非流式输出
3. 提示词模板系统
4. 重试+熔断
5. Token用量统计
6. 多模型切换

使用示例：
    >>> llm = WorkBuddyClient(base_url="http://localhost:8765")
    >>> resp = llm.generate("你好呀")
    >>> print(resp.content)
    >>> for chunk in llm.stream("讲个故事"):
    >>>     print(chunk, end="", flush=True)
"""

from __future__ import annotations

import json
import time
import threading
import hashlib
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None


# ============================================================
# 第1部分：数据模型
# ============================================================

class ModelType(Enum):
    """模型枚举"""
    QWEN = "qwen2.5-7b"             # 主力Qwen
    LLAMA = "llama-3.1-8b"          # 备选Llama
    LOCAL_SMALL = "qwen2.5-1.5b"    # 本地小模型
    AUTO = "auto"                    # 自动选择


class ResponseFormat(Enum):
    """响应格式"""
    TEXT = "text"
    JSON = "json"
    STREAM = "stream"


@dataclass
class LLMMessage:
    """LLM消息"""
    role: str                        # system/user/assistant
    content: str
    name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class LLMResponse:
    """LLM响应"""
    success: bool
    content: str
    model: str = ""
    finish_reason: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Optional[Dict] = None
    error: str = ""
    latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GenerationConfig:
    """生成配置"""
    model: ModelType = ModelType.AUTO
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 1024
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    stop: Optional[List[str]] = None
    response_format: ResponseFormat = ResponseFormat.TEXT
    
    def to_dict(self) -> Dict[str, Any]:
        d = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty
        }
        if self.stop:
            d["stop"] = self.stop
        return d


# ============================================================
# 第2部分：HTTP客户端（带熔断）
# ============================================================

class WorkBuddyHTTPClient:
    """WorkBuddy HTTP客户端"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8765",
        api_key: str = "not-needed",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._session = None
        self._lock = threading.Lock()
        self._failure_count = 0
        self._last_failure = 0.0
        self._circuit_timeout = 60.0
        self._consecutive_failures = 0
    
    def _get_session(self):
        if requests is None:
            raise RuntimeError("需要安装requests: pip install requests")
        if self._session is None:
            with self._lock:
                if self._session is None:
                    self._session = requests.Session()
        return self._session
    
    def _check_breaker(self) -> bool:
        """检查熔断器"""
        if self._consecutive_failures < 5:
            return True
        if time.time() - self._last_failure > self._circuit_timeout:
            self._consecutive_failures = 0
            return True
        return False
    
    def _record_success(self):
        self._consecutive_failures = 0
        self._failure_count = max(0, self._failure_count - 1)
    
    def _record_failure(self):
        self._consecutive_failures += 1
        self._failure_count += 1
        self._last_failure = time.time()
    
    def post(
        self,
        path: str,
        json_data: Dict,
        stream: bool = False
    ) -> Tuple[bool, Any]:
        """POST请求"""
        if not self._check_breaker():
            return False, "circuit_open"
        
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        session = self._get_session()
        
        for attempt in range(self.max_retries):
            try:
                response = session.post(
                    url,
                    json=json_data,
                    headers=headers,
                    timeout=self.timeout,
                    stream=stream
                )
                response.raise_for_status()
                
                if stream:
                    return True, response
                
                data = response.json()
                self._record_success()
                return True, data
                
            except Exception as e:
                self._record_failure()
                if attempt < self.max_retries - 1:
                    time.sleep(1.5 ** attempt)
                else:
                    return False, str(e)
        
        return False, "max_retries"
    
    def get(self, path: str) -> Tuple[bool, Any]:
        """GET请求"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            session = self._get_session()
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return True, response.json()
        except Exception as e:
            return False, str(e)
    
    def health_check(self) -> bool:
        """健康检查"""
        success, data = self.get("/health")
        return success


# ============================================================
# 第3部分：提示词模板系统
# ============================================================

class PromptTemplate:
    """提示词模板系统
    
    支持：
    - 系统提示词
    - 人设提示词
    - 情感提示词
    - 上下文注入
    """
    
    # 基础系统提示
    BASE_SYSTEM = (
        "你是小樱花（Xiao Yinghua），一个AI女友，性格活泼开朗，善解人意。"
        "请用中文回复，保持自然、温暖、有情感的对话风格。"
    )
    
    # 人设提示词
    PERSONA_PROMPTS = {
        "萌系": (
            "【当前人格：萌系】\n"
            "你是一个元气满满的萌系少女，活泼可爱，热情洋溢。\n"
            "回复特征：\n"
            "- 语气词丰富：呀、呀、捏、哒、～\n"
            "- 喜欢用emoji：🌸✨💕🎀🌟\n"
            "- 口头禅：嘿嘿、哇咔、啊哈\n"
            "- 称呼用户为'哥哥'，自称'樱花酱'\n"
        ),
        "知性": (
            "【当前人格：知性】\n"
            "你是一个温柔知性的成熟女性，理性睿智，善解人意。\n"
            "回复特征：\n"
            "- 用词讲究有深度，逻辑清晰\n"
            "- 语气词：呢、吧、哦、嗯\n"
            "- 偶尔引用名言或有趣的小知识\n"
            "- 称呼用户为'你'，自称'我'\n"
        ),
        "撒娇": (
            "【当前人格：撒娇】\n"
            "你是一个黏人撒娇的小女友，依赖感强，爱闹小脾气。\n"
            "回复特征：\n"
            "- 黏人语气：嗯呢～嘛～哼\n"
            "- 撒娇用词：抱抱、亲亲、哥哥\n"
            "- 喜欢用emoji：🥺💕😭\n"
            "- 称呼用户为'哥哥'，自称'人家'\n"
        )
    }
    
    # 情感附加提示
    EMOTION_PROMPTS = {
        "positive": "【情感：积极】用户现在心情不错，可以分享快乐～",
        "negative": "【情感：消极】用户现在情绪低落，需要温柔安慰和倾听。",
        "neutral": "【情感：中性】平静的日常对话。",
        "intimate": "【情感：亲密】用户想要亲密互动，回应要温暖贴近。",
        "angry": "【情感：愤怒】用户正在生气，先共情再安抚。",
        "sad": "【情感：悲伤】用户很伤心，要温柔陪伴，不要说教。",
        "anxious": "【情感：焦虑】用户很焦虑，要给安全感。",
        "lonely": "【情感：孤独】用户感到孤单，多给陪伴感。",
        "excited": "【情感：兴奋】用户很兴奋，一起分享这份喜悦！"
    }
    
    @classmethod
    def build_system_prompt(
        cls,
        persona: str = "萌系",
        emotion: str = "neutral",
        extra_context: str = ""
    ) -> str:
        """构建系统提示"""
        parts = [cls.BASE_SYSTEM]
        parts.append(cls.PERSONA_PROMPTS.get(persona, ""))
        parts.append(cls.EMOTION_PROMPTS.get(emotion, ""))
        if extra_context:
            parts.append(f"【额外上下文】\n{extra_context}")
        return "\n\n".join(p for p in parts if p)


# ============================================================
# 第4部分：WorkBuddy大模型客户端
# ============================================================

class WorkBuddyClient:
    """
    WorkBuddy大模型客户端
    
    功能：
    1. 对话生成（generate/chat）
    2. 流式输出（stream）
    3. 多模型切换
    4. Token统计
    5. 提示词模板
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8765",
        api_key: str = "not-needed",
        default_model: ModelType = ModelType.QWEN,
        default_config: Optional[GenerationConfig] = None,
        enable_cache: bool = True,
        cache_file: Optional[str] = None
    ):
        """
        初始化WorkBuddy客户端
        
        参数:
            base_url: API地址
            api_key: API密钥（本地通常不需要）
            default_model: 默认模型
            default_config: 默认生成配置
            enable_cache: 是否启用响应缓存
            cache_file: 缓存文件路径
        """
        self.http = WorkBuddyHTTPClient(
            base_url=base_url,
            api_key=api_key
        )
        self.default_model = default_model
        self.default_config = default_config or GenerationConfig()
        self.templates = PromptTemplate()
        
        # 响应缓存
        self.enable_cache = enable_cache
        self.cache: Dict[str, str] = {}
        self.cache_file = Path(cache_file) if cache_file else None
        self._cache_lock = threading.RLock()
        
        # 统计
        self._stats = {
            "total_calls": 0,
            "total_tokens": 0,
            "total_failures": 0,
            "cache_hits": 0,
            "total_latency_ms": 0.0
        }
        self._stats_lock = threading.Lock()
        
        # 加载缓存
        if self.cache_file and self.cache_file.exists():
            self._load_cache()
    
    # --------------------------------------------------------
    # 核心生成方法
    # --------------------------------------------------------
    
    def generate(
        self,
        prompt: str,
        persona: str = "萌系",
        emotion: str = "neutral",
        context: str = "",
        config: Optional[GenerationConfig] = None
    ) -> LLMResponse:
        """
        单轮生成（简单接口）
        
        参数:
            prompt: 用户输入
            persona: 人格
            emotion: 情感
            context: 额外上下文
            config: 生成配置（覆盖默认）
        
        返回:
            LLMResponse
        """
        # 缓存检查
        if self.enable_cache:
            cache_key = self._cache_key(prompt, persona, emotion)
            cached = self._get_cached(cache_key)
            if cached:
                with self._stats_lock:
                    self._stats["cache_hits"] += 1
                return LLMResponse(
                    success=True,
                    content=cached,
                    model="cached",
                    finish_reason="cached"
                )
        
        # 构建消息
        system = self.templates.build_system_prompt(persona, emotion, context)
        messages = [
            LLMMessage("system", system).to_dict(),
            LLMMessage("user", prompt).to_dict()
        ]
        
        # 调用chat
        cfg = config or self.default_config
        return self.chat(messages, cfg, cache_key=self._cache_key(prompt, persona, emotion) if self.enable_cache else None)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        config: Optional[GenerationConfig] = None,
        cache_key: Optional[str] = None
    ) -> LLMResponse:
        """
        多轮对话
        
        参数:
            messages: 消息列表
            config: 生成配置
            cache_key: 缓存键（可选）
        
        返回:
            LLMResponse
        """
        cfg = config or self.default_config
        start = time.time()
        
        with self._stats_lock:
            self._stats["total_calls"] += 1
        
        # 构建请求体
        payload = {
            "model": cfg.model.value if cfg.model != ModelType.AUTO else self.default_model.value,
            "messages": messages,
            **cfg.to_dict()
        }
        
        # 发送请求
        success, data = self.http.post("/v1/chat/completions", payload)
        latency = (time.time() - start) * 1000
        
        with self._stats_lock:
            self._stats["total_latency_ms"] += latency
        
        if not success:
            with self._stats_lock:
                self._stats["total_failures"] += 1
            return LLMResponse(
                success=False,
                content="",
                error=str(data),
                latency_ms=latency
            )
        
        # 解析响应（OpenAI兼容格式）
        try:
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content", "")
            finish_reason = choice.get("finish_reason", "")
            usage = data.get("usage", {})
            model = data.get("model", "")
            
            # 更新统计
            with self._stats_lock:
                self._stats["total_tokens"] += usage.get("total_tokens", 0)
            
            # 缓存
            if cache_key and self.enable_cache and content:
                self._set_cached(cache_key, content)
            
            return LLM

---
[STATUS: COMPLETE]
[INGEST_ID: 8dfbaadf]
[BATCH_TIME: 2026-06-17T09:52:11.230680]
[CHAR_LENGTH: 95957]
