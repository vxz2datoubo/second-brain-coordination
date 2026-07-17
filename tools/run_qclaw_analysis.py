import sys; sys.path.insert(0,'F:/ai')
from core.qclaw import QClawBridge

qc = QClawBridge()
content, path = qc.ask(
    open('F:/ai/tools/douyin_prompt.txt','r',encoding='utf-8').read(),
    save_as='AI提示词教程分析.md',
    max_tokens=1500,
    timeout=120
)
print(qc_content[:800])
