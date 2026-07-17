/**
 * Douyin v7 - 直接调用问AI API接口
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const VIDEO_ID = '7650106006073502949';
const PROFILE_DIR = 'C:/WorkBuddy/PlaywrightProfile';
const OUTPUT_DIR = 'F:/ai/tools/screenshots';

if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR, { recursive: true });

(async () => {
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: true,
    viewport: { width: 1920, height: 1080 },
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });

  const page = await context.newPage();
  
  // 先导航到视频页面以获取 cookie/session
  console.log('=== 导航到视频页 ===');
  await page.goto(`https://www.douyin.com/video/${VIDEO_ID}`, { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(5000);
  
  // 收集所有 AI 相关 API 响应
  console.log('\n=== 调用 AI 相关 API ===');
  
  const apiCalls = [
    {
      name: 'ai_history_preview',
      url: `https://so-landing.douyin.com/douyin/select/v1/ai/history_preview/?aid=6383&device_id=7651518205098608143&from_group_id=${VIDEO_ID}&history_preview_type=from_group&conversation_ts=${Date.now()}`
    },
    {
      name: 'ai_history',
      url: `https://so-landing.douyin.com/douyin/select/v1/ai/history/?device_id=7651518205098608143&aid=6383&need_integration_card=1&version_code=32.1.0&ai_search_history_support_parallel_conversation=false&enter_from=video_detail&from_group_id=${VIDEO_ID}`
    },
    {
      name: 'ai_suggestions',
      url: `https://www.douyin.com/douyin/select/study/ai_assistant/watch/sug/get?device_platform=webapp&aid=6383&channel=channel_pc_web&item_id=${VIDEO_ID}&update_version_code=170400&pc_client_type=1`
    },
    {
      name: 'ai_current_mention',
      url: `https://www.douyin.com/douyin/select/study/ai_assistant/watch/current_mention/get?device_platform=webapp&aid=6383&channel=channel_pc_web&item_id=${VIDEO_ID}&update_version_code=170400&pc_client_type=1`
    },
    {
      name: 'aweme_detail',
      url: `https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=${VIDEO_ID}&aid=6383&device_platform=webapp&channel=channel_pc_web`
    },
    {
      name: 'search_ai_page',
      url: `https://so-landing.douyin.com/search_ai_mobile/pc?aid=6383&device_id=7651518205098608143&user_id=100804183530&ai_search_req_patch=${encodeURIComponent(JSON.stringify({ai_search_enter_from_group_id: VIDEO_ID}))}&enter_from=video_detail`
    }
  ];
  
  const results = {};
  for (const api of apiCalls) {
    try {
      const resp = await page.evaluate(async ({url, name}) => {
        try {
          const r = await fetch(url, {
            headers: {
              'User-Agent': navigator.userAgent,
              'Accept': 'application/json',
              'Referer': 'https://www.douyin.com/'
            },
            credentials: 'include'
          });
          const text = await r.text();
          return { 
            api: name, 
            status: r.status, 
            len: text.length,
            data: text.substring(0, 5000),
            isJSON: text.startsWith('{') || text.startsWith('[')
          };
        } catch(e) {
          return { api: name, error: e.message };
        }
      }, {url: api.url, name: api.name});
      
      results[api.name] = resp;
      console.log(`[${api.name}] status=${resp.status} len=${resp.len} isJSON=${resp.isJSON}`);
      
      if (resp.isJSON && resp.len > 50) {
        try {
          const parsed = JSON.parse(resp.data);
          console.log(`   keys: ${Object.keys(parsed).join(', ')}`);
          // 提取关键信息
          if (parsed.data) {
            const dataKeys = typeof parsed.data === 'object' ? Object.keys(parsed.data).join(', ') : 'not-object';
            console.log(`   data keys: ${dataKeys}`);
          }
          
          // 保存完整响应
          const filePath = path.join(OUTPUT_DIR, `${api.name}.json`);
          fs.writeFileSync(filePath, JSON.stringify(parsed, null, 2));
          console.log(`   已保存: ${filePath}`);
        } catch(e) {
          console.log(`   JSON解析失败: ${e.message?.substring(0, 60)}`);
          // 保存原始文本
          const filePath = path.join(OUTPUT_DIR, `${api.name}.txt`);
          fs.writeFileSync(filePath, resp.data);
        }
      }
      
      if (resp.len > 50 && !resp.isJSON) {
        const filePath = path.join(OUTPUT_DIR, `${api.name}.html`);
        fs.writeFileSync(filePath, resp.data);
        console.log(`   已保存HTML: ${filePath}`);
      }
    } catch(e) {
      console.log(`[${api.name}] 请求失败: ${e.message?.substring(0, 80)}`);
    }
  }
  
  // 总结
  console.log('\n=== 总结 ===');
  for (const [name, r] of Object.entries(results)) {
    console.log(`  ${name}: status=${r.status} len=${r.len}`);
  }
  
  console.log('\n完成！浏览器保持打开 30 秒...');
  await page.waitForTimeout(30000);
  await context.close();
})();
