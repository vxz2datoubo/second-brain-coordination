"""
迪迪 抖音视频分析器
通过 Chrome CDP 直接操作抖音网页版，提取视频文案
"""
import json, time, urllib.request, websocket, sys

CDP = 'http://localhost:9222'

def get_ws(target_id):
    return f'ws://localhost:9222/devtools/page/{target_id}'

def cdp_send(ws, method, params=None):
    ws.send(json.dumps({'id': 1, 'method': method, 'params': params or {}}))
    return json.loads(ws.recv())

def main(douyin_url):
    # 1. 打开抖音页面
    req = urllib.request.Request(f'{CDP}/json/new?{douyin_url}', method='PUT')
    tab = json.loads(urllib.request.urlopen(req).read())
    target_id = tab['id']
    print(f'[1] 打开页面: {target_id[:12]}')
    time.sleep(6)  # 等页面加载

    # 2. WebSocket 连接
    ws = websocket.create_connection(get_ws(target_id))
    cdp_send(ws, 'Runtime.enable')
    cdp_send(ws, 'Page.enable')
    print(f'[2] CDP 已连接')

    # 3. 滚动页面触发懒加载
    cdp_send(ws, 'Runtime.evaluate', {'expression': 'window.scrollTo(0, 300)', 'returnByValue': True})
    time.sleep(1)
    cdp_send(ws, 'Runtime.evaluate', {'expression': 'window.scrollTo(0, 0)', 'returnByValue': True})
    time.sleep(1)
    print(f'[3] 触发懒加载')

    # 4. 提取页面内容
    result = cdp_send(ws, 'Runtime.evaluate', {
        'expression': '''
        JSON.stringify({
            title: document.title,
            desc: Array.from(document.querySelectorAll('[data-e2e="video-desc"], .video-info-desc, .desc-text, [class*="desc"]')).map(e=>e.innerText).join('\\n'),
            author: Array.from(document.querySelectorAll('[data-e2e="user-info"], .author-name, [class*="author"]')).map(e=>e.innerText).join('|'),
            meta_desc: document.querySelector('meta[name="description"]')?.content || '',
            og_title: document.querySelector('meta[property="og:title"]')?.content || '',
            visible: document.body?.innerText?.substring(0, 5000) || '',
            html_title: document.title
        })
        ''',
        'returnByValue': True
    })

    val = result.get('result', {}).get('result', {}).get('value', '')
    if not val:
        print('⚠️ 未提取到内容，页面可能需要登录或反爬')
        # 试试获取纯文本
        r2 = cdp_send(ws, 'Runtime.evaluate', {
            'expression': 'document.body ? document.body.innerText.substring(0,3000) : "no body"',
            'returnByValue': True
        })
        val = r2.get('result',{}).get('result',{}).get('value','')
        print(val[:2000])
        ws.close()
        return {}
    
    try:
        data = json.loads(val)
    except:
        print(f'JSON解析失败，原始值: {str(val)[:300]}')
        ws.close()
        return {}

    print(f'[4] 提取完成')
    print('=' * 60)
    print(f'标题: {data.get("html_title", "?")}')
    print(f'作者: {data.get("author", "?")}')
    print(f'描述: {data.get("desc", "")[:500]}')
    print(f'OG标题: {data.get("og_title", "")}')
    print(f'Meta: {data.get("meta_desc", "")[:200]}')
    print('---页面文本(前2000字)---')
    print(data.get("visible", "")[:2000])
    print('=' * 60)

    ws.close()
    return data

if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.douyin.com/video/7651456171711282281'
    main(url)
