/**
 * Douyin 问AI v6 - 深入检查 AI Panel 内容 + 尝试 API 方式
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
  
  // 监听网络请求，寻找 AI 相关的 API
  const networkLogs = [];
  page.on('request', req => {
    const url = req.url();
    if (url.includes('ai') || url.includes('AI') || url.includes('aisearch') || 
        url.includes('chat') || url.includes('llm') || url.includes('summary')) {
      networkLogs.push({ type: 'request', url: url.substring(0, 200), method: req.method() });
    }
  });
  page.on('response', resp => {
    const url = resp.url();
    if (url.includes('ai') || url.includes('AI') || url.includes('aisearch') ||
        url.includes('chat') || url.includes('llm') || url.includes('summary')) {
      networkLogs.push({ type: 'response', url: url.substring(0, 200), status: resp.status() });
    }
  });
  
  console.log('=== 导航 ===');
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(8000);
  
  // 检查当前视频
  const videoInfo = await page.evaluate(() => {
    // 尝试多种方式获取视频ID
    const url = window.location.href;
    const videoEl = document.querySelector('video');
    const src = videoEl?.src || videoEl?.querySelector('source')?.src || '';
    
    // 查找页面中的视频标题
    const titleEls = document.querySelectorAll('[class*="video-info-detail"], [class*="title"]');
    let title = '';
    for (const el of titleEls) {
      const t = el.textContent?.trim();
      if (t && t.length > 5 && t.length < 200) {
        title = t;
        break;
      }
    }
    
    return { url, videoSrc: src.substring(0, 200), title };
  });
  console.log('视频信息:', JSON.stringify(videoInfo, null, 2));
  
  // 等 tablist
  for (let i = 0; i < 30; i++) {
    const c = await page.locator('[role="tablist"]').count();
    if (c >= 2) break;
    await page.waitForTimeout(1000);
  }
  await page.waitForTimeout(3000);
  
  // ===== 检查 AI Panel 的 72 字节 =====
  const panelHTML = await page.evaluate(() => {
    const panel = document.querySelector('#semiTabPanelai_card');
    if (!panel) return { error: 'not found' };
    
    return {
      outerHTML: panel.outerHTML,
      innerHTML: panel.innerHTML,
      childCount: panel.children.length,
      children: Array.from(panel.children).map(c => ({
        tag: c.tagName,
        cls: c.className?.substring(0, 80),
        text: c.textContent?.trim()?.substring(0, 200),
        html: c.outerHTML?.substring(0, 300)
      }))
    };
  });
  
  console.log('\n=== AI Panel 内部结构 ===');
  console.log(JSON.stringify(panelHTML, null, 2));
  
  // ===== 尝试点击 detail tab 再回来 =====
  console.log('\n=== 尝试切换 tab 触发加载 ===');
  
  // 先点 "详情"
  await page.locator('#semiTabdetail_tab').click({ timeout: 5000 });
  await page.waitForTimeout(2000);
  
  // 再点回 "问AI"
  await page.locator('#semiTabai_card').click({ timeout: 5000 });
  await page.waitForTimeout(5000);
  
  // 检查是否加载了
  const afterToggle = await page.evaluate(() => {
    const panel = document.querySelector('#semiTabPanelai_card');
    return {
      textLen: (panel?.textContent?.trim() || '').length,
      htmlLen: panel?.innerHTML?.length || 0,
      preview: panel?.textContent?.trim()?.substring(0, 500) || ''
    };
  });
  console.log('切换后:', JSON.stringify(afterToggle));
  
  // ===== 截图 =====
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v6_full.png'), fullPage: false });
  
  // ===== AI 相关网络请求 =====
  console.log(`\n=== AI 相关网络请求 (${networkLogs.length}) ===`);
  for (const log of networkLogs) {
    console.log(`  [${log.type}] ${log.method || ''} ${log.status || ''} ${log.url}`);
  }
  
  // ===== 尝试通过 API 获取 =====
  console.log('\n=== 尝试直接 API 调用 ===');
  
  // 尝试 Douyin 的 AI 搜索 API
  const apiResults = [];
  
  // API 1: 视频字幕/文案 API
  try {
    const resp = await page.evaluate(async () => {
      try {
        const r = await fetch(`https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=${VIDEO_ID}&aid=6383`, {
          headers: { 'User-Agent': navigator.userAgent }
        });
        const data = await r.json();
        return { api: 'aweme_detail', status: r.status, keys: Object.keys(data).join(', ') };
      } catch(e) {
        return { api: 'aweme_detail', error: e.message };
      }
    });
    apiResults.push(resp);
  } catch(e) {}
  
  console.log('API 结果:', JSON.stringify(apiResults, null, 2));
  
  console.log('\n浏览器保持打开 60 秒...');
  await page.waitForTimeout(60000);
  await context.close();
})();
