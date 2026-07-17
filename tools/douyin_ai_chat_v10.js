/**
 * v10 - 极简直接: jingxuan链接 → 等待 → 深度思考 → 输入 → 发送 → 等待90s → 复制
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const VIDEO_ID = '7650409830854790415';
const JINGXUAN_URL = `https://www.douyin.com/jingxuan?modal_id=${VIDEO_ID}`;
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUT = 'F:/ai/tools/screenshots';
const PROMPT = '把视频完全文案发给我，接着根据文案和视频内容整合出文案+资料+背景+视频中出现的错误或偏见或者在其他条件情况会有不同结果的内容一并整理出来，然后再单独另外整合的该内容下的所有评价然后分析整体视频和评价的矛盾点在哪，还有需求点在哪，可挖掘的市场或者可着重表现的点在哪等。如果画面中有重要图片请提取图片中的文案下来，画面中出现的文案也要全部提取下来。';

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false, viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    args: ['--no-sandbox']
  });
  const page = await ctx.newPage();

  // 1. 打开链接，等待足够久
  console.log('1. 打开: ' + JINGXUAN_URL);
  await page.goto(JINGXUAN_URL, { waitUntil: 'load', timeout: 30000 });
  console.log('   等待页面完全渲染 (20s)...');
  await sleep(20000);
  await page.screenshot({ path: `${OUT}/v10_01_page.png` });

  // 2. 找输入框
  console.log('2. 找输入框...');
  const inputs = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('[contenteditable="true"], textarea, input[type="text"]:not([class*="upload"])'))
      .filter(e => e.getBoundingClientRect().width > 50)
      .map(e => ({
        tag: e.tagName, type: e.getAttribute('contenteditable') ? 'editable' : e.tagName,
        x: Math.round(e.getBoundingClientRect().x), y: Math.round(e.getBoundingClientRect().y),
        w: Math.round(e.getBoundingClientRect().width), h: Math.round(e.getBoundingClientRect().height),
        place: (e.getAttribute('placeholder') || '').substring(0, 30)
      }));
  });
  console.log(`   可见输入框: ${inputs.length}`);
  inputs.forEach(i => console.log(`     [${i.x},${i.y}] ${i.w}x${i.h} "${i.place}"`));

  if (inputs.length === 0) {
    console.log('❌ 无输入框！保存HTML调试');
    fs.writeFileSync(`${OUT}/v10_page.html`, await page.content());
    await ctx.close(); return;
  }

  // 选最大的/y最高的输入框
  const best = inputs.reduce((a, b) => a.y > b.y ? a : b);
  console.log(`   选择: [${best.x},${best.y}]`);

  // 3. 深度思考
  console.log('3. 深度思考...');
  const deep = await page.evaluate(() => {
    for (const el of document.querySelectorAll('*')) {
      if (el.textContent.trim() === '深度思考' && el.children.length === 0) {
        const r = el.getBoundingClientRect();
        return { x: r.x+5, y: r.y+5 };
      }
    }
    return null;
  });
  if (deep) { await page.mouse.click(deep.x, deep.y); console.log('   ✅ 已点击'); }
  else console.log('   ⚠️ 未找到');
  await sleep(2000);

  // 4. 输入
  console.log('4. 输入提示词...');
  if (best.type === 'editable') {
    await page.locator('[contenteditable="true"]').first().fill(PROMPT);
  } else {
    await page.locator('input[type="text"], textarea').first().fill(PROMPT);
  }
  console.log(`   ✅ ${PROMPT.length}字`);
  await sleep(1000);
  await page.screenshot({ path: `${OUT}/v10_02_prompt.png` });

  // 5. 发送
  console.log('5. 发送...');
  await page.keyboard.press('Enter');
  console.log('   ✅');
  await sleep(3000);

  // 6. 等90秒
  console.log('6. 等待AI回复 (90s)...');
  let last = '', ended = false;
  for (let i = 0; i < 90; i++) {
    await sleep(1000);
    const cur = await page.evaluate(() => {
      let b = '';
      document.querySelectorAll('div,section,article').forEach(e => {
        const t = (e.innerText||'').trim();
        if (t.length > b.length && t.length < 200000) b = t;
      });
      return b;
    });
    if (i % 15 === 0) console.log(`   [${i}s] ${cur.length}字`);
    if (cur.length > 500 && cur === last) {
      if (++ended >= 5) { console.log(`   ✅ 稳定: ${cur.length}字`); break; }
    } else { ended = 0; last = cur; }
  }
  await sleep(3000);
  await page.screenshot({ path: `${OUT}/v10_03_done.png` });

  // 7. 复制
  console.log('7. 复制...');
  try {
    const copyBtn = await page.evaluate(() => {
      for (const el of document.querySelectorAll('button,span,div,svg')) {
        if (el.textContent.trim() === '复制' && el.getBoundingClientRect().width > 0) {
          return { x: Math.round(el.getBoundingClientRect().x + 5), y: Math.round(el.getBoundingClientRect().y + 5) };
        }
      }
      // 或找class含copy的
      for (const el of document.querySelectorAll('[class*="copy"],[class*="Copy"]')) {
        if (el.getBoundingClientRect().width > 0) {
          return { x: Math.round(el.getBoundingClientRect().x + 5), y: Math.round(el.getBoundingClientRect().y + 5) };
        }
      }
      return null;
    });
    if (copyBtn) { await page.mouse.click(copyBtn.x, copyBtn.y); console.log('   ✅ 已点击复制'); }
    else console.log('   ⚠️ 无复制按钮');
  } catch(e) {}

  // 8. 提取并保存
  console.log('8. 提取文本...');
  const text = await page.evaluate(() => {
    let b = '';
    document.querySelectorAll('div,section').forEach(e => {
      const t = (e.innerText||'').trim();
      if (t.length > b.length && t.length < 200000) b = t;
    });
    return b;
  });

  const outFile = `${OUT}/v10_${VIDEO_ID}_reply.md`;
  fs.writeFileSync(outFile, `# AI回复\n\n${text}`);
  console.log(`   ✅ ${outFile} (${text.length}字)`);
  console.log(`\n=== 前800字 ===\n${text.substring(0, 800)}\n...`);

  // 9. 录入第二大脑
  console.log('9. 录入第二大脑...');
  try {
    const http = require('http');
    const body = JSON.stringify({ text, source: `douyin-${VIDEO_ID}`, source_type: 'douyin_ai', tags: ['抖音AI','视频分析'] });
    const req = http.request({ hostname:'localhost', port:8766, path:'/api/digest/text', method:'POST',
      headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(body)} }, r => { r.resume(); });
    req.on('error', () => {});
    req.write(body); req.end();
    await sleep(2000);
    console.log('   ✅');
  } catch(e) { console.log('   ⚠️', e.message); }

  console.log('\n完成！30s后关闭...');
  await sleep(30000);
  await ctx.close();
})();
