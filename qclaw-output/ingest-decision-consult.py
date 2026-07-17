import urllib.request, json

text = r"""决策前自动检索系统: 迪迪每次做决策 (技术选型/方案推荐/质量标准/降级) 前, 必须自动调 core.decision_consult.before_decision(topic) 检索第二大脑的决策教训和硬规则, 而不是等波仔提醒.

工具路径: F:\ai\core\decision_consult.py
技能: C:\Users\Administrator\.workbuddy\skills\decision-consult\SKILL.md

核心机制:
1. 扩展查询词 (topic / topic 教训 / 不要 topic / topic 红线)
2. 三路检索 (教训/规则/知识) 走 /api/retrieve/search
3. 黑名单过滤自动摄入的 WorkBuddy 跨项目记忆脏数据
4. 标题前缀匹配 (教训:/机制:/原则:) 兜底识别
5. score>=5.5 或标题含"不要/切勿/严禁/红线/致命/降级" 触发警告

写教训的标准: source=decision-lesson 触发 decision-lessons 分类, 或 title 以"教训:"开头.
"""

data = json.dumps({
    'title': '决策前自动检索系统 (decision-consult)',
    'text': text,
    'tags': '决策,自动化,检索,教训,规则',
    'source': 'decision-lesson',
    'category': 'tech-ai'
}).encode('utf-8')
req = urllib.request.Request('http://localhost:8766/api/digest/text', data=data, headers={'Content-Type': 'application/json'})
print(json.loads(urllib.request.urlopen(req, timeout=5).read()))
