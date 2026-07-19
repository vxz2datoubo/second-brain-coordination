# -*- coding: utf-8 -*-
"""self_test.py - 每日自检验系统

验证策略有效性，驱动进化。
"""

import json, os
from datetime import datetime

BASE = r"F:\aidanao"


def load_lessons() -> list:
    path = os.path.join(BASE, "second-brain", "lessons.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def self_check() -> dict:
    lessons = load_lessons()
    negative_count = lessons.count("教训:")
    positive_count = lessons.count("经验:")
    return {
        "timestamp": datetime.now().isoformat(),
        "negative_lessons": negative_count,
        "positive_experiences": positive_count,
        "status": "REVIEW" if negative_count > positive_count else "OK",
        "recommendation": "CONTINUE",
    }


if __name__ == "__main__":
    print(json.dumps(self_check(), ensure_ascii=False, indent=2))
