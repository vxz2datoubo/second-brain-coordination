/**
 * Douyin AI Chat - 点击问AI、开启深度思考、输入提示词、获取回复
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const VIDEO_ID = '7650106006073502949';
const URL = `https://www.douyin.com/jingxuan?modal_id=${VIDEO_ID}`;
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUTPUT_DIR = 'F:/ai/tools/screenshots';

const PROMPT = `把视频完全文案发给我，接着根据文案和视频内容整合出文案+资料+背景+视频中出现的错误或偏见或者在其他条件情况会有不同结果的内容一并整理出来，然后再单独另外整合的该内容下的所有评价然后分析整体视频和评价的矛盾点在哪，还有需求点在哪，可挖掘的市场或者可着重表现的点在哪等。如果画面中有重要图片请提取图片中的文案下来，画面中出现的文案也要全部提取下来。`;

(async () => {
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    viewport: { width: 1920, height: 1080 },
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });

  const page = await context.newPage();
  
  // ===== 1. 导航到视频页 =====
  console.log('=== 1. 导航到视频页 ===');
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  
  // 等待页面稳定
  await page.waitForTimeout(5000);
  
  // ===== 2. 点击「问AI」标签 =====
  console.log('\n=== 2. 点击「问AI」标签 ===');
  try {
    await page.locator('#semiTabai_card').click({ timeout: 10000 });
    console.log('✅ 已点击问AI标签');
  } catch(e) {
    console.log('❌ 点击问AI失败:', e.message);
    await context.close();
    return;
  }
  
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, '01_ai_opened.png') });
  
  // ===== 3. 开启「深度思考」=====
  console.log('\n=== 3. 开启「深度思考」===');
  try {
    // 查找深度思考按钮（通过文本或 class）
    const deepThinkBtn = page.locator('text=深度思考, [class*="deep"], [class*="think"], button:has-text("深度")').first();
    
    // 检查是否已选中
    const isActive = await deepThinkBtn.evaluate(el => {
      return el.classList.contains('active') || el.getAttribute('aria-selected') === 'true' || el.classList.contains('selected');
    }).catch(() => false);
    
    if (!isActive) {
      await deepThinkBtn.click({ timeout: 5000 });
      console.log('✅ 已开启深度思考');
    } else {
      console.log('✅ 深度思考已是开启状态');
    }
  } catch(e) {
    console.log('⚠️ 深度思考按钮处理:', e.message);
  }
  
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, '02_deep_think.png') });
  
  // ===== 4. 在输入框输入提示词 =====
  console.log('\n=== 4. 输入提示词 ===');
  try {
    // 查找输入框（placeholder 或特定 class）
    const inputBox = page.locator('[placeholder*="问AI"], [placeholder*="提问"], textarea, [contenteditable="true"], input[type="text"]').first();
    await inputBox.fill(PROMPT);
    console.log('✅ 已输入提示词');
  } catch(e) {
    console.log('❌ 输入失败:', e.message);
    await context.close();
    return;
  }
  
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, '03_prompt_entered.png') });
  
  // ===== 5. 发送消息 =====
  console.log('\n=== 5. 发送消息 ===');
  try {
    // 查找发送按钮
    const sendBtn = page.locator('button:has-text("发送"), [class*="send"], svg[class*="send"], button[type="submit"]').first();
    
    // 或者按 Enter
    await sendBtn.click({ timeout: 5000 });
    console.log('✅ 已发送');
  } catch(e) {
    console.log('尝试按 Enter...');
    await page.keyboard.press('Enter');
  }
  
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, '04_sending.png') });
  
  // ===== 6. 等待回复（约1分钟）=====
  console.log('\n=== 6. 等待AI回复（约60秒）===');
  
  // 等待回复出现 - 检查新消息
  let lastContent = '';
  let stableCount = 0;
  const maxWait = 90; // 最多等90秒
  
  for (let i = 0; i < maxWait; i++) {
    await page.waitForTimeout(1000);
    
    // 获取当前AI回复内容
    const currentContent = await page.evaluate(() => {
      // 找AI回复区域 - 通常是最后一条消息
      const messages = document.querySelectorAll('[class*="message"], [class*="chat"], [class*="answer"], [class*="reply"]');
      const lastMsg = messages[messages.length - 1];
      return lastMsg?.textContent?.trim() || '';
    });
    
    // 检查内容是否稳定（连续3秒不变）
    if (currentContent && currentContent.length > 100) {
      if (currentContent === lastContent) {
        stableCount++;
        if (stableCount >= 3) {
          console.log(`✅ 回复已完成，长度: ${currentContent.length}`);
          break;
        }
      } else {
        stableCount = 0;
        lastContent = currentContent;
      }
      
      if (i % 10 === 0) {
        console.log(`  [${i}s] 内容长度: ${currentContent.length}`);
      }
    }
  }
  
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, '05_reply_done.png'), fullPage: false });
  
  // ===== 7. 复制回复内容 =====
  console.log('\n=== 7. 复制回复内容 ===');
  
  // 方法1: 找复制按钮
  let copied = false;
  try {
    const copyBtn = page.locator('button:has-text("复制"), [class*="copy"], svg[class*="copy"]').first();
    await copyBtn.click({ timeout: 5000 });
    console.log('✅ 点击复制按钮');
    copied = true;
  } catch(e) {
    console.log('未找到复制按钮，尝试其他方法');
  }
  
  // 方法2: 直接提取文本
  const aiReply = await page.evaluate(() => {
    // 找AI回复区域
    const selectors = [
      '[class*="message"]:last-of-type',
      '[class*="chat-item"]:last-of-type',
      '[class*="answer"]:last-of-type',
      '[class*="reply-content"]:last-of-type',
      '.semi-chat-content:last-child',
      '[class*="markdown"]:last-of-type'
    ];
    
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent.length > 50) {
        return {
          text: el.innerText,
          html: el.innerHTML
        };
      }
    }
    
    // 回退：找最大的文本块
    let maxText = '';
    let maxEl = null;
    document.querySelectorAll('div, section').forEach(el => {
      const t = el.textContent?.trim() || '';
      if (t.length > maxText.length && t.length < 50000) {
        maxText = t;
        maxEl = el;
      }
    });
    
    return maxEl ? { text: maxEl.innerText, html: maxEl.innerHTML } : { text: '', html: '' };
  });
  
  console.log(`\n回复长度: ${aiReply.text?.length || 0} 字符`);
  
  // 保存到文件
  const outputPath = path.join(OUTPUT_DIR, 'ai_reply.md');
  fs.writeFileSync(outputPath, 
    `# AI 回复\n\n## 提示词\n\n${PROMPT}\n\n## 回复内容\n\n${aiReply.text || '(空)'}\n\n## HTML\n\n\`\`\`html\n${aiReply.html?.substring(0, 5000) || '(空)'}\n\`\`\``
  );
  
  console.log(`✅ 已保存到: ${outputPath}`);
  
  // 显示内容摘要
  if (aiReply.text) {
    console.log('\n=== 回复摘要（前500字）===');
    console.log(aiReply.text.substring(0, 500));
    console.log('...');
  }
  
  console.log('\n完成！浏览器保持打开，你可以手动查看...');
  await page.waitForTimeout(60000);
  await context.close();
})();
