/**
 * Douyin 问AI - 点击并提取内容
 * 目标: 点击 "问AI" tab，提取 AI 生成的内容
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
  
  console.log('=== 1. 导航到页面 ===');
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  
  // 等待页面加载
  try {
    await page.waitForSelector('video, [class*="player"], [class*="modal-video"]', { timeout: 15000 });
    console.log('视频播放器已加载');
  } catch(e) {
    console.log('未检测到视频播放器，继续...');
  }
  await page.waitForTimeout(5000);
  
  // 截图初始状态
  await page.screenshot({ path: path.join(OUTPUT_DIR, '01_initial.png') });
  
  // ===== 尝试多种方式点击 "问AI" =====
  console.log('\n=== 2. 尝试点击 "问AI" ===');
  
  let clicked = false;
  const clickStrategies = [
    // 策略1: 通过 text 精确匹配
    async () => {
      console.log('  策略1: page.getByText("问AI", { exact: true })');
      const btn = page.getByText('问AI', { exact: true });
      const count = await btn.count();
      console.log(`    找到 ${count} 个`);
      if (count > 0) {
        const first = btn.first();
        const visible = await first.isVisible();
        console.log(`    可见: ${visible}`);
        if (visible) {
          await first.click({ timeout: 5000 });
          return true;
        }
      }
      return false;
    },
    // 策略2: 通过 role=tab
    async () => {
      console.log('  策略2: page.getByRole("tab", { name: "问AI" })');
      const btn = page.getByRole('tab', { name: '问AI' });
      const count = await btn.count();
      console.log(`    找到 ${count} 个`);
      if (count > 0) {
        const first = btn.first();
        const visible = await first.isVisible();
        console.log(`    可见: ${visible}`);
        if (visible) {
          await first.click({ timeout: 5000 });
          return true;
        }
      }
      return false;
    },
    // 策略3: 找包含"问AI"文本的可见元素
    async () => {
      console.log('  策略3: 搜索所有包含"问AI"文本的可见元素');
      const elements = await page.evaluate(() => {
        const results = [];
        const walker = document.createTreeWalker(
          document.body,
          NodeFilter.SHOW_ELEMENT,
          {
            acceptNode: (node) => {
              if (node.textContent?.trim() === '问AI') {
                return NodeFilter.FILTER_ACCEPT;
              }
              return NodeFilter.FILTER_SKIP;
            }
          }
        );
        while (walker.nextNode()) {
          const el = walker.currentNode;
          const rect = el.getBoundingClientRect();
          results.push({
            tag: el.tagName,
            cls: el.className?.substring?.(0, 100) || '',
            text: el.textContent?.trim(),
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            w: Math.round(rect.width),
            h: Math.round(rect.height),
            visible: rect.width > 0 && rect.height > 0
          });
        }
        return results;
      });
      
      for (const el of elements) {
        console.log(`    <${el.tag}> class="${el.cls}" [${el.x},${el.y}] ${el.w}x${el.h} visible=${el.visible}`);
      }
      
      // 找可见的并且合适的
      const visible = elements.filter(e => e.visible);
      if (visible.length > 0) {
        // 尝试通过位置点击
        const target = visible[0];
        console.log(`    尝试点击 [${target.x + target.w/2}, ${target.y + target.h/2}]`);
        await page.mouse.click(target.x + target.w/2, target.y + target.h/2);
        return true;
      }
      return false;
    },
    // 策略4: 使用 CSS 选择器找 tab 容器中的元素
    async () => {
      console.log('  策略4: 在 tablist 中搜索');
      const result = await page.evaluate(() => {
        const tablists = document.querySelectorAll('[role="tablist"]');
        for (const tl of tablists) {
          const text = tl.textContent || '';
          if (text.includes('问AI')) {
            // 找到问AI这个子元素
            const children = tl.children;
            for (const child of children) {
              if (child.textContent?.trim() === '问AI') {
                const rect = child.getBoundingClientRect();
                return {
                  found: true,
                  x: Math.round(rect.x + rect.width/2),
                  y: Math.round(rect.y + rect.height/2),
                  tag: child.tagName,
                  cls: child.className?.substring?.(0, 100) || ''
                };
              }
            }
            // 尝试找更深的子元素
            const all = tl.querySelectorAll('*');
            for (const el of all) {
              if (el.textContent?.trim() === '问AI' && el.children.length === 0) {
                const rect = el.getBoundingClientRect();
                return {
                  found: true,
                  x: Math.round(rect.x + rect.width/2),
                  y: Math.round(rect.y + rect.height/2),
                  tag: el.tagName,
                  cls: el.className?.substring?.(0, 100) || ''
                };
              }
            }
          }
        }
        return { found: false };
      });
      
      console.log(`    结果: ${JSON.stringify(result)}`);
      if (result.found) {
        await page.mouse.click(result.x, result.y);
        return true;
      }
      return false;
    }
  ];
  
  for (const strategy of clickStrategies) {
    try {
      const success = await strategy();
      if (success) {
        clicked = true;
        console.log('    ✅ 点击成功！');
        break;
      }
    } catch(e) {
      console.log(`    ❌ 失败: ${e.message?.substring(0, 100)}`);
    }
    console.log('    ⏭ 尝试下一个策略...');
  }
  
  if (!clicked) {
    console.log('\n=== ❌ 所有策略都失败了 ===');
    console.log('保存当前页面 HTML 用于分析...');
    const html = await page.content();
    fs.writeFileSync(path.join(OUTPUT_DIR, 'page_source.html'), html);
    console.log('HTML 已保存到 page_source.html');
    await context.close();
    return;
  }
  
  // ===== 等待 AI 内容加载 =====
  console.log('\n=== 3. 等待 AI 内容加载 ===');
  await page.waitForTimeout(5000);
  
  // 截图点击后的状态
  await page.screenshot({ path: path.join(OUTPUT_DIR, '02_after_click.png') });
  
  // ===== 提取内容 =====
  console.log('\n=== 4. 提取 AI 内容 ===');
  
  // 获取整个页面的文本
  const pageText = await page.evaluate(() => document.body.innerText);
  
  // 尝试找 AI 回复容器
  const aiContent = await page.evaluate(() => {
    // 搜索可能的 AI 内容容器
    const selectors = [
      '[class*="ai"]', '[class*="AI"]',
      '[class*="answer"]', '[class*="reply"]',
      '[class*="result"]', '[class*="content"]',
      '[class*="markdown"]', '[class*="message"]'
    ];
    
    const results = [];
    for (const sel of selectors) {
      const els = document.querySelectorAll(sel);
      for (const el of els) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 100 && rect.height > 50) {
          const text = el.textContent?.trim() || '';
          if (text.length > 50) {
            results.push({
              selector: sel,
              cls: el.className?.substring?.(0, 100) || '',
              textLen: text.length,
              text: text.substring(0, 500)
            });
          }
        }
      }
    }
    return results;
  });
  
  console.log(`找到 ${aiContent.length} 个可能的内容区域`);
  for (const c of aiContent) {
    console.log(`  [${c.selector}] class="${c.cls}" len=${c.textLen}`);
    console.log(`  ---`);
    console.log(`  ${c.text.substring(0, 300)}`);
    console.log(`  ---`);
  }
  
  // 保存完整文本
  const outputFile = path.join(OUTPUT_DIR, 'ai_content.txt');
  fs.writeFileSync(outputFile, pageText);
  console.log(`\n完整页面文本保存到: ${outputFile}`);
  console.log(`文本长度: ${pageText.length} 字符`);
  
  // 保存 Markdown 格式
  const mdFile = path.join(OUTPUT_DIR, 'ai_content.md');
  const title = await page.title();
  fs.writeFileSync(mdFile, `# ${title}\n\n## 问AI 内容\n\n${pageText}`);
  console.log(`Markdown 保存到: ${mdFile}`);
  
  console.log('\n=== 完成 ===');
  console.log('浏览器保持打开 60 秒...');
  await page.waitForTimeout(60000);
  await context.close();
})();
