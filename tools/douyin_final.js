/**
 * 走 search_ai_mobile 页面，URL+提示词
 */
const { chromium } = require('playwright');
const fs = require('fs');

const VIDEO_ID = '7650409830854790415';
const JX_URL = `https://www.douyin.com/jingxuan?modal_id=${VIDEO_ID}`;
const PROFILE = 'C:/WorkBuddy/PlaywrightProfile';
const OUT = 'F:/ai/tools/screenshots';
const PROMPT = `${JX_URL}。把视频完全文案发给我，接着根据文案和视频内容整合出文案+资料+背景+视频中出现的错误或偏见或者在其他条件情况会有不同结果的内容一并整理出来，然后再单独另外整合的该内容下的所有评价然后分析整体视频和评价的矛盾点在哪，还有需求点在哪，可挖掘的市场或者可着重表现的点在哪等。如果画面中有重要图片请提取图片中的文案下来，画面中出现的文案也要全部提取下来。`;

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    headless: false, viewport: { width: 1920, height: 1080 }, args: ['--no-sandbox']
  });
  const page = await ctx.newPage();

  // 1. 先访问视频页建 cookie
  console.log('1. 视频页...');
  await page.goto(`https://www.douyin.com/video/${VIDEO_ID}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(5000);

  const deviceId = await page.evaluate(() => {
    const m = document.cookie.match(/device_id=([^;]+)/);
    return m ? m[1] : '7651518205098608143';
  });

  // 2. 进入 AI 页面
  console.log('2. AI页面...');
  const aiUrl = `https://so-landing.douyin.com/search_ai_mobile/pc?aid=6383&device_id=${deviceId}&ai_search_req_patch=${encodeURIComponent(JSON.stringify({ai_search_enter_from_group_id:VIDEO_ID,enter_from:'video_detail'}))}&enter_from=video_detail`;
  await page.goto(aiUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(15000);

  // 3. 点击对话框 → 激活深度思考
  console.log('3. 对话框...');
  let dialog = null;
  for (let i = 0; i < 10 && !dialog; i++) {
    dialog = await page.evaluate(() => {
      const el = document.querySelector('[contenteditable="true"]');
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: r.x + r.width/2, y: r.y + r.height/2 };
    });
    if (!dialog) await sleep(2000);
  }
  if (dialog) {
    await page.mouse.click(dialog.x, dialog.y);
    console.log(`   ✅`);
    await sleep(2000);
  } else {
    console.log('   ❌ 无对话框');
    await ctx.close(); return;
  }

  // 4. 深度思考
  console.log('4. 深度思考...');
  const deep = await page.evaluate(() => {
    for (const el of document.querySelectorAll('*')) {
      if (el.textContent.trim() === '深度思考' && el.children.length === 0) {
        const r = el.getBoundingClientRect();
        if (r.width > 0) return { x: r.x + r.width/2, y: r.y + r.height/2 };
      }
    }
    return null;
  });
  if (deep) { await page.mouse.click(deep.x, deep.y); console.log('   ✅'); }
  else { console.log('   ⚠️ 跳过'); }
  await sleep(1500);

  // 5. 输入
  console.log('5. 输入...');
  await page.locator('[contenteditable="true"]').first().click();
  await sleep(300);
  await page.locator('[contenteditable="true"]').first().fill(PROMPT);
  console.log(`   ✅ ${PROMPT.length}字`);
  await sleep(1000);

  // 6. 发送
  console.log('6. 发送...');
  await page.keyboard.press('Enter');
  console.log('   ✅');
  await sleep(5000);

  // 7. 等回复（3分钟）
  console.log('7. 等待回复...');
  let last = '', final = 0, text = '';
  for (let i = 0; i < 180; i++) {
    await sleep(1000);
    const cur = await page.evaluate(() => {
      let b = '';
      document.querySelectorAll('div,section').forEach(e => {
        const t = (e.innerText||'').trim();
        if (t.length > b.length && t.length < 200000) b = t;
      });
      return b;
    });
    if (i % 15 === 0) console.log(`   [${i}s] ${cur.length}字`);
    if (cur.length > 500 && cur === last) {
      if (++final >= 6) { text = cur; break; }
    } else { final = 0; last = cur; }
  }
  text = text || last;
  console.log(`   ✅ ${text.length}字`);

  // 8. 复制
  console.log('8. 复制...');
  try {
    const btn = await page.evaluate(() => {
      for (const el of document.querySelectorAll('*')) {
        if (el.textContent.trim() === '复制' && el.getBoundingClientRect().width > 0)
          return { x: Math.round(el.getBoundingClientRect().x + 8), y: Math.round(el.getBoundingClientRect().y + 8) };
      }
      return null;
    });
    if (btn) { await page.mouse.click(btn.x, btn.y); console.log('   ✅'); }
    else console.log('   ⚠️');
  } catch(e) {}

  // 9. 保存
  const out = `${OUT}/final_${VIDEO_ID}.md`;
  fs.writeFileSync(out, `# AI回复\n\n${text}`);
  console.log(`9. 保存: ${out} (${text.length}字)`);

  // 10. 消化
  console.log('10. 录入第二大脑...');
  try {
    const http = require('http');
    const bd = JSON.stringify({ text, source: `douyin-${VIDEO_ID}`, source_type: 'douyin_ai', tags: ['抖音AI','视频分析'] });
    const rq = http.request({ hostname:'localhost', port:8766, path:'/api/digest/text', method:'POST',
      headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(bd)} }, r => {
        let d=''; r.on('data',c=>d+=c); r.on('end',()=>console.log('   入库:', d.substring(0, 100)));
      });
    rq.on('error',()=>{});
    rq.write(bd); rq.end();
    await sleep(3000);
  } catch(e) {}

  console.log('\n=== 前1000字 ===\n' + text.substring(0, 1000) + '\n...');
  console.log('\n60s后关闭...');
  await sleep(60000);
  await ctx.close();
})();
