"""Local Autopilot — 全自动推进引擎（SLEEP_AUTONOMY 执行载体）。

把已有治理零件（durable_mission_kernel、CONTROL-TOWER、Unified Execution
Fabric）串成一个无人值守闭环：

    sync -> discover -> claim -> execute -> verify -> report
         -> commit -> push -> PR -> tiered-merge -> next

这是「编排层」，不是第二个控制面：它只调用既有 canonical 模块，不重写
治理逻辑，也不授予任何新的 secret / production / trading / funds / orders
/ review / merge 权限。所有 merge 都走受治理的分层策略（见 auto_merge）。
"""

from __future__ import annotations

__version__ = "0.1.0"
__task_id__ = "LOCAL-AUTOPILOT-SLEEP-AUTONOMY-0001"
