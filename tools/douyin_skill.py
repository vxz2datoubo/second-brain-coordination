"""
抖音视频分析技能 — Playwright采集 + QClaw分析 + 第二大脑入库
用法: python douyin_skill.py <抖音链接>

关键: 
  1. 使用持久化浏览器配置保持登录态
  2. 自动转换链接格式 → /jingxuan?modal_id= (解锁"问AI"功能)
"""
import json, time, sys, os, re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.qclaw import QClawBridge

BROWSER_PROFILE = "C:/WorkBuddy/PlaywrightProfile"

def to_jingxuan_url(url_or_share_text):
    """将各种抖音链接格式转为 /jingxuan?modal_id= 格式（解锁问AI功能）
    
    支持: v.douyin.com短链 / /video/ID / share文本 / modal_id直接
    """
    # 1. 从分享文本中提取链接
    urls = re.findall(r'https?://[^\s]+', url_or_share_text)
    url = urls[0] if urls else url_or_share_text
    
    # 2. 提取 video_id
    vid_match = re.search(r'modal_id=(\d+)', url)
    if vid_match:
        return f'https://www.douyin.com/jingxuan?modal_id={vid_match.group(1)}'
    
    vid_match = re.search(r'/video/(\d+)', url)
    if vid_match:
        return f'https://www.douyin.com/jingxuan?modal_id={vid_match.group(1)}'
    
    # 3. 短链接需解析
    return url  # 留给 Playwright 跟随重定向

# ====== 1. Playwright 采集 ======
def extract_video(url, headless=True):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_PROFILE,
            headless=headless,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1366, 'height': 768}
        )
        page = context.new_page()
        
        # video 路由直接导航（内容最完整）
        page.goto(url, timeout=20000, wait_until='domcontentloaded')
        time.sleep(3)
        
        # 短链接跟随重定向
        if 'v.douyin.com' in page.url or 'discover' in page.url:
            time.sleep(2)
        
        final = page.url
        vid = re.search(r'modal_id=(\d+)', final) or re.search(r'/video/(\d+)', final)
        
        if vid and '/video/' not in final:
            page.goto(f'https://www.douyin.com/video/{vid.group(1)}', timeout=20000, wait_until='domcontentloaded')
        
        time.sleep(5)
        
        data = {
            'title': page.title(),
            'url': page.url,
            'body': page.inner_text('body'),
            'extracted_at': datetime.now().isoformat()
        }
        
        # 提取AI章节
        body = data['body']
        chapters = []
        if '章节要点' in body:
            idx = body.index('章节要点')
            chapter_text = body[idx:idx+500]
            for line in chapter_text.split('\n'):
                line = line.strip()
                if re.match(r'\d{2}:\d{2}', line) and len(line) > 10:
                    chapters.append(line)
        data['chapters'] = chapters
        
        # 提取评论
        comment_section = ''
        if '全部评论' in body:
            ci = body.index('全部评论')
            comment_end = body.find('推荐视频', ci) if '推荐视频' in body[ci:] else len(body)
            comment_section = body[ci:comment_end][:3000]
        data['comment_text'] = comment_section
        
        # 提取互动数据
        nums = re.findall(r'(\d{1,6})\s*\n\s*(\d{1,6})\s*\n\s*(\d{1,6})\s*\n\s*(\d{1,6})', body)
        if not nums:
            nums_simple = re.findall(r'(\d{3,7})', body[:500])
            if len(nums_simple) >= 4:
                nums = [tuple(nums_simple[:4])]
        
        if nums:
            data['likes'] = int(nums[0][0])
            data['comments'] = int(nums[0][1])
            data['collects'] = int(nums[0][2])
            data['shares'] = int(nums[0][3])
        
        context.close()
        return data

