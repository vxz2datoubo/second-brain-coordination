// Chrome Extension Background Service Worker
// 负责：与本地桥 (localhost:8799) 通信，并在 content script 与桥之间转发任务
const BRIDGE = "http://localhost:8799";

function api(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  return fetch(BRIDGE + path, opts).then((r) => r.json()).catch((err) => ({
    error: err.message,
  }));
}

// 每隔 1.5 秒向桥取任务，取到后发到当前 ChatGPT 标签页的 content script
async function pollAndForward() {
  const res = await api("GET", "/pending");
  if (res && res.task_id) {
    const tabs = await chrome.tabs.query({
      url: ["https://chatgpt.com/*", "https://chat.openai.com/*"],
    });
    if (tabs.length === 0) return;
    // 发给所有 ChatGPT 标签页，第一个响应的 content script 执行
    for (const tab of tabs) {
      try {
        chrome.tabs.sendMessage(tab.id, { action: "execute_task", task: res });
      } catch (e) {
        console.log("[bg] send to tab failed", e);
      }
    }
  }
}

setInterval(pollAndForward, 1500);

// content script 把回答/错误传回来后，提交到桥
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "complete") {
    api("POST", "/complete", {
      task_id: msg.task_id,
      text: msg.text,
      title: msg.title,
    }).then((res) => sendResponse(res));
    return true;
  }
  if (msg.action === "ingest") {
    api("POST", "/ingest", {
      text: msg.text,
      title: msg.title,
    }).then((res) => sendResponse(res));
    return true;
  }
});

console.log("[ChatGPT桥] background service worker 已启动");
