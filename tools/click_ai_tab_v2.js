/**
 * Douyin 问AI v2 - 精准定位视频弹窗内的"问AI"标签页
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
  
  console.log('=== 导航到页面 ===');
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  
  try {
    await page.waitForSelector('[class*="modal-video"]', { timeout: 15000 });
    console.log('弹窗视频已加载');
  } catch(e) {
    console.log('等待弹窗...');
  }
  await page.waitForTimeout(5000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, '01_initial.png') });
  
  // ===== 精准定位视频弹窗内的 "问AI" =====
  console.log('\n=== 定位视频弹窗内的 "问AI" ===');
  
  // 方法：用 JS 在弹窗容器内搜索
  const result = await page.evaluate(() => {
    // 找弹窗/视频详情容器
    const containers = document.querySelectorAll('[class*="modal"], [class*="detail"], [class*="video-info"], [class*="sliderVideo"], [class*="video-container"]');
    
    for (const container of containers) {
      const rect = container.getBoundingClientRect();
      if (rect.width < 500 || rect.height < 300) continue; // 跳过太小的
      
      // 在这个容器内搜索 "问AI"
      const allElements = container.querySelectorAll('*');
      for (const el of allElements) {
        const text = el.textContent?.trim();
        if (text === '问AI' && el.children.length === 0) {
          const elRect = el.getBoundingClientRect();
          if (elRect.width > 10 && elRect.height > 10) {
            // 确保不在页面顶部（排除全局导航）
            if (elRect.y > 50) {
              return {
                found: true,
                method: 'modal-container-leaf',
                x: Math.round(elRect.x + elRect.width/2),
                y: Math.round(elRect.y + elRect.height/2),
                tag: el.tagName,
                cls: el.className?.substring?.(0, 100) || '',
                containerClass: container.className?.substring?.(0, 100) || '',
                containerSize: `${Math.round(rect.width)}x${Math.round(rect.height)}`,
                parentHTML: el.parentElement?.outerHTML?.substring(0, 300) || ''
              };
            }
          }
        }
      }
      
      // 如果上面没找到，搜索所有text包含"问AI"且不在顶部的元素
      for (const el of allElements) {
        const text = el.textContent?.trim();
        if (text && text.includes('问AI')) {
          const elRect = el.getBoundingClientRect();
          if (elRect.width > 10 && elRect.y > 50) {
            return {
              found: true,
              method: 'modal-container-any',
              x: Math.round(elRect.x + elRect.width/2),
              y: Math.round(elRect.y + elRect.height/2),
              tag: el.tagName,
              cls: el.className?.substring?.(0, 100) || '',
              text: text.substring(0, 100),
              containerClass: container.className?.substring?.(0, 100) || ''
            };
          }
        }
      }
    }
    
    // 如果弹窗容器内没找到，在整个页面搜索但排除顶部区域
    const allElements = document.querySelectorAll('body *');
    for (const el of allElements) {
      const text = el.textContent?.trim();
      if (text === '问AI') {
        const rect = el.getBoundingClientRect();
        if (rect.y > 100 && rect.width > 10 && rect.height > 10) {
          return {
            found: true,
            method: 'body-scan-y>100',
            x: Math.round(rect.x + rect.width/2),
            y: Math.round(rect.y + rect.height/2),
            tag: el.tagName,
            cls: el.className?.substring?.(0, 100) || '',
            siblings: Array.from(el.parentElement?.children || []).map(c => c.textContent?.trim()).join('|')
          };
        }
      }
    }
    
    return { found: false };
  });
  
  console.log(`定位结果: ${JSON.stringify(result, null, 2)}`);
  
  if (!result.found) {
    console.log('未找到弹窗内的问AI！');
    
    // 列出所有 "问AI" 元素及其位置
    const allAI = await page.evaluate(() => {
      const results = [];
      document.querySelectorAll('*').forEach(el => {
        if (el.textContent?.trim() === '问AI') {
          const r = el.getBoundingClientRect();
          results.push({
            tag: el.tagName,
            cls: el.className?.substring?.(0, 80),
            x: Math.round(r.x), y: Math.round(r.y),
            w: Math.round(r.width), h: Math.round(r.height),
            parentTag: el.parentElement?.tagName,
            parentCls: el.parentElement?.className?.substring?.(0, 80)
          });
        }
      });
      return results;
    });
    console.log(`页面中所有 "问AI" 元素 (${allAI.length}个):`);
    for (const ai of allAI) {
      console.log(`  <${ai.tag}> [${ai.x},${ai.y}] ${ai.w}x${ai.h} parent=<${ai.parentTag}>`);
    }
    
    await context.close();
    return;
  }
  
  // 点击
  console.log(`\n=== 点击 [${result.x}, ${result.y}] ===`);
  console.log(`元素: <${result.tag}> class="${result.cls}"`);
  console.log(`父级 HTML: ${result.parentHTML || 'N/A'}`);
  
  await page.mouse.click(result.x, result.y);
  console.log('点击完成！');
  
  // 等待加载
  await page.waitForTimeout(8000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, '02_after_click.png') });
  
  // ===== 提取内容 =====
  console.log('\n=== 提取 AI 内容 ===');
  
  // 尝试多种提取策略
  const extracts = await page.evaluate(() => {
    const results = { methods: [] };
    
    // 方法1: 找右侧面板中新出现的大段文本
    const rightSide = document.querySelectorAll('[class*="right"], [class*="side"], [class*="panel"], [class*="detail"]');
    for (const el of rightSide) {
      const rect = el.getBoundingClientRect();
      if (rect.x > 500 && rect.width > 300) {
        const text = el.textContent?.trim() || '';
        if (text.length > 100) {
          results.methods.push({
            method: 'right-panel',
            len: text.length,
            text: text.substring(0, 2000)
          });
        }
      }
    }
    
    // 方法2: 找新增的文本块
    const allDivs = document.querySelectorAll('div, section, article');
    for (const div of allDivs) {
      const text = div.textContent?.trim() || '';
      if (text.length > 300 && text.length < 10000) {
        const rect = div.getBoundingClientRect();
        if (rect.x > 400 && rect.width > 250) {
          // 检查是否包含AI相关关键词
          if (text.includes('AI') || text.includes('分析') || text.includes('总结') || text.includes('视频')) {
            results.methods.push({
              method: 'text-block',
              cls: div.className?.substring?.(0, 80) || '',
              len: text.length,
              text: text.substring(0, 2000)
            });
            break;
          }
        }
      }
    }
    
    // 方法3: 获取整个 body 文本
    results.fullText = (document.body?.innerText || '').substring(0, 5000);
    
    return results;
  });
  
  console.log(`提取方法数: ${extracts.methods.length}`);
  for (const m of extracts.methods) {
    console.log(`\n--- ${m.method} (${m.len} chars) ---`);
    console.log(m.text);
    console.log(`--- END ---`);
  }
  
  // 保存结果
  const outputPath = path.join(OUTPUT_DIR, 'ai_result.txt');
  let output = '';
  for (const m of extracts.methods) {
    output += `\n## ${m.method}\n\n${m.text}\n`;
  }
  output += `\n\n## Full Page Text\n\n${extracts.fullText}`;
  fs.writeFileSync(outputPath, output);
  console.log(`\n结果保存到: ${outputPath}`);
  
  console.log('\n浏览器保持打开 60 秒...');
  await page.waitForTimeout(60000);
  await context.close();
})();
