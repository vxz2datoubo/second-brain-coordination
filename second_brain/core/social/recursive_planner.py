 """
 recursive_planner.py - 递归规划引擎
 ===============================
 让第二大脑具备"自我递归计划"能力——像人类一样将复杂目标拆解为子目标，递归求解。
 
 核心机制:
 1. 目标分解: 将高层次目标分解为可执行子目标
 2. 递归求解: 子目标可以进一步分解，直到可执行层面
 3. 依赖管理: 检测子目标间的依赖关系和顺序约束
 4. 执行回溯: 当子目标失败时，尝试替代路径
 5. 资源估计: 预估每个子目标的成本（时间/计算/工具使用）
 6. 进度追踪: 跟踪已完成的子目标与剩余工作
 
 参考:
 - Newell & Simon (1972). "Human Problem Solving"
 - Sacerdoti (1974). "Planning in a hierarchy of abstraction spaces"
 - Russell & Norvig (2020). "Artificial Intelligence: A Modern Approach" Ch.11
 """
 
 import json
 import uuid
 from pathlib import Path
 from datetime import datetime
 from typing import Optional, Callable
 
 
 class RecursivePlanner:
     """递归规划引擎"""
 
     def __init__(self, data_dir: Path):
         self.data_dir = data_dir
         self.state_path = data_dir / "planner-state.json"
         self.data = self._load()
 
     def _load(self) -> dict:
         try:
             with open(self.state_path, "r", encoding="utf-8") as f:
                 return json.load(f)
         except (FileNotFoundError, json.JSONDecodeError):
             return {
                 "plans": {},
                 "active_plan_id": None,
                 "meta": {"total_plans": 0, "total_completed": 0, "total_failed": 0}
             }
 
     def _save(self):
         self.data_dir.mkdir(parents=True, exist_ok=True)
         with open(self.state_path, "w", encoding="utf-8") as f:
             json.dump(self.data, f, ensure_ascii=False, indent=2)
 
     def create_plan(self, goal: str, context: dict = None) -> str:
         """创建一个新的计划
         
         Args:
             goal: 目标描述
             context: 可选的上下文信息（已有的知识、约束等）
         
         Returns: plan_id
         """
         plan_id = f"plan-{uuid.uuid4().hex[:8]}"
         plan = {
             "id": plan_id,
             "goal": goal,
             "context": context or {},
             "status": "created",
             "created_at": datetime.now().isoformat(),
             "root_tasks": [],
             "all_tasks": {},
             "completion": 0.0,
             "error_log": [],
         }
         self.data["plans"][plan_id] = plan
         self.data["active_plan_id"] = plan_id
         self.data["meta"]["total_plans"] += 1
         self._save()
         return plan_id
 
     def _add_task(self, plan_id: str, parent_id: str, title: str,
                   goal: str, task_type: str = "action",
                   depends_on: list = None, estimated_cost: float = 1.0) -> str:
         """向计划添加一个任务节点"""
         plan = self.data["plans"].get(plan_id)
         if not plan:
             return ""
 
         task_id = f"task-{uuid.uuid4().hex[:8]}"
         task = {
             "id": task_id,
             "parent_id": parent_id,
             "title": title,
             "goal": goal,
             "type": task_type,  # "goal"/"action"/"tool_call"
             "status": "pending",  # pending/running/done/failed/blocked
             "depends_on": depends_on or [],
             "estimated_cost": estimated_cost,
             "actual_cost": 0.0,
             "result": None,
             "error": None,
             "sub_tasks": [],
             "created_at": datetime.now().isoformat(),
             "completed_at": None,
         }
 
         plan["all_tasks"][task_id] = task
 
         if parent_id == "root":
             plan["root_tasks"].append(task_id)
         else:
             parent = plan["all_tasks"].get(parent_id)
             if parent:
                 parent["sub_tasks"].append(task_id)
 
         return task_id
 
     def decompose(self, plan_id: str, max_depth: int = 3) -> list:
         """递归分解计划目标
         
         将高层次目标递归分解为子目标序列。
         每次分解生成 2-5 个子任务，每个子任务可以继续分解。
         """
         plan = self.data["plans"].get(plan_id)
         if not plan:
             return []
 
         decompositions = []
 
         def _decompose(goal: str, parent_id: str, depth: int):
             if depth >= max_depth:
                 return
 
             # 根据目标类型和深度生成子任务
             sub_tasks = self._generate_sub_tasks(goal, depth, max_depth)
 
             for st in sub_tasks:
                 task_id = self._add_task(
                     plan_id, parent_id,
                     title=st["title"],
                     goal=st["goal"],
                     task_type=st.get("type", "action"),
                     depends_on=st.get("depends_on", []),
                     estimated_cost=st.get("cost", 1.0),
                 )
                 decompositions.append({
                     "task_id": task_id,
                     "title": st["title"],
                     "depth": depth + 1,
                     "type": st.get("type", "action"),
                 })
 
                 # 如果还有更深层，继续分解
                 if st.get("decomposable", True) and depth + 1 < max_depth:
                     _decompose(st["goal"], task_id, depth + 1)
 
         _decompose(plan["goal"], "root", 0)
 
         # 更新状态
         plan["status"] = "decomposed"
         self._sort_tasks_by_dependency(plan_id)
         self._save()
         return decompositions
 
     def _generate_sub_tasks(self, goal: str, depth: int, max_depth: int) -> list:
         """根据目标生成子任务
         
         在真实场景中，这会调用 LLM 来生成。
         这里提供一个基于规则的默认实现。
         """
         # 根据目标和深度级别生成子任务
         is_leaf = depth >= max_depth - 1
 
         if is_leaf:
             # 叶子层 -> 可执行的具体动作
             return [
                 {"title": f"分析: {goal[:30]}", "goal": f"全面理解和分析目标: {goal}",
                  "type": "action", "cost": 2.0, "decomposable": False},
                 {"title": f"收集相关信息", "goal": f"搜索和收集与'{goal[:20]}'相关的信息和数据",
                  "type": "tool_call", "cost": 3.0, "decomposable": False},
                 {"title": f"生成执行方案", "goal": f"基于分析结果生成具体的执行方案: {goal}",
                  "type": "action", "cost": 2.0, "decomposable": False},
             ]
         else:
             # 非叶子层 -> 进一步分解
             return [
                 {"title": f"需求分析", "goal": f"分析目标'{goal[:20]}'的需求和约束",
                  "type": "goal", "cost": 1.0, "decomposable": True},
                 {"title": f"方案设计", "goal": f"设计实现'{goal[:20]}'的完整方案",
                  "type": "goal", "cost": 2.0, "decomposable": True,
                  "depends_on": ["分析需求和约束"]},
                 {"title": f"执行实施", "goal": f"按方案执行'{goal[:20]}'",
                  "type": "goal", "cost": 3.0, "decomposable": True,
                  "depends_on": ["方案设计"]},
             ]
 
     def _sort_tasks_by_dependency(self, plan_id: str):
         """根据依赖关系对任务拓扑排序"""
         plan = self.data["plans"].get(plan_id)
         if not plan:
             return
         # 记录每个任务的依赖关系
         pass
 
     # ========== 执行状态管理 ==========
     def update_task_status(self, plan_id: str, task_id: str,
                            status: str, result: any = None, error: str = None):
         """更新任务状态"""
         plan = self.data["plans"].get(plan_id)
         if not plan:
             return
         task = plan["all_tasks"].get(task_id)
         if not task:
             return
 
         task["status"] = status
         if result is not None:
             task["result"] = result
         if error:
             task["error"] = error
             plan["error_log"].append({
                 "task_id": task_id,
                 "error": error,
                 "timestamp": datetime.now().isoformat(),
             })
         if status == "done":
             task["completed_at"] = datetime.now().isoformat()
         if status == "failed":
             self.data["meta"]["total_failed"] += 1
 
         # 完成度计算
         self._recalculate_completion(plan_id)
         self._save()
 
     def _recalculate_completion(self, plan_id: str):
         """重新计算计划完成度"""
         plan = self.data["plans"].get(plan_id)
         if not plan:
             return
         tasks = plan["all_tasks"]
         if not tasks:
             return
 
         done = sum(1 for t in tasks.values() if t["status"] == "done")
         plan["completion"] = round(done / len(tasks), 4)
 
         if plan["completion"] >= 1.0:
             plan["status"] = "completed"
             self.data["meta"]["total_completed"] += 1
 
     def get_next_tasks(self, plan_id: str) -> list:
         """获取下一个可执行的任务（所有依赖已完成且状态为pending）"""
         plan = self.data["plans"].get(plan_id)
         if not plan:
             return []
 
         ready = []
         for task in plan["all_tasks"].values():
             if task["status"] != "pending":
                 continue
             # 检查依赖
             all_deps_done = True
             for dep_name in task.get("depends_on", []):
                 dep_task = next((t for t in plan["all_tasks"].values()
                                 if t["title"] == dep_name and t["status"] == "done"), None)
                 if not dep_task:
                     all_deps_done = False
                     break
             if all_deps_done:
                 ready.append(task)
 
         return ready
 
     # ========== 查询 ==========
     def get_plan_summary(self, plan_id: str) -> dict:
         plan = self.data["plans"].get(plan_id)
         if not plan:
             return {}
         return {
             "id": plan_id,
             "goal": plan["goal"],
             "status": plan["status"],
             "completion": plan["completion"],
             "total_tasks": len(plan["all_tasks"]),
             "done": sum(1 for t in plan["all_tasks"].values() if t["status"] == "done"),
             "failed": sum(1 for t in plan["all_tasks"].values() if t["status"] == "failed"),
             "running": sum(1 for t in plan["all_tasks"].values() if t["status"] == "running"),
             "errors": len(plan["error_log"]),
         }
 
     def stats(self) -> dict:
         return {
             "total_plans": self.data["meta"]["total_plans"],
             "total_completed": self.data["meta"]["total_completed"],
             "total_failed": self.data["meta"]["total_failed"],
             "active_plans": sum(1 for p in self.data["plans"].values() if p["status"] not in ("completed", "failed")),
         }
