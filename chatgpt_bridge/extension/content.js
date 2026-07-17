// ChatGPT 第二大脑桥 - Content Script
// 在 ChatGPT 页面运行，直接操作 DOM 发送 prompt / 捕获回答

const BRIDGE = "http://localhost:8799";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let justSubmitted = false;
let executingTaskId = null;

// ---------- 工具函数 ----------
function log(...args) {
  console.log("[第二大脑桥-content]", ...args);
}

function findComposer() {
  // 新版 ChatGPT 是 contenteditable div
  const div = document.querySelector(
    'div[contenteditable="true"][role="textbox"], #prompt-textarea, [data-testid="messaging-input-text-area"]'
  );
  if (div) return { el: div, type: "contenteditable" };
  // 旧版 textarea
  const ta = document.querySelector("#prompt-textarea");
  if (ta) return { el: ta, type: "textarea" };
  return null;
}

function findSendButton() {
  return (
    document.querySelector('button[data-testid="send-button"]') ||
    document.querySelector('button[aria-label="Send prompt"]') ||
    document.querySelector('button[aria-label="发送消息"]') ||
    Array.from(document.querySelectorAll("button")).find((b) => {
      const txt = b.innerText || "";
      return txt.includes("→") || b.querySelector("svg");
    })
  );
}

function setTextContent(el, text, type) {
  if (type === "textarea") {
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype,
      "value"
    ).set;
    setter.call(el, text);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  } else {
    el.focus();
    el.innerHTML = "";
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(el);
    selection.removeAllRanges();
    selection.addRange(range);
    document.execCommand("insertText", false, text);
    // 触发 React 受控更新
    el.dispatchEvent(new InputEvent("input", { bubbles: true, data: text }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }
}

function clickSend(btn) {
  if (btn) {
    btn.click();
    return true;
  }
  // 兜底：模拟 Enter
  const composer = findComposer();
  if (composer) {
    composer.el.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "Enter",
        code: "Enter",
        bubbles: true,
        cancelable: true,
      })
    );
  }
  return false;
}

async function waitAnswer(timeoutSec = 120) {
  let last = "";
  let stable = 0;
  for (let i = 0; i < timeoutSec * 2; i++) {
    const msgs = document.querySelectorAll(
      '[data-message-author-role="assistant"]'
    );
    const el = msgs[msgs.length - 1];
    const txt = el ? el.innerText.trim() : "";

    const stopBtn =
      document.querySelector('button[data-testid="stop-button"]') ||
      document.querySelector('button[aria-label="Stop generating"]') ||
      document.querySelector('button[aria-label="停止生成"]');

    if (stopBtn) {
      last = txt;
      await sleep(500);
      continue;
    }
    if (txt && txt === last) {
      stable++;
      if (stable >= 2) return txt;
    } else {
      stable = 0;
      last = txt;
    }
    await sleep(500);
  }
  return last;
}

// ---------- 出站：执行桥下发的任务 ----------
async function executeTask(task) {
  if (executingTaskId) return;
  executingTaskId = task.task_id;
  justSubmitted = true;
  log("收到任务", task.task_id, "text:", task.text.substring(0, 40) + "...");

  try {
    const composer = findComposer();
    if (!composer) {
      throw new Error("未找到 ChatGPT 输入框");
    }
    setTextContent(composer.el, task.text, composer.type);
    await sleep(300);
    const btn = findSendButton();
    clickSend(btn);
    log("已发送 prompt");

    const answer = await waitAnswer(120);
    log("捕获回答", answer.substring(0, 60) + "...");

    chrome.runtime.sendMessage({
      action: "complete",
      task_id: task.task_id,
      text: answer,
      title: "ChatGPT回答",
    });
  } catch (err) {
    log("任务执行失败", err.message);
    chrome.runtime.sendMessage({
      action: "complete",
      task_id: task.task_id,
      text: "[桥接错误] " + err.message,
      title: "ChatGPT回答(错误)",
    });
  } finally {
    executingTaskId = null;
  }
}

// ---------- 入站：捕获手动对话 ----------
function observeManualChat() {
  const seen = new Set();
  const main = document.querySelector("main") || document.body;
  const obs = new MutationObserver(() => {
    const msgs = document.querySelectorAll(
      '[data-message-author-role="assistant"]'
    );
    for (const el of msgs) {
      if (seen.has(el)) continue;
      seen.add(el);
      setTimeout(() => {
        if (justSubmitted) {
          justSubmitted = false;
          return;
        }
        const txt = el.innerText.trim();
        if (txt) {
          log("手动回答入站", txt.substring(0, 40) + "...");
          chrome.runtime.sendMessage({
            action: "ingest",
            text: txt,
            title: "ChatGPT手动对话",
          });
        }
      }, 2500);
    }
  });
  obs.observe(main, { childList: true, subtree: true });
}

// ---------- 监听 background 发来的任务 ----------
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.action === "execute_task" && msg.task) {
    executeTask(msg.task);
  }
});

// ---------- 初始化 ----------
(function init() {
  log("content script 已加载");
  observeManualChat();
})();
