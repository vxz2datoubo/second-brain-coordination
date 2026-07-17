## 1. 整体定位

`F:/ai/core/decision_consult.py` 是一个“决策前检索网关”：输入决策主题后，自动扩展查询词，调用第二大脑检索接口，聚合教训、规则和相关知识，并在命中高风险教训时给出警告。

## 2. 优点

1. **结果对象结构清晰**  
   `ConsultResult` 把 `matched_lessons`、`matched_rules`、`matched_knowledge`、`warning` 分开建模，调用方容易判断和展示。  
   引用: `F:/ai/core/decision_consult.py:29-44`

2. **查询扩展覆盖了风险语义**  
   `_expand_queries()` 不只搜原始 topic，还补充了“教训 / 经验 / 失败 / 不要 / 红线”等表达，适合决策前风险召回。  
   引用: `F:/ai/core/decision_consult.py:99-114`

3. **有明确的“真教训”过滤规则**  
   `_is_real_lesson()` 通过 category、标题前缀、黑名单过滤自动摄入的脏数据，避免把普通记忆误当成决策教训。  
   引用: `F:/ai/core/decision_consult.py:116-152`

4. **三路检索职责分明**  
   `consult()` 分别检索教训、规则、知识，并各自去重、截断，整体流程容易理解。  
   引用: `F:/ai/core/decision_consult.py:167-197`

5. **高风险警告有兜底规则**  
   通过 `score >= 5.5` 或标题包含“不要 / 切勿 / 严禁 / 红线 / 致命 / 降级”触发顶级警告，适合前置拦截高风险决策。  
   引用: `F:/ai/core/decision_consult.py:199-204`

## 3. 问题

1. **异常被完全吞掉，缺乏可观测性**  
   `_search()` 捕获所有异常后直接 `return []`，调用方无法区分“确实无结果”和“服务挂了 / JSON 解析失败 / 网络超时”。变量 `e` 也未使用。  
   引用: `F:/ai/core/decision_consult.py:87-97`

2. **`category` 参数可能没有实际生效，影响检索正确性**  
   `_search()` 会把 `category` 放进 payload，`consult()` 也认为第一路检索是“强制走 decision-lessons 类别”。但如果服务端搜索接口不支持该字段，这里的分类检索只是客户端假设，召回会混入其他类别，只靠 `_is_real_lesson()` 事后过滤。  
   引用: `F:/ai/core/decision_consult.py:83-85`, `F:/ai/core/decision_consult.py:167-170`

3. **对检索结果字段过于乐观，可能 `KeyError`**  
   多处直接访问 `h["id"]`，如果 API 返回缺少 `id` 的异常数据，会导致整个 `consult()` 中断。  
   引用: `F:/ai/core/decision_consult.py:172-173`, `F:/ai/core/decision_consult.py:183-184`, `F:/ai/core/decision_consult.py:192-195`

4. **最坏情况下性能延迟偏高**  
   默认扩展 6 个查询，教训检索 6 次、规则检索 4 次、知识检索 6 次，共约 16 次 HTTP 请求；每次 timeout 5 秒，服务异常时最坏可能接近 80 秒。  
   引用: `F:/ai/core/decision_consult.py:93`, `F:/ai/core/decision_consult.py:169-181`, `F:/ai/core/decision_consult.py:189-190`

5. **扩展性有硬编码和未使用代码**  
   `DEFAULT_LESSON_QUERY_TEMPLATES` 定义后没有被 `_expand_queries()` 使用；黑名单、类别、标题前缀、风险关键词也全部硬编码，后续调整规则需要改源码。  
   引用: `F:/ai/core/decision_consult.py:19-26`, `F:/ai/core/decision_consult.py:128-149`, `F:/ai/core/decision_consult.py:199-202`

## 4. 关键风险

有 **正确性风险** 和 **可观测性风险**。最大问题是检索失败会被静默解释成“无匹配”，这在“决策前安全检查”场景里容易造成误放行。其次，分类检索是否真的生效依赖服务端实现，如果服务端忽略 `category`，当前模块的“强制 decision-lessons”语义并不成立。性能上，串行 HTTP 请求较多，服务慢或不可用时会明显拖慢决策流程。安全风险相对较低，因为默认只访问 localhost，但 `brain_url` 可外部传入，若未来接收不可信配置，应限制目标或增加审计。

## 5. 改进建议

1. **最高优先级: 增加失败状态和日志**  
   `_search()` 不应静默吞异常。建议至少记录 query、category、异常类型、耗时；`ConsultResult` 可增加 `errors` 或 `retrieval_ok` 字段，让调用方知道本次检查是否可信。

2. **确认并补齐服务端 category 过滤**  
   如果 `/api/retrieve/search` 需要支持 `category`，应在服务端实际过滤；如果不支持，应移除“强制走 decision-lessons”的注释，改成“全局检索后本地过滤”，避免语义误导。

3. **增强结果字段防御**  
   把 `h["id"]` 改成 `node_id = h.get("id")`，缺失时跳过或生成可追踪错误，避免单条坏数据打断整个决策咨询。

4. **减少串行请求成本**  
   可以合并查询词、提高单次 `top_k` 后本地分类，或并发执行 HTTP 请求；同时设置总超时预算，例如一次 consult 最多 8-10 秒。

5. **把规则配置化**  
   将查询模板、黑名单、标题前缀、风险关键词、score 阈值抽到配置文件或类初始化参数中，并真正复用 `DEFAULT_LESSON_QUERY_TEMPLATES`。

## 6. 总结

这个模块的核心思路是对的：它把“决策前先查历史教训”封装成了一个清晰入口，检索路径、去重、分类和警告逻辑也已经成型。当前最需要补强的是可靠性和可观测性，尤其不能把检索系统不可用伪装成“没有风险”。如果补上异常记录、服务端分类过滤确认、结果字段防御和请求预算控制，它会更适合作为 WorkBuddy 的关键决策前置检查模块。