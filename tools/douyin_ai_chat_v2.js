/**
 * Douyin AI Chat v2 - 正确方式: 先检查AI面板是否加载iframe, 然后操作
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const VIDEO_ID = '7650106006073502949';
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUTPUT_DIR = 'F:/ai/tools/screenshots';

const PROMPT = `把视频完全文案发给我，接着根据文案和视频内容整合出文案+资料+背景+视频中出现的错误或偏见或者在其他条件情况会有不同结果的内容一并整理出来，然后再单独另外整合的该内容下的所有评价然后分析整体视频和评价的矛盾点在哪，还有需求点在哪，可挖掘的市场或者可着重表现的点在哪等。如果画面中有重要图片请提取图片中的文案下来，画面中出现的文案也要全部提取下来。`;

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    viewport: { width: 1920, height: 1080 },
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });

  const page = await context.newPage();
  
  // ===== 方案B: 直接导航到 AI 搜索页面 =====
  console.log('=== 方案B: 直接使用 AI 搜索页面 ===');
  
  const deviceId = '7651518205098608143';
  const aiUrl = `https://so-landing.douyin.com/search_ai_mobile/pc?aid=6383&device_id=${deviceId}&ai_search_req_patch=${encodeURIComponent(JSON.stringify({ai_search_enter_from_group_id: VIDEO_ID}))}&enter_from=video_detail`;
  
  console.log('导航到 AI 页面...');
  await page.goto(aiUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(8000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v2_01_ai_page.png') });
  
  // ===== 分析页面结构 =====
  console.log('\n=== 分析AI页面结构 ===');
  
  const pageAnalysis = await page.evaluate(() => {
    const results = {};
    
    // 找 iframe
    results.iframes = document.querySelectorAll('iframe').length;
    
    // 找输入框
    const inputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
    results.inputs = Array.from(inputs).map(el => ({
      tag: el.tagName,
      placeholder: el.getAttribute('placeholder') || '',
      type: el.getAttribute('type') || '',
      cls: el.className?.substring(0, 80) || '',
      visible: el.getBoundingClientRect().width > 0
    }));
    
    // 找按钮
    const buttons = document.querySelectorAll('button, [role="button"]');
    results.buttons = Array.from(buttons)
      .filter(b => b.getBoundingClientRect().width > 0)
      .map(b => ({
        text: b.textContent?.trim()?.substring(0, 50) || '',
        cls: b.className?.substring(0, 80) || ''
      }))
      .slice(0, 20);
    
    // 页面标题和URL
    results.title = document.title;
    results.bodyText = document.body?.innerText?.substring(0, 500) || '';
    
    return results;
  });
  
  console.log(`页面标题: ${pageAnalysis.title}`);
  console.log(`iframe数: ${pageAnalysis.iframes}`);
  console.log(`输入框: ${pageAnalysis.inputs.length}`);
  for (const inp of pageAnalysis.inputs) {
    console.log(`  <${inp.tag}> placeholder="${inp.placeholder}" class="${inp.cls}" visible=${inp.visible}`);
  }
  console.log(`可见按钮: ${pageAnalysis.buttons.length}`);
  for (const btn of pageAnalysis.buttons.slice(0, 15)) {
    console.log(`  "${btn.text}" class="${btn.cls}"`);
  }
  
  // ===== 如果有iframe，切换到iframe =====
  let targetPage = page;
  if (pageAnalysis.iframes > 0) {
    console.log('\n=== 检测到iframe，尝试切换 ===');
    const frame = page.frameLocator('iframe').first();
    // frame-locator模式
    targetPage = page; // frameLocator不能直接用于page操作
  }
  
  // ===== 点击「深度思考」=====
  console.log('\n=== 点击「深度思考」===');
  try {
    // 方法: 找所有带"深度"文字的可见元素
    const deepBtn = page.locator('span:has-text("深度思考"), div:has-text("深度思考"), button:has-text("深度"), label:has-text("深度")').first();
    const count = await deepBtn.count();
    console.log(`  深度思考匹配数: ${count}`);
    
    if (count > 0) {
      await deepBtn.click({ timeout: 5000 });
      console.log('✅ 已点击深度思考');
    } else {
      console.log('⚠️ 未找到深度思考按钮');
    }
  } catch(e) {
    console.log('⚠️ 深度思考:', e.message?.substring(0, 80));
  }
  
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v2_02_deep.png') });
  
  // ===== 找到正确的输入框 =====
  console.log('\n=== 查找输入框 ===');
  
  // 尝试找 chat 专用的输入框
  const inputResult = await page.evaluate(() => {
    // 找所有可能的输入元素
    const candidates = [];
    
    // 检查 textarea
    document.querySelectorAll('textarea').forEach(el => {
      const r = el.getBoundingClientRect();
      candidates.push({
        type: 'textarea',
        placeholder: el.getAttribute('placeholder') || '',
        cls: el.className?.substring(0, 80),
        x: Math.round(r.x), y: Math.round(r.y),
        w: Math.round(r.width), h: Math.round(r.height),
        visible: r.width > 0 && r.height > 0
      });
    });
    
    // 检查 contenteditable
    document.querySelectorAll('[contenteditable="true"]').forEach(el => {
      const r = el.getBoundingClientRect();
      candidates.push({
        type: 'contenteditable',
        cls: el.className?.substring(0, 80),
        x: Math.round(r.x), y: Math.round(r.y),
        w: Math.round(r.width), h: Math.round(r.height),
        visible: r.width > 0 && r.height > 0
      });
    });
    
    // 检查 input
    document.querySelectorAll('input[type="text"], input:not([type])').forEach(el => {
      const r = el.getBoundingClientRect();
      candidates.push({
        type: 'input',
        placeholder: el.getAttribute('placeholder') || '',
        cls: el.className?.substring(0, 80),
        x: Math.round(r.x), y: Math.round(r.y),
        w: Math.round(r.width), h: Math.round(r.height),
        visible: r.width > 0 && r.height > 0
      });
    });
    
    return candidates.filter(c => c.visible);
  });
  
  console.log(`可见输入框: ${inputResult.length}`);
  for (const inp of inputResult) {
    console.log(`  ${inp.type} [${inp.x},${inp.y}] ${inp.w}x${inp.h} placeholder="${inp.placeholder}"`);
  }
  
  // 选择最可能是AI聊天输入框的 (较大且在页面下方)
  let targetInput = null;
  for (const inp of inputResult) {
    if (inp.y > 300 && inp.w > 200) {
      targetInput = inp;
      break;
    }
  }
  if (!targetInput && inputResult.length > 0) {
    targetInput = inputResult[inputResult.length - 1]; // 最后一个
  }
  
  if (!targetInput) {
    console.log('❌ 未找到合适的输入框');
    await context.close();
    return;
  }
  
  console.log(`\n选择输入框: ${targetInput.type} [${targetInput.x},${targetInput.y}]`);
  
  // ===== 输入文本 =====
  console.log('\n=== 输入提示词 ===');
  
  if (targetInput.type === 'textarea') {
    const ta = page.locator('textarea').first();
    await ta.fill(PROMPT);
    console.log('✅ 已输入到 textarea');
  } else if (targetInput.type === 'contenteditable') {
    const editable = page.locator('[contenteditable="true"]').first();
    await editable.fill(PROMPT);
    console.log('✅ 已输入到 contenteditable');
  } else {
    // 直接用键盘输入
    await page.mouse.click(targetInput.x + targetInput.w/2, targetInput.y + targetInput.h/2);
    await page.keyboard.type(PROMPT, { delay: 10 });
    console.log('✅ 已键盘输入');
  }
  
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v2_03_prompt.png') });
  
  // ===== 发送 =====
  console.log('\n=== 发送 ===');
  
  // 先找发送按钮
  const sendBtns = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('button, [role="button"], span, div, svg'))
      .filter(el => {
        const text = el.textContent?.trim() || '';
        const cls = (el.className?.toString() || '').toLowerCase();
        return text === '发送' || text === '→' || cls.includes('send') || cls.includes('submit');
      })
      .filter(el => el.getBoundingClientRect().width > 0)
      .map(el => ({
        text: el.textContent?.trim()?.substring(0, 20),
        cls: el.className?.toString()?.substring(0, 80),
        x: Math.round(el.getBoundingClientRect().x),
        y: Math.round(el.getBoundingClientRect().y)
      }));
  });
  
  console.log(`发送按钮候选: ${sendBtns.length}`);
  for (const b of sendBtns) {
    console.log(`  [${b.x},${b.y}] "${b.text}" class="${b.cls}"`);
  }
  
  if (sendBtns.length > 0) {
    const btn = sendBtns[0];
    await page.mouse.click(btn.x + 10, btn.y + 10);
    console.log('✅ 已点击发送');
  } else {
    // 尝试Enter
    await page.keyboard.press('Enter');
    console.log('✅ 按Enter发送');
  }
  
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v2_04_sent.png') });
  
  // ===== 等待回复 =====
  console.log('\n=== 等待回复（最多90秒）===');
  
  let lastLen = 0;
  let stable = 0;
  
  for (let i = 0; i < 90; i++) {
    await sleep(1000);
    
    const current = await page.evaluate(() => {
      // 找AI回复内容 - 通常是包含markdown或大段文字的元素
      const possible = document.querySelectorAll('[class*="message"], [class*="answer"], [class*="content"], [class*="markdown"], [class*="chat"]');
      let best = { len: 0, text: '' };
      for (const el of possible) {
        const t = el.textContent?.trim() || '';
        if (t.length > best.len && t.length < 50000) {
          best = { len: t.length, text: t.substring(0, 500) };
        }
      }
      return best;
    });
    
    if (current.len > 100 && current.len === lastLen) {
      stable++;
      if (stable >= 5) {
        console.log(`✅ 回复稳定，长度: ${current.len} 字符`);
        break;
      }
    } else if (current.len > lastLen) {
      lastLen = current.len;
      stable = 0;
      if (i % 5 === 0) console.log(`  [${i}s] 长度: ${current.len}`);
    }
  }
  
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v2_05_done.png'), fullPage: false });
  
  // ===== 提取完整回复 =====
  console.log('\n=== 提取回复 ===');
  
  const finalReply = await page.evaluate(() => {
    // 找最大的文本块（AI回复通常是最长的）
    let best = { text: '', len: 0 };
    
    document.querySelectorAll('div, section, article, main').forEach(el => {
      const t = el.innerText?.trim() || '';
      // 排除导航、侧栏等
      const cls = (el.className?.toString() || '').toLowerCase();
      if (!cls.includes('nav') && !cls.includes('sidebar') && !cls.includes('header') && !cls.includes('footer')) {
        if (t.length > best.len && t.length < 100000) {
          best = { text: t, len: t.length };
        }
      }
    });
    
    return best;
  });
  
  console.log(`最终回复: ${finalReply.len} 字符`);
  
  const outPath = path.join(OUTPUT_DIR, 'v2_ai_reply.md');
  fs.writeFileSync(outPath, 
    `# AI 回复\n\n` +
    `## 提示词\n\n${PROMPT}\n\n` +
    `## 回复内容 (${finalReply.len} 字符)\n\n${finalReply.text}`
  );
  
  console.log(`✅ 已保存: ${outPath}`);
  
  // 预览
  if (finalReply.text) {
    console.log('\n=== 内容预览（前800字）===');
    console.log(finalReply.text.substring(0, 800));
    console.log('\n...');
  }
  
  console.log('\n浏览器保持打开 60 秒...');
  await sleep(60000);
  await context.close();
})();
