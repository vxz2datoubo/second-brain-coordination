/**
 * Douyin 问AI v4 - 等待视频弹窗完全渲染后再找 tablist
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const VIDEO_ID = '7650106006073502949';
const URL = `https://www.douyin.com/jingxuan?modal_id=${VIDEO_ID}`;
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUTPUT_DIR = 'F:/ai/tools/screenshots';

if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR, { recursive: true });

(async () => {
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    viewport: { width: 1920, height: 1080 },
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });

  const page = await context.newPage();
  
  console.log('=== 导航 ===');
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  
  // 等待视频出现
  console.log('等待视频元素...');
  try {
    await page.waitForSelector('video, [class*="xgplayer"], .xg-video-container', { timeout: 15000 });
    console.log('视频元素已加载');
  } catch(e) {
    console.log('未找到视频: ' + e.message?.substring(0, 80));
  }
  await page.waitForTimeout(3000);
  
  // 点击视频确保激活
  console.log('点击视频区域...');
  try {
    const video = page.locator('video, [class*="xg-video-container"]').first();
    await video.click({ timeout: 5000 });
    console.log('已点击视频');
  } catch(e) {
    console.log('点击视频失败: ' + e.message?.substring(0, 80));
  }
  await page.waitForTimeout(3000);
  
  // 等待 tablist 出现 - 使用轮询
  console.log('等待 tablist 出现...');
  let tablistReady = false;
  for (let i = 0; i < 20; i++) {
    const count = await page.locator('[role="tablist"]').count();
    const hasAI = await page.evaluate(() => {
      const tls = document.querySelectorAll('[role="tablist"]');
      for (const tl of tls) {
        if (tl.textContent?.includes('问AI')) return true;
      }
      return false;
    });
    
    console.log(`  [${i+1}/20] tablist数: ${count}, 包含问AI: ${hasAI}`);
    if (hasAI) {
      tablistReady = true;
      break;
    }
    await page.waitForTimeout(1000);
  }
  
  if (!tablistReady) {
    console.log('tablist 未出现!');
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'no_tablist.png') });
    
    // 最后尝试：打印页面状态
    const bodyLen = await page.evaluate(() => document.body?.innerHTML?.length || 0);
    console.log(`body HTML长度: ${bodyLen}`);
    
    // 搜索所有包含 "问AI" 或 "详情" 的元素
    const searchText = await page.evaluate(() => {
      const results = [];
      document.querySelectorAll('*').forEach(el => {
        const t = el.textContent?.trim() || '';
        if (t.includes('问AI') || t.includes('详情TA的作品评论') || t.includes('相关推荐')) {
          const r = el.getBoundingClientRect();
          results.push({
            tag: el.tagName,
            text: t.substring(0, 100),
            x: Math.round(r.x), y: Math.round(r.y),
            w: Math.round(r.width), h: Math.round(r.height)
          });
        }
      });
      return results;
    });
    console.log(`包含关键词的元素: ${searchText.length}`);
    for (const s of searchText) {
      console.log(`  <${s.tag}> [${s.x},${s.y}] ${s.w}x${s.h} "${s.text}"`);
    }
    
    await context.close();
    return;
  }
  
  console.log('\ntablist 已就绪!');
  await page.screenshot({ path: path.join(OUTPUT_DIR, '01_tablist_ready.png') });
  
  // ===== 详细分析 =====
  const tabInfo = await page.evaluate(() => {
    const results = [];
    const tablists = document.querySelectorAll('[role="tablist"]');
    
    tablists.forEach((tl, i) => {
      const tlRect = tl.getBoundingClientRect();
      const text = tl.textContent?.trim() || '';
      
      if (text.includes('问AI')) {
        const children = Array.from(tl.children);
        const childInfo = children.map((child, j) => {
          const cr = child.getBoundingClientRect();
          return {
            index: j,
            tag: child.tagName,
            text: child.textContent?.trim() || '',
            x: Math.round(cr.x), y: Math.round(cr.y),
            w: Math.round(cr.width), h: Math.round(cr.height),
            visible: cr.width > 0 && cr.height > 0,
            html: child.outerHTML?.substring(0, 400) || ''
          };
        });
        
        results.push({
          index: i,
          tlX: Math.round(tlRect.x), tlY: Math.round(tlRect.y),
          tlW: Math.round(tlRect.width), tlH: Math.round(tlRect.height),
          children: childInfo
        });
      }
    });
    
    return results;
  });
  
  console.log(`包含问AI的tablist: ${tabInfo.length} 个`);
  for (const tl of tabInfo) {
    console.log(`\nTablist #${tl.index}: [${tl.tlX},${tl.tlY}] ${tl.tlW}x${tl.tlH}`);
    for (const child of tl.children) {
      console.log(`  [${child.index}] <${child.tag}> [${child.x},${child.y}] ${child.w}x${child.h} visible=${child.visible}`);
      console.log(`       "${child.text}"`);
      console.log(`       HTML: ${child.html}`);
    }
  }
  
  // ===== 点击 "问AI" =====
  console.log('\n=== 点击 "问AI" ===');
  
  const clickR = await page.evaluate(() => {
    const tablists = document.querySelectorAll('[role="tablist"]');
    for (const tl of tablists) {
      if (!tl.textContent?.includes('问AI')) continue;
      
      // 直接找子元素
      for (const child of tl.children) {
        if (child.textContent?.trim() === '问AI') {
          child.click();
          const r = child.getBoundingClientRect();
          return { ok: true, method: 'direct-child', tag: child.tagName, x: Math.round(r.x+r.width/2), y: Math.round(r.y+r.height/2) };
        }
      }
      
      // 找更深层
      for (const el of tl.querySelectorAll('*')) {
        if (el.textContent?.trim() === '问AI' && el.children.length === 0) {
          el.click();
          const r = el.getBoundingClientRect();
          return { ok: true, method: 'deep-child', tag: el.tagName, x: Math.round(r.x+r.width/2), y: Math.round(r.y+r.height/2) };
        }
      }
      
      // 用坐标点击
      for (const child of tl.children) {
        const t = child.textContent?.trim() || '';
        if (t.includes('问AI')) {
          child.click();
          const r = child.getBoundingClientRect();
          return { ok: true, method: 'fuzzy-child', tag: child.tagName, x: Math.round(r.x+r.width/2), y: Math.round(r.y+r.height/2) };
        }
      }
    }
    return { ok: false };
  });
  
  console.log(JSON.stringify(clickR));
  
  if (clickR.ok) {
    console.log('✅ 点击成功！等待...');
    await page.waitForTimeout(10000);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '02_after_click.png') });
    
    // 提取
    const extracts = await page.evaluate(() => {
      const results = [];
      
      // 重点：右侧大于视频描述区域
      const allDivs = document.querySelectorAll('div, section, article');
      for (const div of allDivs) {
        const rect = div.getBoundingClientRect();
        const text = div.textContent?.trim() || '';
        
        // 找视频描述右侧的大段文字 (x > 视频左侧 + 视频宽度)
        if (rect.x > 800 && rect.width > 300 && text.length > 200) {
          results.push({
            pos: `[${Math.round(rect.x)},${Math.round(rect.y)}] ${Math.round(rect.width)}x${Math.round(rect.height)}`,
            cls: div.className?.substring(0, 80) || '',
            len: text.length,
            text: text.substring(0, 4000)
          });
        }
      }
      
      // 如果没找到右侧内容，返回所有大于200字且宽度大于300的
      if (results.length === 0) {
        for (const div of allDivs) {
          const rect = div.getBoundingClientRect();
          const text = div.textContent?.trim() || '';
          if (rect.width > 300 && text.length > 500 && text.length < 10000) {
            results.push({
              pos: `[${Math.round(rect.x)},${Math.round(rect.y)}]`,
              cls: div.className?.substring(0, 80) || '',
              len: text.length,
              text: text.substring(0, 4000)
            });
            if (results.length >= 3) break;
          }
        }
      }
      
      return results;
    });
    
    console.log(`\n=== 提取到 ${extracts.length} 个内容块 ===`);
    for (const e of extracts) {
      console.log(`\n--- ${e.pos} ${e.cls} (${e.len} chars) ---`);
      console.log(e.text);
      console.log(`--- END ---`);
    }
    
    const outFile = path.join(OUTPUT_DIR, 'ai_result_v4.txt');
    fs.writeFileSync(outFile, extracts.map((e,i) => `## Content Block ${i+1}\n\n${e.text}`).join('\n\n---\n\n'));
    console.log(`\n保存: ${outFile}`);
  } else {
    console.log('❌ 点击失败');
  }
  
  console.log('\n浏览器保持打开 60 秒...');
  await page.waitForTimeout(60000);
  await context.close();
})();
