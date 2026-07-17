# MaiBot 第二大脑

这个目录保存了基于官方文档站 `https://docs.mai-mai.org` 的本地知识库快照，面向之后继续研究、开发和排错 MaiBot 使用。

## 目录结构
- `sources/`：官方 `llms.txt` 与 `llms-full.txt` 快照。
- `atoms/`：原子笔记；根目录是概念原子，`atoms/pages/` 是每个官方页面的来源页原子。
- `indexes/`：原子索引和官方来源目录。
- `maps/`：知识地图和主题关系。

## 推荐入口
- [知识地图](maps/maibot-knowledge-map.md)
- [原子笔记索引](indexes/atomic-index.md)
- [官方来源目录](indexes/source-catalog.md)

## 快照信息
- 日期：2026-06-22
- 页面数：70
- 概念原子数：18
- 来源页原子数：70

## 维护原则
- 以后重新学习官方文档时，先更新 `sources/` 快照，再重建索引和页面原子。
- 概念原子可以人工增补，但要保留来源链接。
- 涉及代码实现时，以当前仓库代码和项目 `AGENTS.md` 为最终约束；本知识库是辅助记忆，不替代代码实查。
