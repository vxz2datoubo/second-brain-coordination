import urllib.request, json

text = r"""QClaw 端口动态（每次启动会变），加固措施：
1) 端口从 C:\Users\Administrator\.qclaw\qclaw.json 动态读取，不写死
2) 每次调用前 ping /v1/models 做健康检查，不通直接 RuntimeError 不闷头撞墙
3) token 也从配置读，读不到用常量兜底
4) QClaw 硬规则（不调 Agent / 不管理项目 / 不读写自己文件系统）写入技能 qclaw-bridge/SKILL.md
5) 触发规则：波仔输入以 q:（半角）开头才调用

代码：F:\ai\core\qclaw.py v2
技能路径：C:\Users\Administrator\.workbuddy\skills\qclaw-bridge\SKILL.md
"""

data = json.dumps({
    'title': 'QClaw加固-v2-动态端口探测',
    'text': text,
    'tags': 'QClaw,加固,动态端口,健康检查,技能',
    'source': 'workbuddy-memory'
}).encode('utf-8')
req = urllib.request.Request('http://localhost:8766/api/digest/text', data=data, headers={'Content-Type': 'application/json'})
print(json.loads(urllib.request.urlopen(req, timeout=5).read()))
