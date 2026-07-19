/**
 * Douyin AI Chat v4 - jingxuan + 等待iframe加载 + iframe内操作
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
  
  // ===== 1. 导航到 jingxuan =====
  console.log('=== 1. 导航到 jingxuan ===');
  await page.goto(`https://www.douyin.com/jingxuan?modal_id=${VIDEO_ID}`, { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  
  // 等待视频加载
  try { await page.waitForSelector('video', { timeout: 15000 }); } catch(e) {}
  await page.waitForTimeout(5000);
  
  // 点击视频激活
  try { await page.locator('video').first().click(); } catch(e) {}
  await page.waitForTimeout(3000);
  
  // ===== 2. 等待并点击问AI =====
  console.log('\n=== 2. 点击问AI ===');
  
  for (let i = 0; i < 30; i++) {
    const cnt = await page.locator('#semiTabai_card').count();
    if (cnt > 0) break;
    await sleep(1000);
  }
  
  try {
    await page.locator('#semiTabai_card').click({ timeout: 5000 });
    console.log('✅ 已点击');
  } catch(e) {
    console.log('❌ 点击失败:', e.message?.substring(0, 60));
    await context.close();
    return;
  }
  
  await page.waitForTimeout(5000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v4_01_clicked.png') });
  
  // ===== 3. 检查iframe =====
  console.log('\n=== 3. 检查AI iframe ===');
  
  let aiFrame = null;
  
  // 轮询检查iframe出现
  for (let i = 0; i < 30; i++) {
    const frames = page.frames();
    for (const f of frames) {
      const url = f.url();
      if (url.includes('search_ai') || url.includes('so-landing') || url.includes('aisearch')) {
        aiFrame = f;
        break;
      }
    }
    if (aiFrame) break;
    
    // 同时检查DOM中的iframe
    const iframeCount = await page.locator('iframe').count();
    if (i % 5 === 0) console.log(`  [${i+1}/30] iframe数: ${iframeCount}, frame数: ${page.frames().length}`);
    
    await sleep(1000);
  }
  
  if (aiFrame) {
    console.log(`✅ 找到AI iframe: ${aiFrame.url().substring(0, 120)}`);
  } else {
    console.log('⚠️ 未找到AI iframe，检查面板内容');
    
    // 检查面板当前内容
    const panelState = await page.evaluate(() => {
      const panel = document.querySelector('#semiTabPanelai_card');
      return {
        exists: !!panel,
        htmlLen: panel?.innerHTML?.length || 0,
        text: panel?.textContent?.trim()?.substring(0, 300) || '',
        iframes: document.querySelectorAll('#semiTabPanelai_card iframe').length
      };
    });
    console.log('面板状态:', JSON.stringify(panelState, null, 2));
    
    if (panelState.iframes > 0) {
      // Iframe在面板内，重新获取frame
      for (const f of page.frames()) {
        if (f.url().includes('search_ai') || f.url().includes('so-landing')) {
          aiFrame = f;
          break;
        }
      }
    }
    
    if (!aiFrame) {
      console.log('❌ 没有AI iframe。保存截图和HTML用于调试');
      await page.screenshot({ path: path.join(OUTPUT_DIR, 'v4_debug.png') });
      const html = await page.content();
      fs.writeFileSync(path.join(OUTPUT_DIR, 'v4_page.html'), html);
      console.log('HTML已保存');
      
      // 尝试作为替代方案: 直接导航到AI页面
      console.log('\n=== 替代方案: 直接AI页面 ===');
      const deviceId = '7651518205098608143';
      const aiUrl = `https://so-landing.douyin.com/search_ai_mobile/pc?aid=6383&device_id=${deviceId}&ai_search_req_patch=${encodeURIComponent(JSON.stringify({ai_search_enter_from_group_id: VIDEO_ID}))}&enter_from=video_detail`;
      await page.goto(aiUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await sleep(8000);
      
      // 在这个页面中操作
      await page.screenshot({ path: path.join(OUTPUT_DIR, 'v4_alt_page.png') });
      
      // 输入和发送
      console.log('输入提示词...');
      const editable = page.locator('[contenteditable="true"]').first();
      await editable.click();
      await editable.fill(PROMPT);
      await sleep(1000);
      
      console.log('发送...');
      await page.keyboard.press('Enter');
      
      console.log('等待回复...');
      await sleep(90000); // 等90秒
      
      await page.screenshot({ path: path.join(OUTPUT_DIR, 'v4_alt_done.png') });
      
      // 提取
      const reply = await page.evaluate(() => {
        let best = '';
        document.querySelectorAll('div, section').forEach(el => {
          const t = el.innerText?.trim() || '';
          if (t.length > best.length && t.length < 100000) best = t;
        });
        return best;
      });
      
      const outPath = path.join(OUTPUT_DIR, 'v4_alt_reply.md');
      fs.writeFileSync(outPath, `# AI 回复 (备选方案)\n\n${reply}`);
      console.log(`✅ 保存: ${outPath} (${reply.length} 字符)`);
      
      await context.close();
      return;
    }
  }
  
  // ===== 4. iframe内操作 =====
  console.log('\n=== 4. 在AI iframe内操作 ===');
  
  // iframe内等待加载
  await aiFrame.waitForSelector('[contenteditable="true"], textarea, input', { timeout: 15000 }).catch(() => {});
  await sleep(3000);
  
  // 内容预览
  const preview = await aiFrame.evaluate(() => document.body?.innerText?.substring(0, 300) || '');
  console.log(`iframe内容: ${preview.substring(0, 200)}`);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v4_02_iframe.png') });
  
  // 深度思考
  console.log('\n点击深度思考...');
  const deepBtn = aiFrame.locator('span:has-text("深度"), div:has-text("深度")').first();
  if (await deepBtn.count() > 0) {
    await deepBtn.click({ timeout: 3000 });
    console.log('✅ 深度思考');
  }
  await sleep(2000);
  
  // 输入
  console.log('\n输入提示词...');
  const input = aiFrame.locator('[contenteditable="true"], textarea').first();
  await input.click();
  await input.fill(PROMPT);
  console.log('✅ 已输入');
  await sleep(1000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v4_03_prompt.png') });
  
  // 发送
  console.log('\n发送...');
  await aiFrame.locator('[contenteditable="true"], textarea').first().press('Enter');
  console.log('✅ 已发送');
  await sleep(5000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v4_04_sent.png') });
  
  // 等待回复
  console.log('\n等待回复（90秒）...');
  for (let i = 0; i < 90; i++) {
    await sleep(1000);
    const len = await aiFrame.evaluate(() => {
      let best = 0;
      document.querySelectorAll('[class*="message"], [class*="answer"], div').forEach(el => {
        const t = el.textContent?.length || 0;
        if (t > best && t < 100000) best = t;
      });
      return best;
    });
    if (i % 10 === 0) console.log(`  [${i}s] 最大内容: ${len} 字符`);
  }
  
  await sleep(5000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v4_05_done.png') });
  
  // 提取
  const reply = await aiFrame.evaluate(() => {
    let best = '';
    document.querySelectorAll('div, section').forEach(el => {
      const t = el.innerText?.trim() || '';
      if (t.length > best.length && t.length < 100000) best = t;
    });
    return best;
  });
  
  console.log(`\n回复: ${reply.length} 字符`);
  const outPath = path.join(OUTPUT_DIR, 'v4_ai_reply.md');
  fs.writeFileSync(outPath, `# AI 回复\n\n${reply}`);
  console.log(`✅ 保存: ${outPath}`);
  
  console.log('\n...预览...');
  console.log(reply.substring(0, 500));
  
  console.log('\n浏览器保持打开 60 秒...');
  await sleep(60000);
  await context.close();
})();
