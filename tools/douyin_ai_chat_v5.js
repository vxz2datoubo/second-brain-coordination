/**
 * Douyin AI Chat v5 - 直接 AI 页面，带完整上下文
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const VIDEO_ID = '7650106006073502949';
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUTPUT_DIR = 'F:/ai/tools/screenshots';

// 先通过视频页面获取 cookie 和 user_id
const PROMPT = `把视频完全文案发给我，接着根据文案和视频内容整合出文案+资料+背景+视频中出现的错误或偏见或者在其他条件情况会有不同结果的内容一并整理出来，然后再单独另外整合的该内容下的所有评价然后分析整体视频和评价的矛盾点在哪，还有需求点在哪，可挖掘的市场或者可着重表现的点在哪等。如果画面中有重要图片请提取图片中的文案下来，画面中出现的文案也要全部提取下来。`;

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    viewport: { width: 1920, height: 1080 },
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });

  const page = await context.newPage();
  
  // ===== 步骤1: 先访问视频页建立上下文 =====
  console.log('=== 1. 访问视频页建立上下文 ===');
  await page.goto(`https://www.douyin.com/video/${VIDEO_ID}`, { 
    waitUntil: 'domcontentloaded', timeout: 30000 
  });
  await sleep(5000);
  
  // 获取 user_id
  const userId = await page.evaluate(() => {
    // 尝试从各种来源获取
    const match = document.cookie.match(/passport_csrf_token=([^;]+)/);
    const uid = document.cookie.match(/uid=([^;]+)/) || document.cookie.match(/user_id=([^;]+)/);
    return uid ? uid[1] : '';
  });
  console.log(`user_id from cookie: ${userId || '未获取'}`);
  
  // 获取 device_id
  const deviceId = await page.evaluate(() => {
    const match = document.cookie.match(/device_id=([^;]+)/);
    return match ? match[1] : '7651518205098608143';
  });
  console.log(`device_id: ${deviceId}`);
  
  // ===== 步骤2: 导航到 AI 页面 =====
  console.log('\n=== 2. 导航到 AI 页面 ===');
  
  const aiUrl = `https://so-landing.douyin.com/search_ai_mobile/pc?aid=6383&device_id=${deviceId}&ai_search_req_patch=${encodeURIComponent(JSON.stringify({ai_search_enter_from_group_id: VIDEO_ID, enter_from: 'video_detail'}))}&enter_from=video_detail`;
  
  await page.goto(aiUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  console.log('AI页面已加载，等待渲染...');
  await sleep(10000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v5_01_loaded.png') });
  
  // 检查页面内容
  const pageText = await page.evaluate(() => document.body?.innerText?.substring(0, 600) || '');
  console.log(`页面内容:\n${pageText.substring(0, 400)}`);
  
  // ===== 步骤3: 深度思考 (先不点，先看看有没有用) =====
  console.log('\n=== 3. 深度思考 ===');
  
  const deepButtons = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const text = el.textContent?.trim() || '';
        return text === '深度思考' && el.children.length === 0;
      })
      .map(el => ({
        tag: el.tagName,
        cls: el.className?.substring(0, 80),
        text: el.textContent?.trim(),
        x: Math.round(el.getBoundingClientRect().x),
        y: Math.round(el.getBoundingClientRect().y)
      }));
  });
  
  console.log(`深度思考按钮: ${deepButtons.length}`);
  for (const b of deepButtons) {
    console.log(`  <${b.tag}> [${b.x},${b.y}] "${b.text}"`);
  }
  
  // 点击深度思考
  if (deepButtons.length > 0) {
    await page.mouse.click(deepButtons[0].x + 5, deepButtons[0].y + 5);
    console.log('✅ 深度思考已点击');
    await sleep(2000);
  }
  
  // ===== 步骤4: 输入 =====
  console.log('\n=== 4. 输入提示词 ===');
  
  const inputs = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('[contenteditable="true"]'))
      .map(el => ({
        x: Math.round(el.getBoundingClientRect().x),
        y: Math.round(el.getBoundingClientRect().y),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height)
      }));
  });
  
  console.log(`contenteditable: ${inputs.length} 个`);
  
  if (inputs.length > 0) {
    const inp = page.locator('[contenteditable="true"]').first();
    await inp.click();
    await sleep(500);
    await inp.fill(PROMPT);
    console.log('✅ 已输入');
  } else {
    // 尝试 textarea
    const ta = page.locator('textarea').first();
    await ta.fill(PROMPT);
    console.log('✅ 已输入(textarea)');
  }
  
  await sleep(1000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v5_02_prompt.png') });
  
  // ===== 步骤5: 发送 =====
  console.log('\n=== 5. 发送 ===');
  
  // 找发送按钮
  const sendBtns = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const text = (el.textContent?.trim() || '');
        const cls = (el.className?.toString() || '');
        return (text === '发送' || text === '→' || cls.includes('send-btn') || cls.includes('submit-btn')) && 
               el.getBoundingClientRect().width > 0;
      })
      .map(el => ({
        tag: el.tagName,
        text: el.textContent?.trim(),
        cls: el.className?.substring(0, 80),
        x: Math.round(el.getBoundingClientRect().x),
        y: Math.round(el.getBoundingClientRect().y)
      }));
  });
  
  console.log(`发送按钮: ${sendBtns.length}`);
  for (const b of sendBtns) {
    console.log(`  <${b.tag}> [${b.x},${b.y}] "${b.text}" class="${b.cls}"`);
  }
  
  if (sendBtns.length > 0) {
    await page.mouse.click(sendBtns[0].x + 5, sendBtns[0].y + 5);
    console.log('✅ 点击发送');
  } else {
    await page.keyboard.press('Enter');
    console.log('✅ Enter发送');
  }
  
  await sleep(3000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v5_03_sent.png') });
  
  // ===== 步骤6: 等待回复 =====
  console.log('\n=== 6. 等待回复（120秒）===');
  
  let lastFinal = '';
  for (let i = 0; i < 120; i++) {
    await sleep(1000);
    
    const current = await page.evaluate(() => {
      // 找AI消息 - 排除用户输入
      let best = { text: '', len: 0 };
      
      // 策略: 找所有可见的大段文字块
      document.querySelectorAll('div, section, article').forEach(el => {
        const t = el.innerText?.trim() || '';
        const cls = (el.className?.toString() || '').toLowerCase();
        // 排除导航、头部等
        if (!cls.includes('nav') && !cls.includes('header') && !cls.includes('footer') && !cls.includes('sidebar')) {
          if (t.length > best.len && t.length < 100000) {
            best = { text: t, len: t.length };
          }
        }
      });
      
      return best;
    });
    
    if (i % 10 === 0) console.log(`  [${i}s] 内容: ${current.len} 字符`);
    
    // 检测完成 (内容 > 1000 且稳定 5秒)
    if (current.len > 1000 && current.text === lastFinal && i > 10) {
      console.log(`✅ 回复稳定: ${current.len} 字符`);
      break;
    }
    lastFinal = current.text;
  }
  
  await sleep(3000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v5_04_done.png') });
  
  // ===== 提取 =====
  console.log('\n=== 7. 提取最终内容 ===');
  
  const finalReply = await page.evaluate(() => {
    let best = '';
    document.querySelectorAll('div, section').forEach(el => {
      const t = el.innerText?.trim() || '';
      if (t.length > best.length && t.length < 100000) best = t;
    });
    return best;
  });
  
  console.log(`总长度: ${finalReply.length} 字符`);
  
  const outPath = path.join(OUTPUT_DIR, 'v5_ai_reply.md');
  fs.writeFileSync(outPath, `# AI 回复\n\n${finalReply}`);
  console.log(`✅ 保存: ${outPath}`);
  
  // 预览
  console.log('\n=== 内容预览 ===');
  console.log(finalReply.substring(0, 800));
  console.log('...');
  
  console.log('\n浏览器保持打开 60 秒...');
  await sleep(60000);
  await context.close();
})();
