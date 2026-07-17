# UPGRADE-AB-TEST-PLAN — v1.0.4 → v1.0.12 升级对比方案

> 本任务禁止实际升级。此方案供升级后执行。更新前先保存 v1.0.4 快照(PREUPDATE-HASHES.csv)。

## 升级前快照 (已保存)
- tqcenter.py SHA256 + DLL SHA256 (见 PREUPDATE-HASHES.csv)
- v1.0.4 方法清单 (V104-METHOD-SURFACE.md)
- v1.0.4 get_more_info 4标的基线 (probes/more_info_*.json)

## 升级后必须重测的接口 (按优先级)

### P0: get_more_info 字段差异
```python
tq.initialize(__file__)
data = tq.get_more_info("300418.SZ")
# 比对: v1.0.4 86字段 → v1.0.12 是否新增字段? 哪些字段值变化?
# 重点: L2TicNum/BCancel/SCancel/Zjl 等L2聚合字段
```

### P0: Tick 支持
```python
tq.get_market_data(stock_list=["300418.SZ"], period='tick', count=10)
# v1.0.4: error -5 → v1.0.12: 是否能返回 Date/Time+价格?
```

### P1: 新增方法存在性
```python
hasattr(tq, 'get_pricevol')       # v1.0.4=False → v1.0.12 应为 True
hasattr(tq, 'get_match_stkinfo')  # v1.0.4=False
hasattr(tq, 'get_relation')       # v1.0.4=False
hasattr(tq, 'formula_get_all')    # v1.0.4=False → 待确认
hasattr(tq, 'formula_get_info')   # v1.0.4=False → 待确认
```

### P1: get_pricevol 测试
```python
tq.get_pricevol("300418.SZ")
# 价量分布：是否返回 LastClose/Now/Volume + 价量区间?
```

### P2: HTTP 17709 可用性
v1.0.12 更新后检查端口 17709 是否变为 LISTENING，以启用 TQ-Local 路线。

### P2: subscribe_hq 推送字段
v1.0.12 的 subscribe_hq 回调是否仍只有 Code+ErrorId？还是新增实际行情数据？

## 预期差异
- v1.0.12 可能新增: get_pricevol(价量), get_relation(关联品种), get_match_stkinfo(模糊查找)
- v1.0.12 get_more_info 可能字段数 >86
- v1.0.12 tick period 可能可用(DOCUMENT_CONFLICT, 待证实)
- v1.0.12 formula_get_all 可能存在(DOCUMENT_CONFLICT, 待证实)
- v1.0.12 端口 17709 可能可用

## 升级后也需要重测的旧能力 (回归)
- get_market_snapshot: 是否仍五档？
- subscribe_hq: 推送字段是否增加？
- get_market_data: 各周期正常？
- 错误处理: 无初始化时调用是否仍报 RuntimeError？
