/**
 * Douyin "问AI" 按钮定位脚本
 * 目标: 在 jingxuan 页面找到所有可能的 "问AI" 按钮并点击
 */
const { chromium } = require('playwright');
const path = require('path');

const VIDEO_ID = '7650106006073502949';
const URL = `https://www.douyin.com/jingxuan?modal_id=${VIDEO_ID}`;
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUTPUT_DIR = 'F:/ai/tools/screenshots';

const fs = require('fs');
if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR, { recursive: true });

(async () => {
  // 使用持久化上下文 - 保持登录态
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    viewport: { width: 1920, height: 1080 },
    args: [
      '--disable-blink-features=AutomationControlled',
      '--no-sandbox'
    ]
  });

  const page = await context.newPage();
  
  console.log('=== 导航到 jingxuan 页面 ===');
  await page.goto(URL, { 
    waitUntil: 'domcontentloaded', 
    timeout: 60000 
  });
  
  // 等待页面内容加载 - 尝试等视频元素或内容区域出现
  console.log('等待页面内容加载...');
  try {
    await page.waitForSelector('video, [class*="player"], [class*="video"], [class*="content"], [class*="detail"]', { timeout: 15000 });
    console.log('页面内容区域已加载');
  } catch(e) {
    console.log('未检测到典型内容元素，继续...');
  }
  
  // 额外等待
  await page.waitForTimeout(5000);
  
  console.log('=== 页面标题 ===');
  console.log(await page.title());
  
  // 截图全页
  await page.screenshot({ 
    path: path.join(OUTPUT_DIR, 'full_page.png'), 
    fullPage: false 
  });
  console.log('全页截图已保存: full_page.png');
  
  // ===== 方法1: 搜索所有包含 "问AI" 或 "AI" 的文本元素 =====
  console.log('\n=== 方法1: 搜索包含 "问AI"/"AI"/"问" 的文本 ===');
  
  const keywords = ['问AI', '问 AI', 'AI', '问一问', '问问AI', 'AI视频', '智能'];
  for (const kw of keywords) {
    const elements = page.locator(`text="${kw}"`);
    const count = await elements.count();
    if (count > 0) {
      console.log(`  找到 ${count} 个包含 "${kw}" 的元素`);
      for (let i = 0; i < Math.min(count, 5); i++) {
        const el = elements.nth(i);
        const text = await el.textContent().catch(() => 'N/A');
        const tag = await el.evaluate(e => e.tagName).catch(() => 'N/A');
        const cls = await el.evaluate(e => e.className).catch(() => 'N/A');
        const visible = await el.isVisible().catch(() => false);
        console.log(`    [${i}] tag=${tag} class="${cls}" visible=${visible} text="${text?.substring(0, 100)}"`);
      }
    }
  }
  
  // ===== 方法2: 用 role=button 搜索 =====
  console.log('\n=== 方法2: 搜索 button 角色中可能的相关按钮 ===');
  
  const allButtons = page.locator('button, [role="button"], span[class*="btn"], div[class*="btn"]');
  const btnCount = await allButtons.count();
  console.log(`  总共有 ${btnCount} 个可能的按钮元素`);
  
  // 只检查前100个
  for (let i = 0; i < Math.min(btnCount, 100); i++) {
    const btn = allButtons.nth(i);
    const text = await btn.textContent().catch(() => '');
    if (text && (text.includes('AI') || text.includes('问') || text.includes('智能'))) {
      const visible = await btn.isVisible().catch(() => false);
      const tag = await btn.evaluate(e => e.tagName).catch(() => 'N/A');
      const cls = await btn.evaluate(e => e.className).catch(() => 'N/A');
      const html = await btn.evaluate(e => e.outerHTML.substring(0, 300)).catch(() => 'N/A');
      console.log(`  [${i}] tag=${tag} class="${cls}" visible=${visible}`);
      console.log(`       text="${text.substring(0, 150)}"`);
      console.log(`       html="${html}"`);
    }
  }
  
  // ===== 方法3: 搜索 class 名中包含 ai 的元素 =====
  console.log('\n=== 方法3: 搜索 class 中包含 "ai" 的元素 ===');
  
  const aiElements = page.locator('[class*="ai" i], [class*="AI"], [id*="ai" i], [id*="AI"]');
  const aiCount = await aiElements.count();
  console.log(`  找到 ${aiCount} 个 class/id 包含 "ai" 的元素`);
  
  for (let i = 0; i < Math.min(aiCount, 20); i++) {
    const el = aiElements.nth(i);
    const visible = await el.isVisible().catch(() => false);
    if (visible) {
      const text = await el.textContent().catch(() => 'N/A');
      const tag = await el.evaluate(e => e.tagName).catch(() => 'N/A');
      const cls = await el.evaluate(e => e.className).catch(() => 'N/A');
      console.log(`  [${i}] tag=${tag} class="${cls}" text="${text?.substring(0, 150)}"`);
    }
  }
  
  // ===== 方法4: 搜索作者头像附近的元素 =====
  console.log('\n=== 方法4: 搜索作者信息区域附近 ===');
  
  // 看看有没有 author/creator 相关元素
  const authorSelectors = [
    '[class*="author"]',
    '[class*="creator"]',
    '[class*="user-info"]',
    '[class*="UserInfo"]',
    '[class*="profile"]',
    'img[class*="avatar"]',
    '[class*="Avatar"]'
  ];
  
  for (const sel of authorSelectors) {
    const els = page.locator(sel);
    const count = await els.count();
    if (count > 0) {
      console.log(`  选择器 "${sel}" 找到 ${count} 个元素`);
      for (let i = 0; i < Math.min(count, 3); i++) {
        const el = els.nth(i);
        const visible = await el.isVisible().catch(() => false);
        const text = await el.textContent().catch(() => 'N/A');
        const tag = await el.evaluate(e => e.tagName).catch(() => 'N/A');
        console.log(`    [${i}] ${tag} visible=${visible} text="${text?.substring(0, 100)}"`);
        
        // 截图这个元素
        if (visible) {
          try {
            await el.screenshot({ path: path.join(OUTPUT_DIR, `author_${sel.replace(/[^a-z]/gi, '_')}_${i}.png`) });
          } catch(e) {}
        }
      }
    }
  }
  
  // ===== 方法5: 搜索评论区标签页 =====
  console.log('\n=== 方法5: 搜索评论区/标签页区域 ===');
  
  const tabsSelectors = [
    '[class*="tab"]',
    '[class*="Tab"]',
    '[role="tab"]',
    '[role="tablist"]',
    '[class*="comment"]',
    '[class*="Comment"]'
  ];
  
  for (const sel of tabsSelectors) {
    const els = page.locator(sel);
    const count = await els.count();
    if (count > 0) {
      console.log(`  选择器 "${sel}" 找到 ${count} 个元素`);
      for (let i = 0; i < Math.min(count, 5); i++) {
        const el = els.nth(i);
        const visible = await el.isVisible().catch(() => false);
        if (visible) {
          const text = await el.textContent().catch(() => 'N/A');
          console.log(`    [${i}] text="${text?.substring(0, 200)}"`);
        }
      }
    }
  }
  
  // ===== 方法6: 直接执行 JS 搜索所有可能包含 "问AI" 的 DOM 节点 =====
  console.log('\n=== 方法6: 深度 JS DOM 搜索 ===');
  
  const jsResults = await page.evaluate(() => {
    const results = [];
    
    // 搜索所有文本节点和元素
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
      {
        acceptNode: (node) => {
          if (node.nodeType === Node.TEXT_NODE) {
            const t = node.textContent || '';
            if (t.includes('AI') || t.includes('问') || t.includes('智能')) {
              return NodeFilter.FILTER_ACCEPT;
            }
          }
          return NodeFilter.FILTER_SKIP;
        }
      }
    );
    
    let count = 0;
    while (walker.nextNode() && count < 50) {
      const node = walker.currentNode;
      const text = (node.textContent || '').trim();
      if (text && text.length > 1) {
        const parent = node.parentElement;
        const tag = parent ? parent.tagName : 'TEXT';
        const cls = parent ? parent.className : '';
        const id = parent ? parent.id : '';
        const rect = parent ? parent.getBoundingClientRect() : null;
        
        results.push({
          tag,
          cls: typeof cls === 'string' ? cls.substring(0, 100) : String(cls).substring(0, 100),
          id,
          text: text.substring(0, 200),
          visible: rect ? (rect.width > 0 && rect.height > 0) : false,
          x: rect ? Math.round(rect.x) : 0,
          y: rect ? Math.round(rect.y) : 0
        });
        count++;
      }
    }
    
    return results;
  });
  
  for (const r of jsResults) {
    console.log(`  [${r.x},${r.y}] <${r.tag}> class="${r.cls}" visible=${r.visible}`);
    console.log(`       text="${r.text}"`);
  }
  
  // ===== 方法7: 打印页面的主要结构 =====
  console.log('\n=== 方法7: 页面主要结构 ===');
  
  const structure = await page.evaluate(() => {
    const mainSelectors = [
      '#root', '[class*="App"]', 'main', '[class*="main"]',
      '[class*="video"]', '[class*="player"]', '[class*="detail"]',
      '[class*="side"]', '[class*="right"]', '[class*="left"]'
    ];
    
    const found = [];
    for (const sel of mainSelectors) {
      const els = document.querySelectorAll(sel);
      els.forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width > 50) {
          found.push({
            selector: sel,
            tag: el.tagName,
            cls: el.className?.substring?.(0, 80) || '',
            w: Math.round(rect.width),
            h: Math.round(rect.height)
          });
        }
      });
    }
    return found;
  });
  
  for (const s of structure) {
    console.log(`  ${s.selector} -> <${s.tag}> class="${s.cls}" ${s.w}x${s.h}`);
  }
  
  console.log('\n=== 探索完成 ===');
  console.log(`截图保存在: ${OUTPUT_DIR}`);
  
  // 保持浏览器打开让用户查看
  console.log('\n浏览器保持打开状态，按 Ctrl+C 关闭...');
  
  // 等待30秒后自动关闭(给用户时间查看)
  // 等待60秒后自动关闭
  await page.waitForTimeout(60000);
  await context.close();
})();
