/**
 * Douyin AI v9 — 绕过 AI 搜索页，直接用 API 数据 + 自建分析
 * 因为 search_ai_mobile 页面的 AI 无法获取视频上下文
 * 使用 QClaw 进行完整消化分析
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const http = require('http');

const VIDEO_ID = '7650409830854790415';
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUTPUT_DIR = 'F:/ai/tools/screenshots';

const sleep = ms => new Promise(r => setTimeout(r, ms));

const ANALYSIS_PROMPT = `把视频完全文案发给我，接着根据文案和视频内容整合出文案+资料+背景+视频中出现的错误或偏见或者在其他条件情况会有不同结果的内容一并整理出来，然后再单独另外整合的该内容下的所有评价然后分析整体视频和评价的矛盾点在哪，还有需求点在哪，可挖掘的市场或者可着重表现的点在哪等。如果画面中有重要图片请提取图片中的文案下来，画面中出现的文案也要全部提取下来。`;

(async () => {
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: true,
    viewport: { width: 1920, height: 1080 },
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });

  const page = await context.newPage();

  // ===== 1. 访问视频页获取 cookies =====
  console.log('=== 1. 访问视频页 ===');
  await page.goto(`https://www.douyin.com/video/${VIDEO_ID}`, {
    waitUntil: 'domcontentloaded', timeout: 30000
  });
  await sleep(5000);

  // ===== 2. 获取所有视频相关数据 =====
  console.log('\n=== 2. 获取视频数据 ===');

  // API: aweme_detail
  const awemeResp = await page.evaluate(async (vid) => {
    const r = await fetch(`https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=${vid}&aid=6383`);
    return await r.json();
  }, VIDEO_ID);
  const aweme = awemeResp.aweme_detail;
  
  // API: AI suggestions
  const sugResp = await page.evaluate(async (vid) => {
    const r = await fetch(`https://www.douyin.com/douyin/select/study/ai_assistant/watch/sug/get?device_platform=webapp&aid=6383&channel=channel_pc_web&item_id=${vid}&update_version_code=170400&pc_client_type=1`);
    return await r.json();
  }, VIDEO_ID);

  // API: AI mentions
  const mentionResp = await page.evaluate(async (vid) => {
    const r = await fetch(`https://www.douyin.com/douyin/select/study/ai_assistant/watch/current_mention/get?device_platform=webapp&aid=6383&channel=channel_pc_web&item_id=${vid}&update_version_code=170400&pc_client_type=1`);
    return await r.json();
  }, VIDEO_ID);

  // 提取结构化数据
  const videoData = {
    title: aweme.desc || '',
    author: aweme.author?.nickname || '',
    author_uid: aweme.author?.uid || '',
    duration: `${Math.round((aweme.video?.duration || 0) / 1000)}秒`,
    create_time: new Date((aweme.create_time || 0) * 1000).toLocaleString('zh-CN'),
    music_title: aweme.music?.title || '',
    music_author: aweme.music?.author || '',
    tags: (aweme.text_extra || []).filter(t => t.hashtag_name).map(t => `#${t.hashtag_name}`),
    statistics: {
      digg: aweme.statistics?.digg_count || 0,
      comment: aweme.statistics?.comment_count || 0,
      share: aweme.statistics?.share_count || 0,
      collect: aweme.statistics?.collect_count || 0,
      play: aweme.statistics?.play_count || 0,
    },
    ai_suggestions: (sugResp.question_list || []).map(q => ({
      question: q.content || q.question || '',
      type: q.type || '',
      context: q.context || '',
      sub_type: q.sub_type || '',
      start_time: q.start_time || 0
    })),
    ai_knowledge: (mentionResp.knowledge_list || []).map(k => ({
      content: k.content || '',
      start: k.start_time || 0,
      end: k.end_time || 0,
      title: k.title || ''
    })),
    original_music: aweme.music?.original || false,
    is_ads: aweme.is_ads || false,
    is_top: aweme.is_top || 0,
    comment_list: [], // 评论区需要额外API
  };

  console.log(`标题: ${videoData.title}`);
  console.log(`作者: ${videoData.author}`);
  console.log(`时长: ${videoData.duration}`);
  console.log(`数据: ${videoData.statistics.play}播放 ${videoData.statistics.digg}赞 ${videoData.statistics.comment}评`);
  console.log(`AI建议: ${videoData.ai_suggestions.length}条`);
  console.log(`知识点: ${videoData.ai_knowledge.length}条`);

  // 保存完整数据
  fs.writeFileSync(path.join(OUTPUT_DIR, `v9_video_data_${VIDEO_ID}.json`), JSON.stringify(videoData, null, 2));

  // ===== 3. 构建分析上下文 =====
  console.log('\n=== 3. 构建分析上下文 ===');

  const contextText = `
## 视频基本信息
- 标题: ${videoData.title}
- 作者: ${videoData.author} (UID: ${videoData.author_uid})
- 时长: ${videoData.duration}
- 发布时间: ${videoData.create_time}
- BGM: ${videoData.music_title} by ${videoData.music_author}
- 标签: ${videoData.tags.join(' ')}

## 视频数据
- 播放量: ${videoData.statistics.play}
- 点赞: ${videoData.statistics.digg}
- 评论: ${videoData.statistics.comment}
- 分享: ${videoData.statistics.share}
- 收藏: ${videoData.statistics.collect}

## AI 预分析建议（抖音AI生成的问题）
${videoData.ai_suggestions.map((q,i) => `${i+1}. [${q.sub_type || '通用'}] ${q.question} (视频时间: ${q.start_time || 0}s)`).join('\n')}

## AI 提取的知识点
${videoData.ai_knowledge.map((k,i) => `${i+1}. ${k.content} (${k.start}s-${k.end}s${k.title ? ', 标题:' + k.title : ''})`).join('\n')}
`;

  // ===== 4. 发送到 QClaw 进行分析 =====
  console.log('\n=== 4. 使用 QClaw 进行深度分析 ===');

  const qclawCfgPath = require('os').homedir() + '/.qclaw/qclaw.json';
  let qclawPort = 8234;
  try {
    if (fs.existsSync(qclawCfgPath)) {
      const cfg = JSON.parse(fs.readFileSync(qclawCfgPath, 'utf8'));
      qclawPort = cfg.port || 8234;
    }
  } catch(e) {}

  const fullPrompt = `${contextText}

---

${ANALYSIS_PROMPT}`;

  // 先保存分析请求
  const analysisFile = path.join(OUTPUT_DIR, `v9_analysis_${VIDEO_ID}.md`);
  
  // 尝试 QClaw
  let analysisResult = '';
  let usedQclaw = false;
  
  try {
    const qclawBody = JSON.stringify({
      model: 'default',
      messages: [
        { role: 'system', content: '你是一个专业的视频内容分析师。请基于提供的视频信息，生成全面、详细的分析报告。' },
        { role: 'user', content: fullPrompt }
      ],
      temperature: 0.7,
      max_tokens: 16000
    });

    const qclawReq = http.request({
      hostname: '127.0.0.1', port: qclawPort,
      path: '/v1/chat/completions', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(qclawBody) },
      timeout: 120000
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const resp = JSON.parse(data);
          analysisResult = resp.choices?.[0]?.message?.content || '';
          if (analysisResult) {
            console.log(`QClaw 分析完成: ${analysisResult.length} 字`);
            usedQclaw = true;
            
            // 保存分析
            const qcOut = `# 视频分析报告\n\n## 视频信息\n${contextText}\n\n---\n\n## 深度分析\n\n${analysisResult}`;
            fs.writeFileSync(analysisFile, qcOut);
            console.log(`✅ 已保存: ${analysisFile}`);
            
            // 录入第二大脑
            const digestData = JSON.stringify({
              text: qcOut,
              source: `douyin-video-${VIDEO_ID}`,
              source_type: 'douyin_deep_analysis',
              tags: ['抖音AI分析', '视频文案', '市场洞察', 'QClaw分析']
            });
            const digestReq = http.request({
              hostname: 'localhost', port: 8766,
              path: '/api/digest/text', method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(digestData) }
            }, (dr) => { dr.resume(); });
            digestReq.on('error', () => console.log('⚠️ 第二大脑未运行'));
            digestReq.write(digestData);
            digestReq.end();
          }
        } catch(e) {
          console.log('QClaw 响应解析失败:', e.message);
        }
      });
    });
    qclawReq.on('error', (e) => console.log('QClaw 不可用:', e.message));
    qclawReq.write(qclawBody);
    qclawReq.end();
    
    // 等待 QClaw 响应
    await sleep(90000);
  } catch(e) {
    console.log('QClaw 异常:', e.message);
  }

  // ===== 5. 如果 QClaw 不可用，使用 Playwright 中的 AI 页面 =====
  if (!analysisResult) {
    console.log('\n=== 5. 回退: 使用 AI 搜索页面 ===');
    
    const deviceId = '7651518205098608143';
    const aiUrl = `https://so-landing.douyin.com/search_ai_mobile/pc?aid=6383&device_id=${deviceId}&ai_search_req_patch=${encodeURIComponent(JSON.stringify({ai_search_enter_from_group_id: VIDEO_ID}))}`;
    
    await page.goto(aiUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await sleep(15000);
    
    // 直接输入完整上下文
    const inp = page.locator('[contenteditable="true"]').first();
    await inp.click();
    await sleep(500);
    await inp.fill(contextText + '\n\n' + ANALYSIS_PROMPT);
    await sleep(1000);
    await page.keyboard.press('Enter');
    
    console.log('等待回复...');
    let last = '';
    for (let i = 0; i < 90; i++) {
      await sleep(1000);
      const cur = await page.evaluate(() => {
        let best = '';
        document.querySelectorAll('div, section').forEach(el => {
          const t = el.innerText?.trim() || '';
          if (t.length > best.length && t.length < 200000) best = t;
        });
        return best;
      });
      if (cur.length > 500 && cur === last && i > 15) {
        analysisResult = cur;
        break;
      }
      last = cur;
    }
    
    if (analysisResult) {
      fs.writeFileSync(analysisFile, `# 视频分析\n\n${analysisResult}`);
      console.log(`✅ AI 分析完成: ${analysisResult.length} 字`);
    }
  }

  // 最终结果
  if (fs.existsSync(analysisFile)) {
    const content = fs.readFileSync(analysisFile, 'utf8');
    console.log(`\n分析报告: ${analysisFile}`);
    console.log(`长度: ${content.length} 字`);
    
    // 预览
    console.log('\n=== 前 1000 字 ===');
    console.log(content.substring(0, 1000));
  }

  await context.close();
})();
