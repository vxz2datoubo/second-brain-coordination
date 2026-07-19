/**
 * 提取视频数据 → QClaw 深度分析 → 消化入库
 */
const { chromium } = require('playwright');
const fs = require('fs');
const http = require('http');
const path = require('path');

const VIDEO_ID = '7650409830854790415';
const VIDEO_URL = `https://www.douyin.com/jingxuan?modal_id=${VIDEO_ID}`;
const QCLAW_PORT = 3715;
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUT = 'F:/ai/tools/screenshots';

const ANALYSIS_CMD = `${VIDEO_URL}。把视频完全文案发给我，接着根据文案和视频内容整合出文案+资料+背景+视频中出现的错误或偏见或者在其他条件情况会有不同结果的内容一并整理出来，然后再单独另外整合的该内容下的所有评价然后分析整体视频和评价的矛盾点在哪，还有需求点在哪，可挖掘的市场或者可着重表现的点在哪等。如果画面中有重要图片请提取图片中的文案下来，画面中出现的文案也要全部提取下来。`;

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  // ===== Step 1: 提取视频数据 =====
  console.log('Step 1: 提取视频数据...');
  const ctx = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: true, viewport: { width: 1920, height: 1080 }, args: ['--no-sandbox']
  });
  const page = await ctx.newPage();
  await page.goto(`https://www.douyin.com/video/${VIDEO_ID}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await sleep(5000);

  const [aweme, sug, mention] = await Promise.all([
    page.evaluate(vid => fetch(`https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=${vid}&aid=6383`).then(r=>r.json()), VIDEO_ID),
    page.evaluate(vid => fetch(`https://www.douyin.com/douyin/select/study/ai_assistant/watch/sug/get?device_platform=webapp&aid=6383&item_id=${vid}&update_version_code=170400&pc_client_type=1`).then(r=>r.json()), VIDEO_ID),
    page.evaluate(vid => fetch(`https://www.douyin.com/douyin/select/study/ai_assistant/watch/current_mention/get?device_platform=webapp&aid=6383&item_id=${vid}&update_version_code=170400&pc_client_type=1`).then(r=>r.json()), VIDEO_ID)
  ]);
  await ctx.close();

  const a = aweme.aweme_detail;
  const context = `
## 视频链接
${VIDEO_URL}

## 视频基本信息
- 标题: ${a.desc || ''}
- 作者: ${a.author?.nickname || ''}
- 时长: ${Math.round((a.video?.duration||0)/1000)}秒
- 发布时间: ${new Date((a.create_time||0)*1000).toLocaleString('zh-CN')}
- 标签: ${(a.text_extra||[]).filter(t=>t.hashtag_name).map(t=>'#'+t.hashtag_name).join(' ')}
- 播放: ${a.statistics?.play_count||0} | 点赞: ${a.statistics?.digg_count||0} | 评论: ${a.statistics?.comment_count||0} | 分享: ${a.statistics?.share_count||0}

## 抖音AI预分析问题
${(sug.question_list||[]).map((q,i)=>`${i+1}. [${q.sub_type||''}] ${q.content||q.question||''}`).join('\n')}

## 抖音AI提取知识点
${(mention.knowledge_list||[]).map((k,i)=>`${i+1}. ${k.content||''} (${k.start_time||0}s-${k.end_time||0}s)`).join('\n')}
`;

  console.log(`视频: ${a.desc}`);
  console.log(`播放: ${a.statistics?.play_count||0} 赞: ${a.statistics?.digg_count||0}`);
  console.log(`预分析问题: ${(sug.question_list||[]).length}条`);
  console.log(`知识点: ${(mention.knowledge_list||[]).length}条`);

  // ===== Step 2: 发送到 QClaw =====
  console.log('\nStep 2: 发送 QClaw 分析...');
  const body = JSON.stringify({
    model: 'default',
    messages: [
      { role: 'system', content: '你是专业视频分析师。基于提供的视频数据和AI预分析，生成全面深度分析报告。要求：1)整理完整文案 2)补充资料和背景 3)指出错误/偏见/不同条件下的差异 4)分析评论矛盾点、需求点、市场机会 5)提取画面文字。输出详实，结构清晰。' },
      { role: 'user', content: context + '\n\n' + ANALYSIS_CMD }
    ],
    temperature: 0.7, max_tokens: 16000
  });

  let analysis = '';
  const startTime = Date.now();

  const req = http.request({
    hostname: '127.0.0.1', port: QCLAW_PORT,
    path: '/v1/chat/completions', method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
    timeout: 180000
  }, res => {
    let data = '';
    res.on('data', c => { data += c; process.stdout.write('.'); });
    res.on('end', () => {
      try {
        analysis = JSON.parse(data).choices?.[0]?.message?.content || '';
        console.log(`\n完成! ${analysis.length}字, 耗时${Math.round((Date.now()-startTime)/1000)}s`);

        // Step 3: 保存
        const outFile = `${OUT}/analysis_${VIDEO_ID}.md`;
        fs.writeFileSync(outFile, `# 视频深度分析\n\n## 视频数据\n${context}\n\n---\n\n## 完整分析\n\n${analysis}`);
        console.log(`\nStep 3: 已保存 ${outFile}`);

        // Step 4: 消化录入第二大脑
        console.log('\nStep 4: 录入第二大脑...');
        const brainBody = JSON.stringify({
          text: analysis,
          source: `douyin-video-${VIDEO_ID}`,
          source_type: 'douyin_deep_analysis',
          tags: ['抖音深度分析', '视频文案', '市场洞察', 'QClaw']
        });
        const br = http.request({
          hostname: 'localhost', port: 8766,
          path: '/api/digest/text', method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(brainBody) }
        }, r => {
          let d = '';
          r.on('data', c => d += c);
          r.on('end', () => console.log('入库:', d.substring(0, 120)));
        });
        br.on('error', () => console.log('⚠️ 第二大脑未运行'));
        br.write(brainBody);
        br.end();

        // 预览
        console.log('\n=== 分析报告前 1000 字 ===');
        console.log(analysis.substring(0, 1000));
        console.log('...');
      } catch(e) {
        console.log('解析失败:', e.message);
        if (data) fs.writeFileSync(`${OUT}/qclaw_raw_${VIDEO_ID}.json`, data);
      }
    });
  });
  req.on('error', e => console.log('QClaw连接失败:', e.message));
  req.write(body);
  req.end();

  // 等待 QClaw 响应（最多120秒）
  for (let i = 0; i < 120 && !analysis; i++) await sleep(1000);
  if (!analysis) console.log('⚠️ QClaw 超时');
})();
