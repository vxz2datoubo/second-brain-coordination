# ChatGPT 第二大脑桥 - Chrome 扩展安装说明

## 文件结构

```
extension/
├── manifest.json
├── background.js
└── content.js
```

## 安装步骤

1. 打开 Edge/Chrome 浏览器，地址栏输入：`chrome://extensions/` 或 `edge://extensions/`
2. 开启右上角 **"开发者模式"**（Developer mode）
3. 点击 **"加载已解压的扩展"**（Load unpacked）
4. 选择本目录：`F:/aidanao/chatgpt_bridge/extension`
5. 扩展加载后，打开或刷新 `https://chatgpt.com`
6. 按 F12 → Console，应看到：`[第二大脑桥-content] content script 已加载`

## 使用

- 在 WorkBuddy 里说一句：`问 ChatGPT：你好，世界。`
- 扩展会自动把问题填进 ChatGPT 输入框、发送、等待回答、回传给桥
- 桥自动把回答存入第二大脑

## 注意

- 首次使用前请确保已登录 ChatGPT
- 请确保桥服务在运行（`start_bridge.bat` 或后台已启动）
- 如果扩展图标显示"错误"，点击"重新加载"即可
