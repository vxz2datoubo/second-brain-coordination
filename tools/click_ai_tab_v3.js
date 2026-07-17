/**
 * Douyin 问AI v3 - 找 tablist 并点击其中的 "问AI"
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
  await page.waitForTimeout(8000); // 给足时间让弹窗完全渲染
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, '01_full.png') });
  
  // ===== 详细分析 tablist 结构 =====
  console.log('\n=== 分析所有 tablist ===');
  
  const tabInfo = await page.evaluate(() => {
    const results = [];
    const tablists = document.querySelectorAll('[role="tablist"]');
    
    tablists.forEach((tl, i) => {
      const tlRect = tl.getBoundingClientRect();
      const children = Array.from(tl.children);
      
      const childInfo = children.map((child, j) => {
        const cr = child.getBoundingClientRect();
        return {
          index: j,
          tag: child.tagName,
          cls: child.className?.substring?.(0, 80) || '',
          role: child.getAttribute('role') || '',
          text: child.textContent?.trim() || '',
          x: Math.round(cr.x), y: Math.round(cr.y),
          w: Math.round(cr.width), h: Math.round(cr.height),
          visible: cr.width > 0 && cr.height > 0,
          html: child.outerHTML?.substring(0, 200) || ''
        };
      });
      
      results.push({
        index: i,
        x: Math.round(tlRect.x), y: Math.round(tlRect.y),
        w: Math.round(tlRect.width), h: Math.round(tlRect.height),
        childCount: children.length,
        totalText: tl.textContent?.trim()?.substring(0, 200) || '',
        children: childInfo
      });
    });
    
    return results;
  });
  
  console.log(`找到 ${tabInfo.length} 个 tablist`);
  for (const tl of tabInfo) {
    console.log(`\nTablist #${tl.index}: [${tl.x},${tl.y}] ${tl.w}x${tl.h}`);
    console.log(`  文本: "${tl.totalText}"`);
    console.log(`  子元素 (${tl.childCount}):`);
    for (const child of tl.children) {
      console.log(`    [${child.index}] <${child.tag}> role="${child.role}" class="${child.cls}"`);
      console.log(`        位置: [${child.x},${child.y}] ${child.w}x${child.h} visible=${child.visible}`);
      console.log(`        文本: "${child.text}"`);
      console.log(`        HTML: ${child.html}`);
    }
  }
  
  // ===== 找包含 "问AI" 的 tablist 并点击 =====
  console.log('\n=== 尝试点击视频 tablist 中的 "问AI" ===');
  
  const clickResult = await page.evaluate(() => {
    const tablists = document.querySelectorAll('[role="tablist"]');
    
    for (const tl of tablists) {
      const text = tl.textContent || '';
      if (text.includes('问AI') && text.includes('评论')) {
        // 这个就是视频的 tablist
        const children = Array.from(tl.children);
        for (const child of children) {
          if (child.textContent?.trim() === '问AI') {
            const rect = child.getBoundingClientRect();
            // 点击
            child.click();
            return {
              success: true,
              method: 'tablist-child-click',
              x: Math.round(rect.x + rect.width/2),
              y: Math.round(rect.y + rect.height/2),
              tag: child.tagName,
              text: child.textContent?.trim()
            };
          }
        }
        
        // 如果子元素中没有精确匹配，尝试找更深层的
        const allDescendants = tl.querySelectorAll('*');
        for (const desc of allDescendants) {
          if (desc.textContent?.trim() === '问AI' && desc.children.length === 0) {
            const rect = desc.getBoundingClientRect();
            desc.click();
            return {
              success: true,
              method: 'tablist-descendant-click',
              x: Math.round(rect.x + rect.width/2),
              y: Math.round(rect.y + rect.height/2),
              tag: desc.tagName,
              text: desc.textContent?.trim()
            };
          }
        }
        
        // 如果还不成功，返回tablist结构供分析
        const childDetails = Array.from(tl.children).map(c => ({
          tag: c.tagName,
          text: c.textContent?.trim(),
          cls: c.className?.substring(0, 60),
          html: c.outerHTML?.substring(0, 300)
        }));
        
        // 也搜索所有后代
        const aiDescendants = [];
        for (const desc of tl.querySelectorAll('*')) {
          const t = desc.textContent?.trim();
          if (t && (t.includes('AI') || t.includes('问'))) {
            const r = desc.getBoundingClientRect();
            aiDescendants.push({
              tag: desc.tagName,
              text: t.substring(0, 50),
              x: Math.round(r.x), y: Math.round(r.y),
              w: Math.round(r.width), h: Math.round(r.height)
            });
          }
        }
        
        return {
          success: false,
          tlText: text.substring(0, 200),
          childCount: children.length,
          children: childDetails,
          aiDescendants: aiDescendants.slice(0, 10)
        };
      }
    }
    
    return { success: false, error: 'no matching tablist' };
  });
  
  console.log(JSON.stringify(clickResult, null, 2));
  
  if (clickResult.success) {
    console.log('\n✅ 点击成功！等待 AI 内容加载...');
    await page.waitForTimeout(8000);
    await page.screenshot({ path: path.join(OUTPUT_DIR, '02_after_click.png') });
    
    // 提取内容
    console.log('\n=== 提取内容 ===');
    const fullText = await page.evaluate(() => document.body.innerText);
    
    // 重点提取右侧面板的内容
    const rightContent = await page.evaluate(() => {
      const panels = document.querySelectorAll('[class*="right"], [class*="side"], [class*="panel"], [class*="detail-info"]');
      const results = [];
      for (const p of panels) {
        const rect = p.getBoundingClientRect();
        if (rect.x > 400 && rect.width > 200 && rect.height > 100) {
          const text = p.textContent?.trim() || '';
          if (text.length > 50) {
            results.push({
              cls: p.className?.substring(0, 80),
              x: Math.round(rect.x),
              w: Math.round(rect.width),
              h: Math.round(rect.height),
              len: text.length,
              text: text.substring(0, 3000)
            });
          }
        }
      }
      return results;
    });
    
    console.log(`右侧面板: ${rightContent.length} 个`);
    for (const r of rightContent) {
      console.log(`\n--- Panel [${r.x}] ${r.w}x${r.h} (${r.len} chars) ---`);
      console.log(r.text);
    }
    
    // 保存
    const outFile = path.join(OUTPUT_DIR, 'ai_result_v3.txt');
    fs.writeFileSync(outFile, 
      rightContent.map(r => `## Panel\n\n${r.text}`).join('\n\n---\n\n') +
      `\n\n## Full Text\n\n${fullText.substring(0, 10000)}`
    );
    console.log(`\n结果保存: ${outFile}`);
  }
  
  console.log('\n浏览器保持打开 60 秒...');
  await page.waitForTimeout(60000);
  await context.close();
})();
