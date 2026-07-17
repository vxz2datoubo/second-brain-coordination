# 桌宠 (Live2D) 注意事项与踩坑记录

更新时间：2026-06-27
用途：记录 MaiBot Live2D 桌面宠物插件在开发和运维中遇到的坑及修复方案。

配套重建文档：
`F:\aipengyou\docs\deskpet-emotion-voice-rebuild.md`

---

## 1. PowerShell 编码损坏问题（重要！）

### 现象
- `plugin.py` 或 `gpt-sovits-bridge.py` 被 PowerShell 的 `Get-Content` / `Set-Content` 操作后，中文全角字符变成 U+FFFD 替换字符
- 代码行被重复（如 `import asyncio` 出现两次）
- Python 加载时报 `SyntaxError: invalid character`
- 桌宠 WebSocket 8523 端口不监听

### 根因
PowerShell 在重定向输出或读写含中文的 Python 文件时，可能损坏 UTF-8 编码。

### 修复
1. 从 Git 恢复：`git checkout HEAD -- plugin.py`
2. 或直接用 Node.js / Python 的 UTF-8 写入替代 PowerShell

### 注意事项
- **永远不要用 PowerShell 的 Get-Content/Set-Content/Out-File 操作含中文的 Python 文件**
- **永远不要用 PowerShell 的 `>` 重定向操作含中文的文件**
- 用 `uv run python` 代替 `python` 以确保使用项目 venv 的依赖
- 用 Node REPL 的 `fs/promises.writeFile(path, content, 'utf-8')` 是安全的替代方案

---

## 2. 桌宠重复说话 (Echo) 问题

### 现象
桌宠不仅说自己的回复，还会把用户刚才说的话也重复一遍。

### 可能原因（待确认）
- `_extract_text_from_message` 的 `raw_message` fallback 路径把所有 type="text" 的组件拼接
- 如果出站消息的 `raw_message` 中同时包含用户原文（在 ReplyComponent 的 target_message_content 中）和 MaiBot 回复
- `processed_plain_text` 格式可能是 `[回复]用户原文 + MaiBot回复`，正则只去掉了 `[回复]` 前缀但保留了用户原文

### 已加修复
1. `raw_message` 路径：过滤 subtype="reply" 的引用文本
2. `raw_message` 路径：对提取结果也做 `[回复xxx]` 前缀清理
3. `send_to_deskpet` 处：添加消息 ID 去重集合（`_sent_message_ids`）
4. `send_to_deskpet` 处：添加 DEBUG 日志，打印收到的消息内容以辅助定位

### 验证方式
重启 MaiBot 后和桌宠说一句话，检查日志中 `[Deskpet] send_to_deskpet received` 行，看 `processed_plain_text` 和 `raw_types` 的内容。

---

## 3. TTS 语音配置

### 架构
```
plugin.py → http://127.0.0.1:9881/tts → gpt-sovits-bridge.py → https://api.fish.audio/v1/tts → MP3/WAV → 前端播放
```

### Fish Audio 配置
- API Key: 在 `gpt-sovits-bridge.py` 的 `FISH_AUDIO_API_KEY` 中
- 音色 ID: 在 `FISH_AUDIO_REFERENCE_ID` 中
- 免费模型: header 中添加 `"model": "s2.1-pro-free"`
- 当前音色: 卖卖 (6343f4d874374a1f9cbf73e9c16414d8)

### 启动 TTS 桥
```powershell
cd F:\aipengyou\plugins\maibot_deskpet-plugin
uv run python gpt-sovits-bridge.py
```

### 注意事项
- TTS 通过 `asyncio.create_task` 后台异步执行，不阻塞文字显示
- TTS 桥需要 `aiohttp` 依赖（通过 `uv pip install aiohttp` 安装）
- 白嫖模型 `s2.1-pro-free` 需要在每个请求的 HTTP header 中携带 `model: s2.1-pro-free`

---

## 4. 情绪系统代价

### 结论
- 关键词情绪推断（`_infer_emotion_from_text`）延迟 < 1ms，可忽略
- Maisaka Tool 情绪控制（`set_deskpet_emotion`）在推理时顺便输出，无额外延迟
- 不需要担心情绪系统影响对话响应速度

---

## 5. 启动顺序

1. 启动 TTS 桥：`uv run python gpt-sovits-bridge.py`
2. 启动 MaiBot：`uv run python bot.py`
3. 桌宠前端会自动连接 8523 端口

---

## 6. 关键端口

| 端口 | 服务 |
|------|------|
| 8001 | MaiBot WebUI |
| 8523 | 桌宠 WebSocket |
| 9881 | TTS 桥 |
| 7999 | WebUI 开发服务器 |
