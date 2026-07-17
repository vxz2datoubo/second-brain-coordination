/**
 * Douyin AI Chat v3 - 从视频页进入, 切换iframe操作
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
  
  // ===== 1. 先进入视频页 =====
  console.log('=== 1. 进入视频页 ===');
  await page.goto(`https://www.douyin.com/video/${VIDEO_ID}`, { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(8000);
  
  // ===== 2. 找并点击 "问AI" =====
  console.log('\n=== 2. 点击问AI ===');
  
  // 先确保tablist出现了
  for (let i = 0; i < 20; i++) {
    const count = await page.locator('#semiTabai_card').count();
    if (count > 0) break;
    await sleep(1000);
  }
  
  await page.locator('#semiTabai_card').click({ timeout: 5000 });
  console.log('✅ 点击问AI');
  await sleep(5000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v3_01_tab.png') });
  
  // ===== 3. 检查是否有iframe =====
  console.log('\n=== 3. 检查iframe ===');
  
  const frames = page.frames();
  console.log(`页面frame数: ${frames.length}`);
  
  // 列出所有iframe信息
  const iframeInfo = await page.evaluate(() => {
    const iframes = document.querySelectorAll('iframe');
    return Array.from(iframes).map((f, i) => ({
      index: i,
      src: f.src?.substring(0, 200) || '',
      name: f.name || '',
      id: f.id || '',
      cls: f.className?.substring(0, 80) || '',
      visible: f.getBoundingClientRect().width > 0
    }));
  });
  
  console.log(`iframe: ${iframeInfo.length}`);
  for (const f of iframeInfo) {
    console.log(`  #${f.index} id="${f.id}" name="${f.name}" visible=${f.visible}`);
    console.log(`       src="${f.src}"`);
  }
  
  // ===== 4. 如果有AI相关iframe，切换进去 =====
  let targetFrame = null;
  
  for (const frame of frames) {
    const url = frame.url();
    if (url.includes('search_ai') || url.includes('so-landing') || url.includes('aisearch')) {
      targetFrame = frame;
      console.log(`\n✅ 找到AI iframe: ${url.substring(0, 100)}`);
      break;
    }
  }
  
  if (!targetFrame) {
    // 没有AI iframe，说明AI面板不是iframe模式，直接在页面中
    console.log('\n⚠️ 没有AI iframe，直接在页面中操作');
    targetFrame = page;
  }
  
  // ===== 5. 在AI面板中操作 =====
  const fp = targetFrame === page ? page : targetFrame;
  
  // 检查内容
  const bodyText = await fp.evaluate(() => {
    return (document.body?.innerText || '').substring(0, 500);
  });
  console.log(`\nAI面板内容预览:\n${bodyText.substring(0, 300)}`);
  
  // 点击深度思考
  console.log('\n=== 5. 点击深度思考 ===');
  try {
    // 在正确的frame中找
    const deepBtn = fp.locator('span:has-text("深度思考"), div:has-text("深度思考"), label:has-text("深度")').first();
    const cnt = await deepBtn.count();
    if (cnt > 0) {
      await deepBtn.click({ timeout: 3000 });
      console.log('✅ 深度思考已点击');
    } else {
      console.log('⚠️ 未找到深度思考按钮');
    }
  } catch(e) {
    console.log('⚠️:', e.message?.substring(0, 60));
  }
  await sleep(2000);
  
  // 找输入框
  console.log('\n=== 6. 找输入框 ===');
  const inputs = await fp.evaluate(() => {
    const results = [];
    document.querySelectorAll('[contenteditable="true"], textarea, input[type="text"]').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width > 50 && r.height > 20) {
        results.push({
          tag: el.tagName,
          type: el.getAttribute('contenteditable') ? 'contenteditable' : el.tagName,
          cls: el.className?.substring(0, 60),
          x: Math.round(r.x), y: Math.round(r.y),
          w: Math.round(r.width), h: Math.round(r.height)
        });
      }
    });
    return results;
  });
  
  console.log(`可见输入: ${inputs.length}`);
  for (const i of inputs) {
    console.log(`  ${i.type} [${i.x},${i.y}] ${i.w}x${i.h}`);
  }
  
  if (inputs.length === 0) {
    console.log('❌ 无输入框');
    await context.close();
    return;
  }
  
  const inp = inputs[0];
  
  // 输入
  console.log('\n=== 7. 输入提示词 ===');
  if (inp.type === 'contenteditable') {
    const editable = fp.locator('[contenteditable="true"]').first();
    await editable.click();
    await editable.fill(PROMPT);
    console.log('✅ 已输入');
  } else {
    await fp.locator('input[type="text"], textarea').first().fill(PROMPT);
    console.log('✅ 已输入');
  }
  await sleep(1000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v3_02_prompt.png') });
  
  // 发送
  console.log('\n=== 8. 发送 ===');
  await fp.keyboard.press('Enter');
  console.log('✅ Enter发送');
  await sleep(3000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v3_03_sent.png') });
  
  // 等待回复
  console.log('\n=== 9. 等待回复 ===');
  let lastLen = 0, stable = 0;
  
  for (let i = 0; i < 90; i++) {
    await sleep(1000);
    
    const current = await fp.evaluate(() => {
      let best = { len: 0 };
      document.querySelectorAll('[class*="message"], [class*="answer"], [class*="content"]').forEach(el => {
        const t = el.textContent?.trim() || '';
        if (t.length > best.len && t.length < 100000) best = { len: t.length };
      });
      return best;
    });
    
    if (current.len > 200 && current.len === lastLen) {
      stable++;
      if (stable >= 5) {
        console.log(`✅ 稳定: ${current.len} 字符`);
        break;
      }
    } else if (current.len > lastLen) {
      lastLen = current.len;
      stable = 0;
      if (i % 5 === 0) console.log(`  [${i}s] ${current.len} 字符`);
    }
  }
  
  await sleep(3000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v3_04_done.png') });
  
  // 提取
  console.log('\n=== 10. 提取 ===');
  const reply = await fp.evaluate(() => {
    let best = '';
    document.querySelectorAll('div, section').forEach(el => {
      const t = el.innerText?.trim() || '';
      if (t.length > best.length && t.length < 100000) best = t;
    });
    return best;
  });
  
  console.log(`长度: ${reply.length}`);
  
  const outPath = path.join(OUTPUT_DIR, 'v3_ai_reply.md');
  fs.writeFileSync(outPath, `# AI 回复\n\n${reply}`);
  console.log(`✅ 保存: ${outPath}`);
  
  console.log('\n...预览前600字...');
  console.log(reply.substring(0, 600));
  
  console.log('\n浏览器保持打开 60 秒...');
  await sleep(60000);
  await context.close();
})();
