// ==UserScript==
// @name         ChatGPT ↔ 第二大脑 桥接助手
// @namespace    http://aidanao.local
// @version      1.4
// @description  把 ChatGPT 回答回传本机桥(8799)，并自动执行桥下发的提示词。无 API Key，复用浏览器登录态。使用 unsafeWindow.Function 注入页面原生上下文，并通过 postMessage 回传结果，避免任务卡死。
// @match        https://chat.openai.com/*
// @match        https://chatgpt.com/*
// @grant        GM_xmlhttpRequest
// @grant        unsafeWindow
// @connect      localhost
// @connect      127.0.0.1
// ==/UserScript==

(function () {
  const BRIDGE = "http://localhost:8799";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  let justSubmitted = false;
  const seen = new Set();
  const messageWaiters = new Map(); // taskId -> {resolve, timer}

  function log(...args) {
    console.log("[第二大脑桥]", ...args);
  }

  function api(method, path, body, cb) {
    GM_xmlhttpRequest({
      method: method,
      url: BRIDGE + path,
      headers: { "Content-Type": "application/json" },
      data: body ? JSON.stringify(body) : undefined,
      onload: function (r) {
        try {
          cb(JSON.parse(r.responseText), r.status);
        } catch (e) {
          cb({}, r.status);
        }
      },
      onerror: function () {
        cb(null, 0);
      },
    });
  }

  // 等待页面脚本通过 postMessage 回传结果
  function waitForMessage(taskId, timeoutMs) {
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        messageWaiters.delete(taskId);
        resolve(null);
      }, timeoutMs);
      messageWaiters.set(taskId, (payload) => {
        clearTimeout(timer);
        messageWaiters.delete(taskId);
        resolve(payload);
      });
    });
  }

  // 用页面原生上下文监听 message（注入脚本会 postMessage 回来）
  const win = unsafeWindow;
  win.addEventListener("message", (e) => {
    const d = e.data;
    if (!d || d.source !== "chatgpt_bridge_page") return;
    const resolver = messageWaiters.get(d.taskId);
    if (resolver) resolver(d);
  });

  // ---------- 自动执行桥下发的提示词 ----------
  async function waitAnswer() {
    const d = win.document;
    let last = "";
    let stable = 0;
    let ticks = 0;
    while (ticks < 150) {
      const msgs = d.querySelectorAll('[data-message-author-role="assistant"]');
      const el = msgs[msgs.length - 1];
      const txt = el ? el.innerText.trim() : "";
      const stopBtn =
        d.querySelector('button[data-testid="stop-button"]') ||
        d.querySelector('button[aria-label="Stop generating"]');
      if (stopBtn) {
        last = txt;
        await sleep(1000);
        ticks++;
        continue;
      }
      if (txt && txt === last) {
        stable++;
        if (stable >= 2) return txt;
      } else {
        stable = 0;
        last = txt;
      }
      await sleep(1000);
      ticks++;
    }
    return last;
  }

  async function processTask(task) {
    log("收到任务，准备发 prompt:", task.task_id, "| 文本:", task.text);
    const taskId = task.task_id;

    // 注入脚本：在页面原生上下文执行，只负责把 prompt 发出去
    const pageCode = `
      (function() {
        try {
          const w = window;
          const d = w.document;
          const TEXT = ${JSON.stringify(task.text)};
          const TASK_ID = ${JSON.stringify(taskId)};

          function findComposer() {
            let el = d.querySelector('#prompt-textarea');
            if (el) return { el: el, kind: 'textarea' };
            el = d.querySelector('div[contenteditable="true"][role="textbox"]')
               || d.querySelector('div[contenteditable="true"]');
            if (el) return { el: el, kind: 'ce' };
            return null;
          }

          const c = findComposer();
          if (!c) {
            w.postMessage({ source: 'chatgpt_bridge_page', taskId: TASK_ID, ok: false, error: '未找到输入框' }, '*');
            return;
          }

          c.el.focus();
          if (c.kind === 'textarea') {
            const setter = Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype, 'value').set;
            setter.call(c.el, TEXT);
            const ev = new w.Event('input', { bubbles: true });
            c.el.dispatchEvent(ev);
          } else {
            c.el.textContent = '';
            c.el.innerHTML = '';
            const sel = w.getSelection();
            const range = d.createRange();
            range.selectNodeContents(c.el);
            sel.removeAllRanges();
            sel.addRange(range);
            d.execCommand('insertText', false, TEXT);
          }

          // 发送
          let sent = false;
          const btn = d.querySelector('button[data-testid="send-button"]')
                   || d.querySelector('button[aria-label="Send prompt"]')
                   || d.querySelector('button[aria-label="发送"]');
          if (btn) {
            w.HTMLButtonElement.prototype.click.call(btn);
            sent = true;
          } else {
            c.el.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
            c.el.dispatchEvent(new w.KeyboardEvent('keyup',   { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
            sent = true;
          }

          w.postMessage({ source: 'chatgpt_bridge_page', taskId: TASK_ID, ok: true, sent: sent }, '*');
        } catch (err) {
          window.postMessage({ source: 'chatgpt_bridge_page', taskId: ${JSON.stringify(taskId)}, ok: false, error: String(err && err.message || err) }, '*');
        }
      })();
    `;

    try {
      new win.Function(pageCode)();
    } catch (err) {
      log("注入代码编译失败:", err);
      api("POST", "/complete", { task_id: taskId, text: "[注入失败] " + String(err), title: "ChatGPT回答" }, () => {});
      return;
    }

    const sendResult = await waitForMessage(taskId, 8000);
    if (!sendResult) {
      log("页面脚本未在 8 秒内回传，可能注入未执行或页面上下文隔离失败");
      api("POST", "/complete", { task_id: taskId, text: "[页面脚本无响应] 注入代码可能未执行", title: "ChatGPT回答" }, () => {});
      return;
    }
    if (!sendResult.ok) {
      log("页面脚本报错:", sendResult.error);
      api("POST", "/complete", { task_id: taskId, text: "[页面错误] " + sendResult.error, title: "ChatGPT回答" }, () => {});
      return;
    }

    log("页面已发送 prompt，等待回答...");
    const answer = await waitAnswer();
    justSubmitted = true;
    log("捕获回答，回传桥:", answer ? answer.slice(0, 60) + "..." : "(空)");
    api(
      "POST",
      "/complete",
      { task_id: taskId, text: answer || "[脚本警告] 未捕获到回答", title: "ChatGPT回答" },
      () => {}
    );
  }

  async function poll() {
    api("GET", "/pending", null, function (res) {
      if (res && res.task_id) processTask(res);
    });
  }
  setInterval(poll, 1500);
  log("脚本已加载，开始轮询 localhost:8799/pending");

  // ---------- 入站：捕获手动聊天（跳过自己触发的） ----------
  function observe() {
    const d = win.document;
    const main = d.querySelector("main");
    if (!main) return;
    const obs = new MutationObserver(() => {
      const msgs = d.querySelectorAll('[data-message-author-role="assistant"]');
      for (const el of msgs) {
        if (seen.has(el)) continue;
        seen.add(el);
        setTimeout(() => {
          if (justSubmitted) {
            justSubmitted = false;
            return;
          }
          const txt = el.innerText.trim();
          if (txt) api("POST", "/ingest", { text: txt, title: "ChatGPT手动对话" }, () => {});
        }, 2500);
      }
    });
    obs.observe(main, { childList: true, subtree: true });
  }

  const iv = setInterval(() => {
    if (win.document.querySelector("main")) {
      observe();
      clearInterval(iv);
    }
  }, 2000);
})();
