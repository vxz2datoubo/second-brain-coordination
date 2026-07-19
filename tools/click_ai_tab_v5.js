/**
 * Douyin 问AI v5 - 精准提取 semiTabPanelai_card
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
  
  // 等待视频加载
  try { await page.waitForSelector('video', { timeout: 15000 }); } catch(e) {}
  await page.waitForTimeout(5000);
  try { await page.locator('video').first().click({ timeout: 3000 }); } catch(e) {}
  await page.waitForTimeout(3000);
  
  // ===== 等待 tablist 出现 =====
  console.log('等待 tablist...');
  let ready = false;
  for (let i = 0; i < 30; i++) {
    const count = await page.locator('[role="tablist"]').count();
    if (count >= 2) { ready = true; break; }
    await page.waitForTimeout(1000);
  }
  if (!ready) {
    console.log('Tablist 未出现');
    await context.close(); return;
  }
  console.log('Tablist 已就绪');
  await page.waitForTimeout(2000);
  
  // ===== 检查当前状态 =====
  let state = await page.evaluate(() => {
    const aiTab = document.querySelector('#semiTabai_card');
    const aiPanel = document.querySelector('#semiTabPanelai_card');
    return {
      aiTabExists: !!aiTab,
      aiTabSelected: aiTab?.getAttribute('aria-selected'),
      aiTabVisible: aiTab ? aiTab.getBoundingClientRect().width > 0 : false,
      aiPanelExists: !!aiPanel,
      aiPanelText: aiPanel?.textContent?.trim()?.substring(0, 500) || '',
      aiPanelHTMLlen: aiPanel?.innerHTML?.length || 0
    };
  });
  console.log('初始状态:', JSON.stringify(state, null, 2));
  
  // ===== 点击 "问AI" (如果未选中) =====
  if (state.aiTabSelected !== 'true') {
    console.log('点击问AI...');
    await page.locator('#semiTabai_card').click({ timeout: 5000 });
    await page.waitForTimeout(5000);
  } else {
    console.log('问AI 已选中');
  }
  
  // ===== 等待 AI 内容加载 =====
  console.log('等待 AI 内容...');
  
  // 等待 panel 内容变长
  let aiContent = '';
  for (let i = 0; i < 20; i++) {
    const info = await page.evaluate(() => {
      const panel = document.querySelector('#semiTabPanelai_card');
      const text = panel?.textContent?.trim() || '';
      return {
        len: text.length,
        htmlLen: panel?.innerHTML?.length || 0,
        hasMarkdown: panel?.querySelector('p, h1, h2, h3, li, code, pre') ? true : false,
        classList: panel?.className || '',
        preview: text.substring(0, 300)
      };
    });
    console.log(`  [${i+1}/20] textLen=${info.len} htmlLen=${info.htmlLen} hasMarkdown=${info.hasMarkdown}`);
    if (info.len > 100) {
      aiContent = info;
      break;
    }
    await page.waitForTimeout(2000);
  }
  
  // ===== 截图 =====
  await page.screenshot({ path: path.join(OUTPUT_DIR, '01_ai_state.png') });
  
  // 截图 AI panel
  try {
    const panel = page.locator('#semiTabPanelai_card');
    await panel.screenshot({ path: path.join(OUTPUT_DIR, '02_ai_panel.png') });
    console.log('AI panel 截图已保存');
  } catch(e) {
    console.log('截图 AI panel 失败:', e.message?.substring(0, 80));
  }
  
  // ===== 提取完整 AI 内容 =====
  console.log('\n=== AI Panel 内容 ===');
  
  const finalContent = await page.evaluate(() => {
    const panel = document.querySelector('#semiTabPanelai_card');
    if (!panel) return { error: 'panel not found' };
    
    // 方法1: innerText
    const text = panel.innerText || '';
    
    // 方法2: 结构化提取 - 找所有段落/列表
    const structured = [];
    const elements = panel.querySelectorAll('p, h1, h2, h3, h4, li, div, span');
    for (const el of elements) {
      const t = el.textContent?.trim();
      if (t && t.length > 10) {
        structured.push(`[${el.tagName}] ${t}`);
      }
    }
    
    // 方法3: 完整 HTML
    const html = panel.innerHTML || '';
    
    return {
      textLen: text.length,
      text: text,
      structuredLen: structured.length,
      structured: structured.join('\n'),
      htmlLen: html.length
    };
  });
  
  console.log(`文本长度: ${finalContent.textLen}`);
  console.log(`结构化条目: ${finalContent.structuredLen}`);
  console.log(`HTML长度: ${finalContent.htmlLen}`);
  
  if (finalContent.textLen > 0) {
    console.log('\n--- 完整内容 ---');
    console.log(finalContent.text);
    console.log('--- END ---');
  } else {
    console.log('\n⚠️ AI Panel 为空！');
    
    // 检查整个 modal 内的内容
    const modalContent = await page.evaluate(() => {
      const modal = document.querySelector('[class*="modal-video"]');
      if (!modal) return { error: 'modal not found' };
      
      // 找 modal 内的所有大段文本
      const texts = [];
      const walker = document.createTreeWalker(modal, NodeFilter.SHOW_TEXT);
      let node;
      let fullText = '';
      while (node = walker.nextNode()) {
        fullText += node.textContent;
      }
      return { modalText: fullText.substring(0, 3000) };
    });
    console.log('Modal 文本:', modalContent.modalText?.substring(0, 2000));
  }
  
  // 保存
  const outFile = path.join(OUTPUT_DIR, 'ai_content_v5.md');
  fs.writeFileSync(outFile, 
    `# 问AI 内容\n\n` +
    `## 原始文本\n\n${finalContent.text || '(空)'}\n\n` +
    `## 结构化\n\n${finalContent.structured || '(空)'}\n`
  );
  console.log(`\n保存: ${outFile}`);
  
  console.log('\n浏览器保持打开 60 秒...');
  await page.waitForTimeout(60000);
  await context.close();
})();
