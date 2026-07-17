# 市场环境温度计 - 2026-06-21T11:08:35

- 环境分: -48
- 环境状态: risk_off
- 风险乘数: 0.25
- 指数CSV: `F:/ai/qclaw-output/finance-market-index-sample.csv`
- 宽度JSON: `F:/ai/qclaw-output/finance-market-breadth-sample.json`

## 原因

- 指数短均线未站上长均线
- 指数收盘弱于20日均线
- 下跌家数占优
- 下跌成交额占优

## 使用原则

- `risk_off` 或 `weak` 时，仓位计划自动降低单笔风险和总暴露。
- 市场温度计只调节风险，不会绕过个股质量、可成交性和交易前 consult。
- 没有指数或宽度数据时，系统会提示缺失，但不阻断日流水线。
