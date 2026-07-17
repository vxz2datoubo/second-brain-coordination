已修改 [core/decision_consult.py](F:/ai/core/decision_consult.py:13)，只动了这个源码文件。

改动位置：
- [13, 28](F:/ai/core/decision_consult.py:13)：引入 `logging`，新增模块级 `logger`。
- [39](F:/ai/core/decision_consult.py:39)：`ConsultResult` 新增 `errors: list = field(default_factory=list)`，放在末尾以保持现有构造参数兼容。
- [84-121](F:/ai/core/decision_consult.py:84)：`_search()` 捕获异常后记录 `query/category/exception_type`，并把结构化错误写入传入的 `errors`。
- [125-129](F:/ai/core/decision_consult.py:125)：`_expand_queries()` 现在先使用 `DEFAULT_LESSON_QUERY_TEMPLATES`，再追加 topic 相关扩展。
- [191-225](F:/ai/core/decision_consult.py:191)：三处 `h["id"]` 改为 `h.get("id")`，缺失时 `continue` 跳过。

测试结果：
- `python -m py_compile F:\ai\core\decision_consult.py`：通过
- 内联 `unittest` 覆盖 3 个修复点：`Ran 3 tests ... OK`

没有新增测试文件；按你的要求未修改其他源码文件。