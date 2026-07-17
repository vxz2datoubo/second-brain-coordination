/**
 * Douyin AI Chat v8 - 简洁直接：打开链接→深度思考→输入→等待→复制
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const VIDEO_ID = '7650409830854790415';
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUTPUT_DIR = 'F:/ai/tools/screenshots';

const sleep = ms => new Promise(r => setTimeout(r, ms));

const PROMPT = `把视频完全文案发给我，接着根据文案和视频内容整合出文案+资料+背景+视频中出现的错误或偏见或者在其他条件情况会有不同结果的内容一并整理出来，然后再单独另外整合的该内容下的所有评价然后分析整体视频和评价的矛盾点在哪，还有需求点在哪，可挖掘的市场或者可着重表现的点在哪等。如果画面中有重要图片请提取图片中的文案下来，画面中出现的文案也要全部提取下来。`;

(async () => {
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    viewport: { width: 1920, height: 1080 },
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });

  const page = await context.newPage();

  // ===== 1. 先访问视频页获取 cookies/session =====
  console.log('=== 1. 访问视频页 ===');
  await page.goto(`https://www.douyin.com/video/${VIDEO_ID}`, {
    waitUntil: 'domcontentloaded', timeout: 30000
  });
  await sleep(5000);

  // ===== 2. 获取 device_id 并导航到 AI 搜索页面 =====
  console.log('\n=== 2. 导航到 AI 页面 ===');
  const deviceId = await page.evaluate(() => {
    const m = document.cookie.match(/device_id=([^;]+)/);
    return m ? m[1] : '7651518205098608143';
  });
  
  const aiUrl = `https://so-landing.douyin.com/search_ai_mobile/pc?aid=6383&device_id=${deviceId}&ai_search_req_patch=${encodeURIComponent(JSON.stringify({ai_search_enter_from_group_id: VIDEO_ID, enter_from: 'video_detail'}))}&enter_from=video_detail`;
  
  await page.goto(aiUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(12000); // AI页面需要较长时间渲染
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v8_01_page.png') });

  // ===== 3. 点击「深度思考」=====
  console.log('\n=== 3. 点击深度思考 ===');
  const deepResult = await page.evaluate(() => {
    const all = document.querySelectorAll('*');
    for (const el of all) {
      if (el.textContent.trim() === '深度思考' && el.children.length === 0) {
        const r = el.getBoundingClientRect();
        return { found: true, x: r.x + r.width/2, y: r.y + r.height/2, tag: el.tagName };
      }
    }
    return { found: false };
  });

  if (deepResult.found) {
    await page.mouse.click(deepResult.x, deepResult.y);
    console.log(`✅ 已点击 (${deepResult.tag} at ${deepResult.x},${deepResult.y})`);
  } else {
    console.log('⚠️ 未找到，尝试其他方式...');
    try { await page.locator('text=深度思考').first().click({ timeout: 3000 }); console.log('✅ text匹配成功'); } catch(e) { console.log('跳过'); }
  }
  await sleep(3000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v8_02_deep.png') });

  // ===== 4. 输入提示词 =====
  console.log('\n=== 4. 输入提示词 ===');
  const inp = page.locator('[contenteditable="true"]').first();
  await inp.click();
  await sleep(500);
  await inp.fill(PROMPT);
  console.log(`✅ 已输入 (${PROMPT.length}字)`);
  await sleep(1000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v8_03_prompt.png') });

  // ===== 5. 发送 =====
  console.log('\n=== 5. 发送 ===');
  await page.keyboard.press('Enter');
  console.log('✅ 已发送');
  await sleep(3000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v8_04_sent.png') });

  // ===== 6. 等待 AI 回复 =====
  console.log('\n=== 6. 等待 AI 回复 (180秒) ===');
  let lastLen = 0, stable = 0, finalText = '';
  for (let i = 0; i < 180; i++) {
    await sleep(1000);
    const cur = await page.evaluate(() => {
      let best = '';
      document.querySelectorAll('div, section, article').forEach(el => {
        const t = el.innerText?.trim() || '';
        if (t.length > best.length && t.length < 200000) best = t;
      });
      return best;
    });

    if (i % 10 === 0) console.log(`  [${i}s] ${cur.length} 字`);

    if (cur.length > 300 && cur.length === lastLen) {
      stable++;
      if (stable >= 5) { finalText = cur; break; }
    } else if (cur.length > lastLen) {
      lastLen = cur.length;
      stable = 0;
    }
  }
  await sleep(3000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v8_05_done.png') });

  // ===== 7. 复制答案 =====
  console.log('\n=== 7. 复制答案 ===');

  // 找复制按钮
  const copyBtns = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('button, span, div, svg'))
      .filter(el => {
        const t = el.textContent?.trim() || '';
        const cls = (el.className?.toString() || '').toLowerCase();
        return (t === '复制' || cls.includes('copy')) && el.getBoundingClientRect().width > 0;
      })
      .map(el => ({
        text: el.textContent?.trim()?.substring(0, 10),
        x: Math.round(el.getBoundingClientRect().x),
        y: Math.round(el.getBoundingClientRect().y)
      }));
  });
  console.log(`复制按钮: ${copyBtns.length}`);
  if (copyBtns.length > 0) {
    await page.mouse.click(copyBtns[0].x + 5, copyBtns[0].y + 5);
    console.log('✅ 已点击复制');
  }

  // 提取文本
  const reply = finalText || await page.evaluate(() => {
    let best = '';
    document.querySelectorAll('div, section').forEach(el => {
      const t = el.innerText?.trim() || '';
      if (t.length > best.length && t.length < 200000) best = t;
    });
    return best;
  });

  const outPath = path.join(OUTPUT_DIR, `v8_${VIDEO_ID}_reply.md`);
  fs.writeFileSync(outPath, `# AI 回复\n\n${reply}`);
  console.log(`\n✅ 已保存: ${outPath}`);
  console.log(`总字数: ${reply.length}`);

  // ===== 8. 消化 & 录入第二大脑 =====
  console.log('\n=== 8. 消化录入第二大脑 ===');
  
  // 检查第二大脑服务器是否运行
  try {
    const http = require('http');
    const digestData = JSON.stringify({
      text: reply,
      source: `douyin-video-${VIDEO_ID}`,
      source_type: 'douyin_ai_analysis',
      tags: ['抖音AI分析', '视频文案', '市场洞察']
    });

    const req = http.request({
      hostname: 'localhost', port: 8766,
      path: '/api/digest/text', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(digestData) }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => console.log('✅ 已录入第二大脑:', data.substring(0, 200)));
    });
    req.on('error', (e) => console.log('⚠️ 第二大脑未运行:', e.message));
    req.write(digestData);
    req.end();
  } catch(e) {
    console.log('⚠️ 录入异常:', e.message);
  }

  // 同时保存到输出目录
  const brainPath = path.join(OUTPUT_DIR, `brain_input_${VIDEO_ID}.txt`);
  fs.writeFileSync(brainPath, reply);
  console.log(`✅ 备用保存: ${brainPath}`);

  // ===== 8. 预览 =====
  console.log('\n=== 回复预览（前800字）===');
  console.log(reply.substring(0, 800));
  console.log('...');

  console.log('\n浏览器保持打开 30 秒...');
  await sleep(30000);
  await context.close();
})();
