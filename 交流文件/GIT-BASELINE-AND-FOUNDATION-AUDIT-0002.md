# CODEX / WORKBUDDY TASK — GIT-BASELINE-AND-FOUNDATION-AUDIT-0002

## 结论

采用“方案A+”：

> 先完成Git初始化前审计和Foundation变更对账，再初始化仓库。  
> 禁止直接执行 `git init && git add .`。

当前状态应标记为：

`SUCCESS_WITH_FINDINGS`

原因：

1. `F:\aidanao` 尚不是Git仓库；
2. Foundation任务已修改现有代码并写回公告栏/进化日志；
3. 报告中的`changed_files`与实际写回范围可能不一致；
4. 当前回滚方案不足以恢复被修改的现有文件和数据库/日志记录。

---

## 第一部分：冻结边界

在本任务完成前：

- Codex暂停继续修改A线核心代码；
- B线允许只读审计；
- C线只允许设计测试矩阵或新增完全隔离的候选文件，不修改A线文件；
- WorkBuddy可以继续执行真实接口字段审计和数据采集；
- 禁止实盘、密钥访问、生产部署和候选参数激活。

---

## 第二部分：Foundation变更精确对账

Codex必须生成：

`F:\aidanao\coordination\RESULTS\FOUNDATION-DATA-GOVERNANCE-0001\CHANGE-AUDIT.md`

至少包含：

1. 实际新增文件；
2. 实际修改文件；
3. 实际写入的公告栏文件；
4. 实际写入的SQLite表和记录主键；
5. 实际写入的JSONL/审计日志行；
6. 每个文件修改前后SHA256；
7. 每个修改的最小diff摘要；
8. 运行过的全部命令；
9. 测试结果；
10. 未纳入`changed_files`但实际发生的写回。

重点核对：

- `brain_core/foundation_data_governance.py`
- `brain_core/service.py`
- `apps/cli/brainctl.py`
- `docs/governance/*`
- `tests/test_foundation_data_governance.py`
- `bulletin/super-second-brain-v01-board.md`
- `data/super_brain_v01.sqlite`
- `data/audit/events.jsonl`
- SelfEvolutionLog实际存储位置

---

## 第三部分：可执行回滚包

不得使用“删除新模块与文档”作为完整回滚方案。

必须生成：

`F:\aidanao\coordination\RESULTS\FOUNDATION-DATA-GOVERNANCE-0001\ROLLBACK-PACK\`

包括：

- 修改前文件备份；
- 针对现有文件的反向补丁；
- SQLite精确回滚脚本，只删除本任务新增记录，不破坏其他记录；
- JSONL/公告栏回滚说明；
- 回滚前检查；
- 回滚后健康检查；
- 回滚脚本默认dry-run；
- SHA256 manifest。

不得立即执行回滚。

---

## 第四部分：Git初始化前审计

由Codex负责技术方案，WorkBuddy负责本机文件盘点。

必须检查：

- 是否存在嵌套Git仓库；
- 密钥、Token、Cookie、券商账号和私钥；
- `.env`和本地配置；
- SQLite、Parquet、CSV、原始行情、日志、模型文件；
- 大于10MB、50MB、100MB的文件；
- 缓存、临时文件、虚拟环境、node_modules；
- ComfyUI或其他无关工作区链接/复制文件；
- 需要Git LFS的候选文件；
- Windows路径和大小写问题。

输出：

- `GIT-PREFLIGHT.md`
- `LARGE-FILES.csv`
- `SECRET-SCAN.md`
- `NESTED-REPOS.md`
- `.gitignore.candidate`
- `.gitattributes.candidate`
- `INITIAL-COMMIT-PLAN.md`

---

## 第五部分：初始Git范围

建议首个Git基线只纳入：

- 源代码；
- 测试；
-Schema；
- 非敏感配置模板；
- 架构和治理文档；
- 小型示例fixture。

默认排除：

- `data/raw/`
- 实时行情与历史大数据；
- SQLite运行库；
- 日志；
- 模型权重；
- 缓存；
- 临时报告；
- 密钥与账号文件；
- WorkBuddy运行产物；
- 大型ZIP和备份。

`bulletin`是否纳入Git，需要区分：

- 稳定治理文档：可纳入；
- 高频运行公告：建议排除或单独归档。

---

## 第六部分：用户批准后才可执行

完成前述审计后，等待用户明确批准以下动作：

1. `git init`
2. 默认分支设为`main`
3. 激活审核后的`.gitignore`与`.gitattributes`
4. 只添加批准范围
5. 生成初始基线提交
6. 不配置远程仓库
7. 不推送任何内容

初始提交前必须展示：

- 待提交文件数量；
- 总大小；
- 最大文件；
- 敏感扫描结果；
- 被排除目录；
- 初始提交message候选。

---

## 第七部分：Git建立后的工作线

Git基线完成后：

- A线：`codex/foundation-data-governance-0001`
- B线：`codex/repo-arch-audit-0001`
- C线：`codex/test-ci-governance-0001`

每条线使用独立worktree。

合并顺序：

1. A线核心契约；
2. C线测试治理；
3. B线审计转化为独立重构任务；
4. WorkBuddy真实字段映射。

---

## 完成反馈格式

若全部审计完成且无风险：

`SUCCESS_WITH_FINDINGS`

必须返回：

- 变更对账结果；
- 发现的漏报写回；
- 回滚包路径；
- Git预检结果；
- 候选`.gitignore`；
- 待用户批准的Git动作；
- 是否发现P0/P1问题；
- 结果目录；
- SHA256。

不得在本任务中直接初始化Git或生成提交。
