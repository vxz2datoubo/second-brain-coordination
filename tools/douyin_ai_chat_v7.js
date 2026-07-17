/**
 * Douyin AI Chat v7 - 像人一样在视频页上操作问AI
 * 关键: 不要跳转到其他页面，在视频页内完成一切
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const VIDEO_ID = '7650106006073502949';
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUTPUT_DIR = 'F:/ai/tools/screenshots';

const sleep = ms => new Promise(r => setTimeout(r, ms));

const USER_PROMPT = `把视频完全文案发给我，接着根据文案和视频内容整合出文案+资料+背景+视频中出现的错误或偏见或者在其他条件情况会有不同结果的内容一并整理出来，然后再单独另外整合的该内容下的所有评价然后分析整体视频和评价的矛盾点在哪，还有需求点在哪，可挖掘的市场或者可着重表现的点在哪等。如果画面中有重要图片请提取图片中的文案下来，画面中出现的文案也要全部提取下来。`;

(async () => {
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    viewport: { width: 1920, height: 1080 },
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });

  const page = await context.newPage();
  
  // 拦截网络请求，记录 AI 相关的响应
  const aiResponses = [];
  page.on('response', async resp => {
    const url = resp.url();
    if (url.includes('ai') || url.includes('chat') || url.includes('stream') || url.includes('conversation') || url.includes('llm') || url.includes('query') || url.includes('message')) {
      try {
        const text = await resp.text();
        if (text.length > 50 && text.length < 50000) {
          aiResponses.push({
            url: url.substring(0, 200),
            status: resp.status(),
            body: text.substring(0, 3000)
          });
        }
      } catch(e) {}
    }
  });
  
  // ===== 1. 导航到 jingxuan 页面 =====
  console.log('=== 1. 导航到 jingxuan ===');
  await page.goto(`https://www.douyin.com/jingxuan?modal_id=${VIDEO_ID}`, { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  
  // 等待视频 + 点击视频激活
  try { 
    await page.waitForSelector('video', { timeout: 15000 }); 
    console.log('视频已加载');
  } catch(e) {}
  await sleep(5000);
  try { await page.locator('video').first().click(); } catch(e) {}
  await sleep(3000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v7_01_page.png') });
  
  // ===== 2. 等待 tablist 并点击问AI =====
  console.log('\n=== 2. 点击问AI ===');
  
  let clicked = false;
  for (let i = 0; i < 30; i++) {
    try {
      const tab = page.locator('#semiTabai_card');
      const cnt = await tab.count();
      if (cnt > 0) {
        await tab.click({ timeout: 3000 });
        clicked = true;
        console.log('✅ 已点击问AI');
        break;
      }
    } catch(e) {}
    if (i % 5 === 0) console.log(`  等待tablist... [${i+1}/30]`);
    await sleep(1000);
  }
  
  if (!clicked) {
    console.log('❌ 未找到问AI标签');
    
    // 打印页面状态用于调试
    const state = await page.evaluate(() => {
      const tabs = document.querySelectorAll('[role="tab"]');
      return Array.from(tabs).map(t => ({
        text: t.textContent?.trim(),
        id: t.id,
        selected: t.getAttribute('aria-selected')
      }));
    });
    console.log('所有tab:', JSON.stringify(state));
    await context.close();
    return;
  }
  
  await sleep(8000); // 等 iframe/AI内容加载
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v7_02_clicked.png') });
  
  // ===== 3. 检查当前页面状态 =====
  console.log('\n=== 3. 检查AI面板 ===');
  
  // 当前URL是否变了？
  const currentUrl = page.url();
  console.log(`当前URL: ${currentUrl.substring(0, 100)}`);
  
  // 有什么frames？
  const frames = page.frames();
  console.log(`Frame数: ${frames.length}`);
  for (const f of frames) {
    const fu = f.url();
    if (fu.includes('ai') || fu.includes('search') || fu.includes('so-landing')) {
      console.log(`  AI Frame: ${fu.substring(0, 120)}`);
    }
  }
  
  // 面板内有什么？
  const panelState = await page.evaluate(() => {
    const panel = document.querySelector('#semiTabPanelai_card');
    if (!panel) return { error: 'panel not found' };
    
    const iframes = panel.querySelectorAll('iframe');
    const inputs = panel.querySelectorAll('[contenteditable="true"], textarea, input');
    const deepBtns = Array.from(panel.querySelectorAll('*')).filter(el => el.textContent?.trim() === '深度思考');
    
    return {
      htmlLen: panel.innerHTML.length,
      iframes: iframes.length,
      iframeSrc: iframes[0]?.src?.substring(0, 200) || '',
      inputs: inputs.length,
      deepBtns: deepBtns.length,
      text: panel.textContent?.trim()?.substring(0, 500) || ''
    };
  });
  
  console.log('面板状态:', JSON.stringify(panelState, null, 2));
  
  // ===== 4. 如果有AI iframe，切进去操作 =====
  let aiFrame = null;
  for (const f of frames) {
    if (f.url().includes('search_ai') || f.url().includes('so-landing')) {
      aiFrame = f;
      break;
    }
  }
  
  // 如果没在frame中找到，在DOM中找
  if (!aiFrame && panelState.iframes > 0) {
    const frameEl = page.frameLocator('iframe').first();
    // 这是一种frame locator，需要不同的API
  }
  
  // 如果在AI搜索页面，直接操作
  if (currentUrl.includes('search_ai') || currentUrl.includes('so-landing')) {
    console.log('\n⚠️ 页面跳转到了AI搜索页');
    // 在这个页面继续操作（需要重新获取上下文）
  }
  
  // ===== 5. 无论哪种情况，尝试在当前页面找到输入框 =====
  console.log('\n=== 5. 尝试输入 ===');
  
  // 检查所有可能的输入元素
  const allInputs = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('[contenteditable="true"], textarea, input[type="text"]:not([class*="upload"])'))
      .filter(el => el.getBoundingClientRect().width > 50)
      .map(el => ({
        tag: el.tagName,
        type: el.getAttribute('contenteditable') ? 'contenteditable' : el.tagName,
        placeholder: el.getAttribute('placeholder') || '',
        cls: el.className?.substring(0, 60),
        x: Math.round(el.getBoundingClientRect().x),
        y: Math.round(el.getBoundingClientRect().y),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height)
      }));
  });
  
  console.log(`可见输入: ${allInputs.length}`);
  for (const i of allInputs) {
    console.log(`  ${i.type} [${i.x},${i.y}] ${i.w}x${i.h} "${i.placeholder}"`);
  }
  
  // 找底部输入框 (y > 400)
  const bottomInputs = allInputs.filter(i => i.y > 400);
  
  if (bottomInputs.length === 0) {
    console.log('❌ 没有底部输入框。AI面板可能未正确加载');
    console.log('\n=== AI相关网络响应 ===');
    for (const r of aiResponses) {
      console.log(`\n[${r.status}] ${r.url}`);
      console.log(r.body.substring(0, 500));
    }
    await context.close();
    return;
  }
  
  // ===== 6. 点击深度思考 =====
  console.log('\n=== 6. 深度思考 ===');
  
  // 在当前页面/iframe 中找
  const targetPage = aiFrame || page;
  
  const deepEls = await targetPage.evaluate(() => {
    return Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const text = el.textContent?.trim() || '';
        return (text === '深度思考' || text.includes('深度')) && el.children.length === 0;
      })
      .map(el => ({
        text: el.textContent?.trim(),
        x: Math.round(el.getBoundingClientRect().x),
        y: Math.round(el.getBoundingClientRect().y),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height)
      }));
  });
  
  console.log(`深度思考: ${deepEls.length} 个`);
  for (const d of deepEls) {
    console.log(`  [${d.x},${d.y}] ${d.w}x${d.h} "${d.text}"`);
  }
  
  if (deepEls.length > 0) {
    if (aiFrame) {
      // 在iframe内点击
      await aiFrame.evaluate(({x, y}) => {
        const el = document.elementFromPoint(x + 5, y + 5);
        if (el) el.click();
      }, {x: deepEls[0].x, y: deepEls[0].y});
    } else {
      await page.mouse.click(deepEls[0].x + 5, deepEls[0].y + 5);
    }
    console.log('✅ 深度思考');
    await sleep(2000);
  }
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v7_03_deep.png') });
  
  // ===== 7. 输入 =====
  console.log('\n=== 7. 输入提示词 ===');
  
  if (aiFrame) {
    await aiFrame.locator('[contenteditable="true"]').first().fill(USER_PROMPT);
  } else {
    const inp = bottomInputs[0];
    if (inp.type === 'contenteditable') {
      await page.locator('[contenteditable="true"]').first().fill(USER_PROMPT);
    } else {
      await page.locator('input[type="text"], textarea').first().fill(USER_PROMPT);
    }
  }
  console.log('✅ 已输入');
  await sleep(1000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v7_04_prompt.png') });
  
  // ===== 8. 发送 =====
  console.log('\n=== 8. 发送 ===');
  await page.keyboard.press('Enter');
  console.log('✅ 已发送');
  await sleep(5000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v7_05_sent.png') });
  
  // ===== 9. 等待回复 =====
  console.log('\n=== 9. 等待回复（120秒）===');
  
  let lastLen = 0;
  for (let i = 0; i < 120; i++) {
    await sleep(1000);
    
    const cur = await (aiFrame || page).evaluate(() => {
      let best = '';
      document.querySelectorAll('div, section').forEach(el => {
        const t = el.innerText?.trim() || '';
        if (t.length > best.length && t.length < 100000) best = t;
      });
      return best;
    });
    
    if (i % 10 === 0) console.log(`  [${i}s] ${cur.length} 字符`);
    
    if (cur.length > 500 && cur.length === lastLen && i > 15) {
      console.log(`✅ 稳定: ${cur.length} 字符`);
      break;
    }
    lastLen = cur.length;
  }
  
  await sleep(5000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v7_06_done.png') });
  
  // ===== 10. 提取 =====
  console.log('\n=== 10. 提取 ===');
  
  const reply = await (aiFrame || page).evaluate(() => {
    let best = '';
    document.querySelectorAll('div, section').forEach(el => {
      const t = el.innerText?.trim() || '';
      if (t.length > best.length && t.length < 100000) best = t;
    });
    return best;
  });
  
  console.log(`长度: ${reply.length}`);
  
  const outPath = path.join(OUTPUT_DIR, 'v7_ai_reply.md');
  fs.writeFileSync(outPath, `# AI 回复\n\n${reply}`);
  console.log(`✅ 保存: ${outPath}`);
  
  console.log('\n=== 回复内容 ===');
  console.log(reply);
  
  console.log('\n浏览器保持打开 60 秒...');
  await sleep(60000);
  await context.close();
})();
