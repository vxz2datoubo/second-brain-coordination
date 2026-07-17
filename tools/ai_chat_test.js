/**
 * Douyin v8 - 获取 aweme_detail + 尝试 AI 对话 API
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const VIDEO_ID = '7650106006073502949';
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUTPUT_DIR = 'F:/ai/tools/screenshots';

(async () => {
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: true,
    viewport: { width: 1920, height: 1080 },
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });

  const page = await context.newPage();
  
  // 获取 cookie
  await page.goto(`https://www.douyin.com/video/${VIDEO_ID}`, { 
    waitUntil: 'domcontentloaded', timeout: 30000 
  });
  await page.waitForTimeout(3000);
  
  const cookies = await context.cookies();
  const cookieStr = cookies.map(c => `${c.name}=${c.value}`).join('; ');
  
  // ===== 1. 获取 aweme_detail (完整版不截断) =====
  console.log('=== 1. aweme_detail ===');
  try {
    const resp = await page.evaluate(async () => {
      const r = await fetch(`https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=${document.querySelector('meta[name="video_id"]')?.content || '7650106006073502949'}&aid=6383`, {
        headers: { 'User-Agent': navigator.userAgent, 'Referer': 'https://www.douyin.com/' }
      });
      return await r.text();
    });
    fs.writeFileSync(path.join(OUTPUT_DIR, 'aweme_detail_full.json'), resp);
    console.log(`长度: ${resp.length}`);
    
    try {
      const data = JSON.parse(resp);
      const aweme = data.aweme_detail || data.aweme || data;
      
      // 提取关键信息
      const info = {
        desc: aweme.desc || '',
        create_time: aweme.create_time,
        duration: aweme.video?.duration,
        // 字幕
        subtitle: aweme.interaction_stickers || aweme.subtitles || aweme.video_text,
        // 章节
        chapters: aweme.video_tag || aweme.chapter_list,
      };
      
      console.log('标题:', info.desc?.substring(0, 200));
      console.log('时长:', info.duration, 'ms');
      
      // 检查是否有字幕数据
      if (aweme.subtitle_info) {
        console.log('字幕信息:', JSON.stringify(aweme.subtitle_info).substring(0, 500));
      }
      
      // 搜索字幕相关字段
      const keys = Object.keys(aweme);
      const subtitleKeys = keys.filter(k => k.toLowerCase().includes('subtitle') || k.toLowerCase().includes('caption') || k.toLowerCase().includes('text') || k.toLowerCase().includes('sticker'));
      console.log('字幕相关字段:', subtitleKeys);
      
      if (subtitleKeys.length > 0) {
        for (const k of subtitleKeys) {
          const v = aweme[k];
          if (v && typeof v === 'object') {
            console.log(`  ${k}:`, JSON.stringify(v).substring(0, 300));
          } else if (v) {
            console.log(`  ${k}:`, String(v).substring(0, 300));
          }
        }
      }
      
      // 互动贴纸（可能包含字幕）
      if (aweme.interaction_stickers) {
        console.log('互动贴纸:', JSON.stringify(aweme.interaction_stickers).substring(0, 500));
      }
      
      // 保存提取的信息
      fs.writeFileSync(path.join(OUTPUT_DIR, 'video_info.json'), JSON.stringify(info, null, 2));
    } catch(e) {
      console.log('解析失败:', e.message?.substring(0, 100));
    }
  } catch(e) {
    console.log('aweme_detail 失败:', e.message?.substring(0, 100));
  }
  
  // ===== 2. 尝试 AI 对话 =====
  console.log('\n=== 2. AI 对话测试 ===');
  
  // 常见 AI 接口模式
  const chatAPIs = [
    {
      name: 'douyin_ai_chat',
      url: 'https://www.douyin.com/douyin/select/v1/ai/chat/',
      method: 'POST',
      body: { 
        question: '视频总结', 
        context: JSON.stringify({ intent: 'summary' }),
        from_group_id: VIDEO_ID,
        item_id: VIDEO_ID
      }
    },
    {
      name: 'so_landing_chat',
      url: 'https://so-landing.douyin.com/douyin/select/v1/ai/chat/',
      method: 'POST',
      body: {
        question: '视频总结',
        context: JSON.stringify({ intent: 'summary' }),
        from_group_id: VIDEO_ID,
        item_id: VIDEO_ID,
        aid: '6383'
      }
    },
    {
      name: 'ai_assistant_chat',
      url: `https://www.douyin.com/douyin/select/study/ai_assistant/watch/chat?device_platform=webapp&aid=6383&item_id=${VIDEO_ID}`,
      method: 'POST',
      body: {
        question: '视频总结',
        context: '{"intent":"summary"}',
        from_group_id: VIDEO_ID
      }
    },
    {
      name: 'ai_stream',
      url: `https://so-landing.douyin.com/douyin/select/v1/ai/stream?aid=6383&from_group_id=${VIDEO_ID}`,
      method: 'POST',
      body: {
        prompt: '请总结这个视频的内容',
        context: '{"intent":"summary"}'
      }
    }
  ];
  
  for (const api of chatAPIs) {
    try {
      const opts = {
        method: api.method,
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
          'Cookie': cookieStr,
          'Referer': `https://www.douyin.com/video/${VIDEO_ID}`
        }
      };
      if (api.body) opts.body = JSON.stringify(api.body);
      
      const result = await page.evaluate(async ({url, opts}) => {
        try {
          const r = await fetch(url, opts);
          const text = await r.text();
          return { status: r.status, len: text.length, preview: text.substring(0, 500) };
        } catch(e) {
          return { error: e.message };
        }
      }, {url: api.url, opts});
      
      console.log(`[${api.name}] status=${result.status} len=${result.len}`);
      if (result.preview) {
        console.log(`  preview: ${result.preview.substring(0, 200)}`);
      }
      if (result.error) {
        console.log(`  error: ${result.error}`);
      }
    } catch(e) {
      console.log(`[${api.name}] 异常: ${e.message?.substring(0, 80)}`);
    }
  }
  
  console.log('\n完成！');
  await context.close();
})();
