
# /AGENTS.md

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/AGENTS.md](https://docs.mai-mai.org/AGENTS.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
| 文件 | 说明 |
|------|------|
| `index.md` | VitePress 首页/Hero page，展示 MaiBot 简介和导航入口 |
| `README.md` | 项目说明，介绍文档仓库用途、本地开发方法和贡献指南 |
| `_redirects` | 单页应用路由重定向配置（所有路径重定向到 /index.html） |
| `.gitignore` | Git 忽略规则（node\_modules, dist, .vitepress/cache 等） |
| `package.json` | Node.js 项目配置（VitePress + Mermaid + Tabs 插件） |
| `pnpm-lock.yaml` | pnpm 依赖锁定文件 |
| `LICENSE` | 开源许可证文件 |
| 文件/文件夹 | 说明 |
|-------------|------|
| `config.mts` | VitePress 核心配置：导航栏、侧边栏、多语言（中文/English）、搜索、markdown 插件（Mermaid, Tabs）、社交链接 |
| `theme/` |

## 快速要点
- **不要在内容页中使用 Markdown 表格**。Markdown 表格在 VitePress 中渲染效果差（移动端不友好、列宽不可控），仅 `index.md` 页面允许使用表格。内容页请用定义列表替代，例如 `**`field`** — 说明。默认 X`

## 标题树
  - 根目录文件
  - 文件夹结构详述
    - `.vitepress/` — VitePress 站点配置
    - `manual/` — 用户手册（简体中文）
    - `develop/` — 开发文档（简体中文）
    - `features/` — 功能介绍页
    - `changelog/` — 更新日志
    - `community/` — 社区页面
    - `en/` — 英文版文档
    - `public/` — 静态资源
    - `.sisyphus/` — 内部工作流记录
  - 文档写作约定


---
*来源: https://docs.mai-mai.org/AGENTS.md*
