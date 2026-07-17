# RUN-RECEIPT — TDX-OFFICIAL-ENTRY-RUNTIME-AUDIT-0006

> 生成: 2026-07-16 ~10:50 | 模型: Hy3 最强推理配置 | 状态: **COMPLETED (HTTP 阻塞, 部分结论基于文档静态分析)**

## 1. 实际模型配置
Hy3 最强推理模型。盲审+静态分析→ 结合 Codex 已验证前提。

## 2. 任务状态
COMPLETED。旧目录 0003/0004/0005 未改动。TdxW PID 1628 存活。

## 3. HTTP 17709 是否可用
**不可用。** 端口 NOT_LISTENING。TDX 客户端 HTTP 服务未启动。

## 4. 官方 TQ-Local 是否可用
**不可用。** 依赖 HTTP 17709 → 在当前会话被阻塞。

## 5. 官方 TQ-Python 是否可用
**理论上可安装**，但本地 tqcenter.py 是 v1.0.4 → v1.0.12 技能文档生成的新接口代码会因本地版本落后而运行失败。版本错位。

## 6. 是否发现新版方法
**是。** TQ-Local/Python v1.0.12 SKILL.md 含: `get_pricevol`(价量分布), `get_more_info`(含 L2TicNum/L2OrderNum/BCancel/SCancel/TotalBVol/TotalSVol/OpenZTBuy/Zjl/Zjl_HB 等), `get_match_stkinfo`, `get_relation`, `get_kzz_info`, `download_file` 等。**但 formula_get_all / formula_get_info 未见。**

## 7. 是否比 Codex 的 Python 路线更丰富
- HTTP/TQ-Local v1.0.12 文档：**是**(更多 L2 聚合字段)
- 本地 Python v1.0.4：**否**(落后)
- 但 HTTP 当前不可用 → 实际不可达

## 8. 是否取得十档
**否。** HTTP 文档 get_market_snapshot 明确仅五档(BuyP[5]+SellP[5])。

## 9. 是否取得原始逐笔成交
**否。** HTTP 文档 period 无 'tick'，无逐笔数组字段。仅 L2TicNum(计数聚合)。

## 10. 是否取得原始逐笔委托
**否。** 仅 L2OrderNum(计数聚合)。

## 11. 是否取得委托队列
**否。** 三条路线均未出现 queue 相关接口。

## 12. 是否取得集合竞价字段
**仅聚合。** get_more_info 有 OpenAmo(开盘额)/OpenZTBuy(竞价涨停买入额)，无虚拟参考价/匹配量/未匹配量。

## 13. 是否存在版本错位
**是。** tqcenter.py v1.0.4 vs 官方 v1.0.12，落后约 8 个 minor 版本。

## 14. 是否建议更新任何组件
**是。** 建议更新 tqcenter.py + TPythClient.dll 到最新版本 + 启用 HTTP 17709 (通过 TDX 官方更新通道, 非手动替换)。

## 15. 是否修改现有系统
**否。** 本轮未做任何修改。更新建议仅写入报告。

## 16. 输出目录
`F:\aidanao\交流文件\TDX-OFFICIAL-ENTRY-RUNTIME-AUDIT-0006\` (14 文件)