# ====== 2. QClaw 分析 Prompt ======
QC_ANALYSIS_PROMPT = """你是抖音内容分析专家。基于以下抓取数据，完成三维分析：

【抓取数据】
- 标题：{title}
- AI章节/页面文案：{chapters}
- 互动：{stats}
- 热评：{comments}

═══════════════════

任务A：事实纠错 + 背景补充
对视频内容逐条核查。若有事实性陈述：
- 标注原文引用 + 正确信息 + 可变条件
- 补充相关背景资料
无错误则输出「未发现明显事实错误」。

任务B：评论洞察
- TOP5评论 + 情绪判断
- 用户核心关注点
- 评论中的矛盾/争议点
- 用户未满足的需求

任务C：市场洞察
- 选题赛道竞争分析
- 可复用的内容方法论
- 可挖掘的市场/表现机会
- 给同类创作者的启发

═══════════════════
每项3-5条要点，数据驱动。末尾 [SAVE: {filename}]"""

OUTPUT_TEMPLATE = """# 抖音分析 | {title}

> 分析时间：{datetime} | 链接：{url}

## 📊 基础数据
| 指标 | 数值 |
|------|------|
| 互动 | {stats} |

## 📝 内容摘要
{chapters_summary}

## ✅ 事实核查与背景
{fact_check}

## 💬 评论洞察
{comment_insight}

## 🔍 市场洞察
{market_insight}

---
*由迪迪+QClaw自动分析 · 第二大脑知识库*
"""

# ====== 3. 主流程 ======
def analyze_douyin(url, output_dir="F:/ai/qclaw-output"):
    print(f'[1/4] Playwright采集...')
    data = extract_video(url)
    title_short = data["title"][:50] if data.get("title") else "?"
    n_ch = len(data.get("chapters", []))
    n_cm = len(data.get("comment_text", ""))
    print("  标题: " + title_short)
    print("  章节: " + str(n_ch) + " 段")
    print("  评论: " + str(n_cm) + " 字符")
    
    print(f'[2/4] QClaw分析中...')
    qc = QClawBridge()
    
    stats_parts = []
    for k in ['likes','comments','collects','shares']:
        if k in data:
            stats_parts.append(f'{k}={data[k]}')
    stats = ', '.join(stats_parts) if stats_parts else '未知'
    
    safe_title = re.sub(r'[\\/:*?"<>|]', '', data['title'][:30])
    filename = f'抖音分析_{safe_title}_{datetime.now().strftime("%m%d-%H%M")}.md'
    
    prompt = QC_ANALYSIS_PROMPT.format(
        title=data['title'],
        chapters='\n'.join(data['chapters'][:10]) or data['body'][:1000],
        stats=stats,
        comments=data['comment_text'][:2000],
        filename=filename
    )
    
    analysis, saved_path = qc.ask(prompt, save_as=filename, max_tokens=2000, timeout=120)
    print(f'  分析: {len(analysis)} 字符')
    
    print(f'[3/4] 组装最终报告...')
    report = OUTPUT_TEMPLATE.format(
        title=data['title'],
        datetime=data['extracted_at'][:16],
        url=url,
        stats=stats,
        chapters_summary='\n'.join(data['chapters'][:5]) if data['chapters'] else data['body'][:300],
        fact_check=analysis,
        comment_insight='(见上方QClaw分析)',
        market_insight='(见上方QClaw分析)'
    )
    
    report_path = Path(output_dir) / filename
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding='utf-8')
    print(f'  报告: {report_path}')
    
    print(f'[4/4] 录入第二大脑...')
    try:
        import urllib.request
        d = json.dumps({
            'title': "抖音分析: " + data["title"][:40],
            'text': analysis[:3000],
            'source': 'douyin-skill-auto',
            'importance': 4
        }).encode('utf-8')
        req = urllib.request.Request('http://localhost:8766/api/digest/text', 
            data=d, headers={'Content-Type': 'application/json'})
        result = json.loads(urllib.request.urlopen(req, timeout=10).read())
        node_title = result.get("node", {}).get("title", "?")[:35]
        print("  ✅ 节点: " + node_title)
    except Exception as e:
        print(f'  ⚠️ 入库失败: {e}')
    
    return report_path

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python douyin_skill.py <抖音链接>')
        sys.exit(1)
    analyze_douyin(sys.argv[1])
