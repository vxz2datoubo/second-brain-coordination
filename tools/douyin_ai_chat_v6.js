/**
 * Douyin AI Chat v6 - 先提取视频信息，再传入AI
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const VIDEO_ID = '7650106006073502949';
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUTPUT_DIR = 'F:/ai/tools/screenshots';

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false, 
    viewport: { width: 1920, height: 1080 },
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });

  const page = await context.newPage();
  
  // ===== 步骤1: 访问视频页获取 cookies =====
  console.log('=== 1. 访问视频页 ===');
  await page.goto(`https://www.douyin.com/video/${VIDEO_ID}`, { 
    waitUntil: 'domcontentloaded', timeout: 30000 
  });
  await sleep(5000);
  
  const deviceId = await page.evaluate(() => {
    const m = document.cookie.match(/device_id=([^;]+)/);
    return m ? m[1] : '7651518205098608143';
  });
  
  // ===== 步骤2: 获取视频信息 =====
  console.log('\n=== 2. 获取视频信息 ===');
  
  // API: aweme_detail
  const awemeResp = await page.evaluate(async () => {
    const r = await fetch(`https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=${'7650106006073502949'}&aid=6383`);
    return await r.json();
  });
  
  const aweme = awemeResp.aweme_detail;
  
  // 提取关键信息
  const videoContext = {
    title: aweme.desc || '',
    author: aweme.author?.nickname || '',
    duration: `${Math.round((aweme.video?.duration || 0) / 1000)}秒`,
    createTime: new Date((aweme.create_time || 0) * 1000).toLocaleDateString(),
    tags: (aweme.text_extra || []).filter(t => t.hashtag_name).map(t => t.hashtag_name).join('、'),
    statistics: {
      digg: aweme.statistics?.digg_count || 0,
      comment: aweme.statistics?.comment_count || 0,
      share: aweme.statistics?.share_count || 0,
      collect: aweme.statistics?.collect_count || 0
    }
  };
  
  console.log(`视频: ${videoContext.title}`);
  console.log(`作者: ${videoContext.author}`);
  console.log(`时长: ${videoContext.duration}`);
  console.log(`点赞: ${videoContext.statistics.digg}`);
  
  // ===== 步骤3: 获取AI建议 =====
  console.log('\n=== 3. 获取AI建议 ===');
  
  const sugResp = await page.evaluate(async () => {
    const r = await fetch(`https://www.douyin.com/douyin/select/study/ai_assistant/watch/sug/get?device_platform=webapp&aid=6383&channel=channel_pc_web&item_id=7650106006073502949&update_version_code=170400&pc_client_type=1`);
    return await r.json();
  });
  
  const questions = (sugResp.question_list || []).map(q => q.content || q.question || '');
  console.log(`AI建议问题: ${questions.length}个`);
  
  // ===== 步骤4: 获取提及知识 =====
  console.log('\n=== 4. 获取知识点 ===');
  
  const mentionResp = await page.evaluate(async () => {
    const r = await fetch(`https://www.douyin.com/douyin/select/study/ai_assistant/watch/current_mention/get?device_platform=webapp&aid=6383&channel=channel_pc_web&item_id=7650106006073502949&update_version_code=170400&pc_client_type=1`);
    return await r.json();
  });
  
  const knowledge = (mentionResp.knowledge_list || []).map(k => k.content || '');
  console.log(`知识点: ${knowledge.length}个`);
  
  // ===== 步骤5: 构建完整上下文提示词 =====
  console.log('\n=== 5. 构建上下文 ===');
  
  const userPrompt = `把视频完全文案发给我，接着根据文案和视频内容整合出文案+资料+背景+视频中出现的错误或偏见或者在其他条件情况会有不同结果的内容一并整理出来，然后再单独另外整合的该内容下的所有评价然后分析整体视频和评价的矛盾点在哪，还有需求点在哪，可挖掘的市场或者可着重表现的点在哪等。如果画面中有重要图片请提取图片中的文案下来，画面中出现的文案也要全部提取下来。`;

  const fullPrompt = `【视频信息】
标题: ${videoContext.title}
作者: ${videoContext.author}
时长: ${videoContext.duration}
发布日期: ${videoContext.createTime}
标签: ${videoContext.tags}
数据: ${videoContext.statistics.digg}点赞 ${videoContext.statistics.comment}评论 ${videoContext.statistics.share}分享

【AI对视频的预分析关键词】
${questions.join('\n')}

【视频提及的知识点】
${knowledge.join('\n')}

---

基于以上视频信息，请执行以下任务：

${userPrompt}`;

  console.log(`上下文长度: ${fullPrompt.length} 字符`);
  
  // ===== 步骤6: 导航到AI页面并发送 =====
  console.log('\n=== 6. 发送到AI ===');
  
  const aiUrl = `https://so-landing.douyin.com/search_ai_mobile/pc?aid=6383&device_id=${deviceId}&ai_search_req_patch=${encodeURIComponent(JSON.stringify({ai_search_enter_from_group_id: VIDEO_ID}))}&enter_from=video_detail`;
  
  await page.goto(aiUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(10000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v6_01_ai.png') });
  
  // 深度思考
  const deepEls = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent?.trim() === '深度思考' && el.children.length === 0)
      .map(el => ({ x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y) }));
  });
  
  if (deepEls.length > 0) {
    await page.mouse.click(deepEls[0].x + 5, deepEls[0].y + 5);
    console.log('✅ 深度思考');
    await sleep(2000);
  } else {
    console.log('⚠️ 深度思考按钮未找到');
  }
  
  // 输入
  const inp = page.locator('[contenteditable="true"]').first();
  await inp.click();
  await sleep(500);
  await inp.fill(fullPrompt);
  console.log('✅ 已输入');
  await sleep(1000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v6_02_prompt.png') });
  
  // 发送
  console.log('发送...');
  await page.keyboard.press('Enter');
  await sleep(3000);
  
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v6_03_sent.png') });
  
  // ===== 等待回复 =====
  console.log('\n=== 等待回复（120秒）===');
  
  let lastText = '';
  for (let i = 0; i < 120; i++) {
    await sleep(1000);
    
    const cur = await page.evaluate(() => {
      let best = '';
      document.querySelectorAll('div, section').forEach(el => {
        const t = el.innerText?.trim() || '';
        if (t.length > best.length && t.length < 100000) best = t;
      });
      return best;
    });
    
    if (i % 10 === 0) console.log(`  [${i}s] ${cur.length} 字符`);
    
    if (cur.length > 500 && cur === lastText && i > 15) {
      console.log(`✅ 稳定: ${cur.length} 字符`);
      break;
    }
    lastText = cur;
  }
  
  await sleep(3000);
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'v6_04_done.png') });
  
  // 提取
  console.log('\n=== 提取 ===');
  const reply = await page.evaluate(() => {
    let best = '';
    document.querySelectorAll('div, section').forEach(el => {
      const t = el.innerText?.trim() || '';
      if (t.length > best.length && t.length < 100000) best = t;
    });
    return best;
  });
  
  console.log(`长度: ${reply.length} 字符`);
  
  const outPath = path.join(OUTPUT_DIR, 'v6_ai_reply.md');
  fs.writeFileSync(outPath, `# AI 回复 (${reply.length} 字符)\n\n${reply}`);
  console.log(`✅ 保存: ${outPath}`);
  
  console.log('\n=== 内容 ===');
  console.log(reply);
  
  console.log('\n浏览器保持打开 60 秒...');
  await sleep(60000);
  await context.close();
})();
