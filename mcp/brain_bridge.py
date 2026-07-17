"""brain_bridge.py — 第二大脑 MCP 服务器 (stdio)

将第二大脑知识库暴露为 MCP 工具，供 MaiBot 的 Planner 调用。

协议: JSON-RPC 2.0 over stdin/stdout
暴露 4 个工具:
  brain_search  — 搜索知识库 (TF-IDF)
  brain_consult — 决策前检索教训/规则/知识
  brain_digest  — 摄入新知识到第二大脑
  brain_read    — 读取知识图谱节点或邻居

启动方式 (MaiBot 配置):
  command = "python"
  args = ["-u", "F:/aidanao/mcp/brain_bridge.py"]

依赖: 仅 Python 标准库 + core/decision_consult.py (同项目)
"""
import json
import logging
import sys
import urllib.request
from pathlib import Path

# 将项目根目录加入 sys.path (确保 MaiBot 子进程能导入 core 模块)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [brain_bridge] %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("brain_bridge")

BRAIN_URL = "http://localhost:8766"
_LOCAL_BRAIN = None

# ---------- HTTP helpers ----------

def _get_json(path: str) -> dict:
    req = urllib.request.Request(f"{BRAIN_URL}{path}")
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read())


def _post_json(path: str, payload: dict, timeout: int = 10) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BRAIN_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())

def _search(query: str, top_k: int = 5, category: str | None = None) -> list:
    """调用第二大脑搜索 API"""
    payload = {"query": query, "top_k": max(1, min(top_k, 20))}
    if category:
        payload["category"] = category
    result = _post_json("/api/retrieve/search", payload, timeout=8)
    return result.get("results", [])


def _digest(text: str, title: str = "", source: str = "maibot-mcp") -> dict:
    """调用第二大脑摄入 API"""
    payload = {"text": text, "title": title, "source": source}
    return _post_json("/api/digest/text", payload, timeout=10)


def _read_graph(node_id: str | None = None, depth: int = 1) -> dict:
    """读取知识图谱"""
    if node_id:
        path = f"/api/retrieve/knowledge-graph?node_id={node_id}&depth={depth}"
    else:
        path = "/api/knowledge-graph"
    return _get_json(path)


def _trading_replay_summary(symbol: str, timeframe: str = "1d", data_path: str = "") -> dict:
    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "summary_only": True,
    }
    if data_path:
        payload["data_path"] = data_path
    return _post_json("/api/v0/trading/replay", payload, timeout=90)


def _trading_a_share_realtime_crosscheck(symbol: str, timeframe: str = "1d") -> dict:
    payload = {"symbol": symbol, "timeframe": timeframe}
    return _post_json("/api/v0/trading/a-share/realtime-crosscheck-summary", payload, timeout=12)


def _trading_research_queue_approval_summary(candidate_slug: str = "", limit: int = 5) -> dict:
    brain = _get_local_brain()
    return brain.trading_research_queue_approval_summary({
        "candidate_slug": candidate_slug,
        "limit": max(1, min(limit, 20)),
    })


def _trading_research_queue_watchlist(candidate_slug: str = "", min_approvals: int = 1) -> dict:
    brain = _get_local_brain()
    return brain.trading_research_queue_watchlist({
        "candidate_slug": candidate_slug,
        "min_approvals": max(1, min(min_approvals, 20)),
    })


def _trading_research_queue_review_agenda(
    candidate_slug: str = "",
    min_approvals: int = 1,
    top_limit: int = 3,
) -> dict:
    brain = _get_local_brain()
    return brain.trading_research_queue_review_agenda({
        "candidate_slug": candidate_slug,
        "min_approvals": max(1, min(min_approvals, 20)),
        "top_limit": max(1, min(top_limit, 20)),
    })


def _trading_research_queue_next_validation_slice(
    candidate_slug: str = "",
    min_approvals: int = 1,
    top_limit: int = 3,
) -> dict:
    brain = _get_local_brain()
    return brain.trading_research_queue_next_validation_slice({
        "candidate_slug": candidate_slug,
        "min_approvals": max(1, min(min_approvals, 20)),
        "top_limit": max(1, min(top_limit, 20)),
    })


def _trading_research_queue_latest_validation_summary(
    candidate_slug: str = "",
    min_approvals: int = 1,
    top_limit: int = 3,
) -> dict:
    brain = _get_local_brain()
    return brain.trading_research_queue_latest_validation_summary({
        "candidate_slug": candidate_slug,
        "min_approvals": max(1, min(min_approvals, 20)),
        "top_limit": max(1, min(top_limit, 20)),
    })


def _trading_research_queue_run_next_validation_slice(payload: dict) -> dict:
    brain = _get_local_brain()
    return brain.trading_research_queue_run_next_validation_slice(payload)


def _trading_confirm_research_queue_manual_approval(payload: dict) -> dict:
    brain = _get_local_brain()
    return brain.trading_confirm_research_queue_manual_approval(payload)


def _v0_status() -> dict:
    http_payload: dict = {}
    try:
        http_payload = _get_json("/api/v0/status")
    except Exception:
        http_payload = {}
    local_payload = _local_status()
    if not http_payload:
        return local_payload
    for key in (
        "trading_status",
        "latest_workbuddy_probability_fusion_mock",
        "latest_trading_research_queue_bulletin_state",
        "latest_trading_self_evolution_log",
        "latest_trading_skill_registry_entry",
        "latest_trading_module_status_record",
        "latest_trading_bulletin_state_record",
    ):
        if key not in http_payload or not http_payload.get(key):
            http_payload[key] = local_payload.get(key, {})
    return http_payload


def _v0_board() -> dict:
    return _get_json("/api/v0/board")


def _v0_evolution_log(limit: int = 10) -> dict:
    return _get_json(f"/api/v0/evolution/log?limit={max(1, min(limit, 50))}")


def _get_local_brain():
    global _LOCAL_BRAIN
    if _LOCAL_BRAIN is None:
        from brain_core.service import SuperBrainV01

        _LOCAL_BRAIN = SuperBrainV01(PROJECT_ROOT)
    return _LOCAL_BRAIN


def _local_status() -> dict:
    try:
        return _get_local_brain().status()
    except Exception as exc:
        logger.warning("local brain_core status fallback failed: %s", exc)
        return {}


def _brain_healthy() -> bool:
    """检查第二大脑是否在线"""
    try:
        req = urllib.request.Request(f"{BRAIN_URL}/api/stats")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


# ---------- Format helpers ----------

def _fmt_node(n: dict) -> str:
    """格式化单个节点为紧凑文本"""
    node_id = n.get("id", "?")[:10]
    title = n.get("title", "无标题")[:100]
    score = n.get("score", 0)
    summary = n.get("summary", "")[:120]
    category = n.get("category", "")
    parts = [f"[{node_id}] {title}"]
    if category:
        parts.append(f"  分类: {category}")
    if score:
        parts.append(f"  相关度: {score:.1f}")
    if summary:
        parts.append(f"  摘要: {summary}")
    return "\n".join(parts)


# ---------- Tool implementations ----------

def tool_brain_search(arguments: dict) -> str:
    """搜索第二大脑知识库"""
    query = arguments.get("query", "").strip()
    if not query:
        return "[brain_search] 错误: 缺少 query 参数"

    top_k = arguments.get("top_k", 5)
    category = arguments.get("category") or None

    try:
        results = _search(query, top_k=top_k, category=category)
    except Exception as e:
        return f"[brain_search] 搜索失败: {type(e).__name__}: {e}"

    if not results:
        return f"[brain_search] 未找到与 \"{query}\" 相关的知识节点。可以尝试换关键词或调 brain_digest 先摄入相关知识。"

    lines = [f"[brain_search] 搜索 \"{query}\" 找到 {len(results)} 个结果:"]
    for i, node in enumerate(results, 1):
        lines.append(f"\n--- 结果 {i} ---")
        lines.append(_fmt_node(node))
    return "\n".join(lines)


def tool_brain_consult(arguments: dict) -> str:
    """决策前检索：查询相关教训/规则/知识"""
    import importlib

    topic = arguments.get("topic", "").strip()
    if not topic:
        return "[brain_consult] 错误: 缺少 topic 参数"

    try:
        # 直接用 DecisionConsult 类 (本地 Python 调用, 不走 HTTP)
        decision_consult = importlib.import_module("core.decision_consult")
        dc = decision_consult.DecisionConsult(brain_url=BRAIN_URL)
        result = dc.consult(topic)
    except Exception as e:
        # fallback: 如果导入失败, 只做简单搜索
        logger.warning("decision_consult import failed: %s, falling back to search", e)
        result = None

    if result is None:
        # 降级: 直接搜索
        try:
            results = _search(topic, top_k=5)
            if not results:
                return f"[brain_consult] 未找到与 \"{topic}\" 相关的决策教训或知识。"
            lines = [f"[brain_consult] 决策主题 \"{topic}\" 的相关知识:"]
            for node in results:
                lines.append(_fmt_node(node))
            return "\n".join(lines)
        except Exception as e2:
            return f"[brain_consult] 查询失败: {type(e2).__name__}: {e2}"

    # 格式化为 LLM 友好的输出
    lines = [f"[brain_consult] 决策主题: \"{topic}\""]
    lines.append(f"检索结果: {len(result.matched_lessons)} 条教训 / {len(result.matched_rules)} 条规则 / {len(result.matched_knowledge)} 条知识")

    if result.warning:
        lines.append(f"\n  {result.warning}")

    if result.matched_lessons:
        lines.append(f"\n  教训 ({len(result.matched_lessons)} 条):")
        for m in result.matched_lessons[:5]:
            node_id = m.get("id", "?")[:8]
            title = m.get("title", "?")[:100]
            summary = m.get("summary", "")[:120]
            lines.append(f"    [{node_id}] {title}")
            if summary:
                lines.append(f"      {summary}")

    if result.matched_rules:
        lines.append(f"\n  规则 ({len(result.matched_rules)} 条):")
        for m in result.matched_rules[:3]:
            title = m.get("title", "?")[:100]
            lines.append(f"    - {title}")

    if result.matched_knowledge:
        lines.append(f"\n  相关知识 ({len(result.matched_knowledge)} 条):")
        for m in result.matched_knowledge[:3]:
            title = m.get("title", "?")[:100]
            lines.append(f"    - {title}")

    if result.errors:
        lines.append(f"\n  (检索过程中有 {len(result.errors)} 个错误, 已自动跳过)")

    return "\n".join(lines)


def tool_brain_digest(arguments: dict) -> str:
    """摄入新知识到第二大脑"""
    text = arguments.get("text", "").strip()
    if not text:
        return "[brain_digest] 错误: 缺少 text 参数"

    title = arguments.get("title", "").strip()
    source = arguments.get("source", "maibot-mcp")

    try:
        result = _digest(text, title=title, source=source)
        if result.get("success"):
            node = result.get("node", {})
            node_id = node.get("id", "?")[:10]
            node_title = node.get("title", "")[:80]
            return f"[brain_digest] 摄入成功! 节点 ID: {node_id}, 标题: {node_title}"
        else:
            return f"[brain_digest] 摄入失败: {result}"
    except Exception as e:
        return f"[brain_digest] 摄入异常: {type(e).__name__}: {e}"


def tool_brain_read(arguments: dict) -> str:
    """读取知识图谱内容"""
    node_id = arguments.get("node_id") or None
    depth = arguments.get("depth", 1)

    try:
        graph = _read_graph(node_id=node_id, depth=depth)
    except Exception as e:
        return f"[brain_read] 读取图谱失败: {type(e).__name__}: {e}"

    if node_id:
        # 返回邻居节点信息
        nodes = graph.get("neighbors", []) if isinstance(graph, dict) else graph
        if not nodes:
            return f"[brain_read] 节点 {node_id} 没有邻居。"
        lines = [f"[brain_read] 节点 {node_id} 的 {len(nodes)} 个关联节点:"]
        for i, node in enumerate(nodes[:10], 1):
            lines.append(f"\n--- 关联 {i} ---")
            lines.append(_fmt_node(node))
        return "\n".join(lines)
    else:
        # 返回全图统计
        nodes = graph.get("nodes", {})
        if isinstance(nodes, list):
            node_list = nodes
        else:
            node_list = list(nodes.values())
        total = len(node_list)
        if total == 0:
            return "[brain_read] 知识图谱为空。"
        # 分类统计
        cats = {}
        for n in node_list:
            c = n.get("category", "unknown") if isinstance(n, dict) else "unknown"
            cats[c] = cats.get(c, 0) + 1
        lines = [f"[brain_read] 知识图谱共有 {total} 个节点:"]
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: {count} 个节点")
        return "\n".join(lines)


def tool_brain_trading_replay(arguments: dict) -> str:
    """读取交易最小闭环的 replay 摘要"""
    symbol = str(arguments.get("symbol", "")).strip() or "300418"
    timeframe = str(arguments.get("timeframe", "1d")).strip() or "1d"
    data_path = str(arguments.get("data_path", "")).strip()
    try:
        summary = _trading_replay_summary(symbol=symbol, timeframe=timeframe, data_path=data_path)
    except Exception as e:
        return f"[brain_trading_replay] 查询失败: {type(e).__name__}: {e}"

    selected = summary.get("selected_candidate_summary", {}) or {}
    lines = [f"[brain_trading_replay] {symbol} replay 摘要"]
    lines.append(f"顶层策略: {summary.get('top_level_strategy_name', 'unknown')}")
    lines.append(f"候选数: {summary.get('candidate_count', 0)}")
    lines.append(f"选择状态: {selected.get('selection_status', 'unknown')}")
    lines.append(f"当前动作: {selected.get('portfolio_action', 'unknown')}")
    lines.append(f"治理动作: {selected.get('selection_governance_action', 'unknown')}")
    lines.append(f"样本外结果: {selected.get('out_of_sample_result', 'unknown')}")
    lines.append(f"验证结论: {selected.get('validation_verdict', 'unknown')}")
    lines.append(f"样本一致性: {selected.get('sample_consistency', 'unknown')}")
    governance_primary_reason = str(selected.get("governance_primary_reason", "")).strip()
    if governance_primary_reason:
        lines.append(f"治理主因: {governance_primary_reason}")
    primary_gate = str(selected.get("primary_gate", "")).strip()
    if primary_gate:
        lines.append(f"当前主门: {primary_gate}")
    queue_recommendation = str(selected.get("queue_recommendation", "")).strip()
    if queue_recommendation:
        lines.append(f"队列建议: {queue_recommendation}")
    freeze_status = str(selected.get("freeze_candidate_status", "")).strip()
    if freeze_status:
        lines.append(f"冻结态: {freeze_status}")
    upgrade_status = str(selected.get("upgrade_candidate_status", "")).strip()
    if upgrade_status:
        lines.append(f"升级态: {upgrade_status}")
    if selected.get("sample_comparison_summary"):
        lines.append(f"样本对比: {selected.get('sample_comparison_summary')}")
    governance_rule_summary = str(selected.get("governance_rule_summary", "")).strip()
    if governance_rule_summary:
        lines.append(f"规则摘要: {governance_rule_summary}")
    selection_reason = str(summary.get("selection_reason", "")).strip()
    if selection_reason:
        lines.append(f"选择原因: {selection_reason}")
    candidate_summaries = summary.get("candidate_summaries", []) or []
    if candidate_summaries:
        lines.append("候选比较:")
        for item in candidate_summaries[:4]:
            lines.append(
                "  - "
                f"{item.get('strategy_name', 'unknown')}: "
                f"oos={item.get('out_of_sample_result', 'unknown')}, "
                f"consistency={item.get('sample_consistency', 'unknown')}, "
                f"action={item.get('governance_action', 'unknown')}, "
                f"gate={item.get('primary_gate', 'n/a') or 'n/a'}, "
                f"return={float(item.get('total_return', 0.0) or 0.0):.4f}"
            )
    warnings = summary.get("validation_warnings", []) or []
    if warnings:
        lines.append("警告:")
        for item in warnings[:4]:
            lines.append(f"  - {item}")
    return "\n".join(lines)


def tool_brain_a_share_realtime_crosscheck(arguments: dict) -> str:
    """读取 A股三路实时交叉校验摘要"""
    symbol = str(arguments.get("symbol", "")).strip() or "300418"
    timeframe = str(arguments.get("timeframe", "1d")).strip() or "1d"
    try:
        payload = _trading_a_share_realtime_crosscheck(symbol=symbol, timeframe=timeframe)
    except Exception as e:
        return f"[brain_a_share_realtime_crosscheck] 查询失败: {type(e).__name__}: {e}"
    summary = payload.get("crosscheck_summary", payload) if isinstance(payload, dict) else {}

    lines = [f"[brain_a_share_realtime_crosscheck] {symbol} A股实时交叉校验摘要"]
    lines.append(f"时间框架: {summary.get('timeframe', timeframe)}")
    lines.append(f"TDX 信号: {summary.get('tdx_signal', 'unknown')}")
    lines.append(f"腾讯 qt 信号: {summary.get('tencent_signal', 'unknown')}")
    lines.append(f"WorkBuddy 信号: {summary.get('workbuddy_signal', 'unknown')}")
    lines.append(f"对齐状态: {summary.get('alignment', 'unknown')}")
    lines.append(f"研究态建议: {summary.get('recommended_action', 'unknown')}")
    lines.append(f"主风险: {summary.get('primary_risk', 'unknown')}")
    lines.append(f"实现状态: {summary.get('implementation_status', 'unknown')}")
    summary_text = str(summary.get("summary", "")).strip()
    if summary_text:
        lines.append(f"摘要: {summary_text}")
    warnings = summary.get("warnings", []) or []
    if warnings:
        lines.append("警告:")
        for item in warnings[:4]:
            lines.append(f"  - {item}")
    return "\n".join(lines)


def tool_brain_trading_research_queue_approve(arguments: dict) -> str:
    """Write a governed ResearchQueue approval result back into the mother system."""
    candidate_slug = str(arguments.get("candidate_slug", "") or "").strip()
    decision = str(arguments.get("decision", "") or "").strip().lower()
    reviewer = str(arguments.get("reviewer", "") or "").strip()
    rationale = str(arguments.get("rationale", "") or "").strip()
    follow_up_items = arguments.get("follow_up_items", []) or []
    evidence_notes = arguments.get("evidence_notes", []) or []

    if not candidate_slug:
        return "[brain_trading_research_queue_approve] 缺少 candidate_slug。"
    if decision not in {"approved", "deferred", "rejected"}:
        return "[brain_trading_research_queue_approve] decision 必须是 approved / deferred / rejected。"
    if not reviewer:
        return "[brain_trading_research_queue_approve] 缺少 reviewer。"
    if not rationale:
        return "[brain_trading_research_queue_approve] 缺少 rationale。"

    payload = {
        "candidate_slug": candidate_slug,
        "decision": decision,
        "reviewer": reviewer,
        "rationale": rationale,
        "follow_up_items": [str(item) for item in follow_up_items if str(item).strip()],
        "evidence_notes": [str(item) for item in evidence_notes if str(item).strip()],
    }
    try:
        result = _trading_confirm_research_queue_manual_approval(payload)
    except Exception as exc:
        return f"[brain_trading_research_queue_approve] 写回失败: {type(exc).__name__}: {exc}"

    module_status = (((result or {}).get("module_status_record", {}) or {}).get("status", "unknown"))
    quality_action = (((result or {}).get("module_status_record", {}) or {}).get("quality_action", "unknown"))
    approval_status = (
        (((result or {}).get("updated_skill_registry_entry", {}) or {})
         .get("metadata", {}) or {})
        .get("manual_approval_entrypoint", {})
        .get("approval_status", "unknown")
    )
    next_step = (((result or {}).get("bulletin_state_record", {}) or {}).get("next_step", ""))
    lines = [
        f"[brain_trading_research_queue_approve] 已写回 ResearchQueue 审批结果: candidate={candidate_slug}",
        f"decision={decision}",
        f"approval_status={approval_status}",
        f"module_status={module_status}",
        f"quality_action={quality_action}",
        "execution_mode=research_governance_only",
        "live_trading=disabled",
    ]
    if next_step:
        lines.append(f"next_step={next_step}")
    return "\n".join(lines)


def tool_brain_trading_research_queue_run_next_validation_slice(arguments: dict) -> str:
    """Run the next research-only validation slice for one ResearchQueue candidate."""
    candidate_slug = str(arguments.get("candidate_slug", "") or "").strip()
    if not candidate_slug:
        return "[brain_trading_research_queue_run_next_validation_slice] 缺少 candidate_slug。"

    payload = {
        "candidate_slug": candidate_slug,
        "min_approvals": int(arguments.get("min_approvals", 1) or 1),
        "top_limit": int(arguments.get("top_limit", 3) or 3),
    }
    variant_key = str(arguments.get("variant_key", "") or "").strip()
    if variant_key:
        payload["variant_key"] = variant_key

    try:
        result = _trading_research_queue_run_next_validation_slice(payload)
    except Exception as exc:
        return (
            "[brain_trading_research_queue_run_next_validation_slice] 执行失败: "
            f"{type(exc).__name__}: {exc}"
        )

    replay_payload_used = (result or {}).get("replay_payload_used", {}) or {}
    execution = (result or {}).get("validation_slice_execution", {}) or {}
    bulletin_sync = (result or {}).get("bulletin_sync", {}) or {}
    lines = [
        "[brain_trading_research_queue_run_next_validation_slice] 已执行 ResearchQueue 下一轮验证切片",
        f"candidate={candidate_slug}",
        f"variant_key={replay_payload_used.get('variant_key', variant_key or 'default')}",
        f"research_mode={bool(replay_payload_used.get('research_mode', True))}",
        f"live_trading_enabled={bool(replay_payload_used.get('live_trading_enabled', False))}",
        f"portfolio_action={result.get('portfolio_action', 'unknown')}",
        f"out_of_sample_result={result.get('out_of_sample_result', 'unknown')}",
        f"selection_status={result.get('selection_status', 'unknown')}",
        f"selection_governance_action={result.get('selection_governance_action', 'unknown')}",
        "execution_mode=research_replay_only",
    ]
    execution_plan_summary = str(execution.get("execution_plan_summary", "") or "").strip()
    if execution_plan_summary:
        lines.append(f"execution_plan={execution_plan_summary}")
    execution_outcome_summary = str(execution.get("execution_outcome_summary", "") or "").strip()
    if execution_outcome_summary:
        lines.append(f"execution_outcome={execution_outcome_summary}")
    next_step = str(((bulletin_sync.get("bulletin_state_record", {}) or {}).get("next_step", "")) or "").strip()
    if next_step:
        lines.append(f"next_step={next_step}")
    return "\n".join(lines)


# ---------- MCP Protocol ----------

SERVER_NAME = "superbrain-mcp"
SERVER_VERSION = "2.1.0"
SUPPORTED_PROTOCOL_VERSIONS = ["2025-06-18", "2024-11-05"]

RESOURCE_DEFS = {
    "superbrain://status": {
        "uri": "superbrain://status",
        "name": "superbrain_status",
        "title": "SuperBrain Status Snapshot",
        "description": "Latest v0 status snapshot from the mother system, including storage, counts, trading status, latest logs, and registry pointers.",
        "mimeType": "application/json",
    },
    "superbrain://board": {
        "uri": "superbrain://board",
        "name": "superbrain_board",
        "title": "SuperBrain Bulletin Board",
        "description": "Current bulletin board state, including completed items, in-progress work, next steps, and trading governance snapshots.",
        "mimeType": "application/json",
    },
    "superbrain://trading/status": {
        "uri": "superbrain://trading/status",
        "name": "superbrain_trading_status",
        "title": "Trading Domain Status Snapshot",
        "description": "Latest mother-system trading status, including ResearchQueue focus, probability-fusion mock visibility, and governance blockers.",
        "mimeType": "application/json",
    },
    "superbrain://trading/research-queue/latest": {
        "uri": "superbrain://trading/research-queue/latest",
        "name": "superbrain_trading_research_queue_latest",
        "title": "Latest Trading ResearchQueue Snapshot",
        "description": "Latest mother-system ResearchQueue bulletin snapshot for trading, including blockers, approvals, replay plan, and governance hints.",
        "mimeType": "application/json",
    },
    "superbrain://trading/probability-fusion/latest": {
        "uri": "superbrain://trading/probability-fusion/latest",
        "name": "superbrain_trading_probability_fusion_latest",
        "title": "Latest WorkBuddy Probability Fusion Mock Snapshot",
        "description": "Latest mother-system probability-fusion mock snapshot, including dominant direction, context alignment, and no-trade governance blockers.",
        "mimeType": "application/json",
    },
    "superbrain://governance/latest": {
        "uri": "superbrain://governance/latest",
        "name": "superbrain_governance_latest",
        "title": "Latest Mother-System Governance Snapshot",
        "description": "Latest skill registry, module status, bulletin state, and trading self-evolution references used by the mother system governance layer.",
        "mimeType": "application/json",
    },
    "superbrain://evolution/latest": {
        "uri": "superbrain://evolution/latest",
        "name": "superbrain_evolution_latest",
        "title": "Recent Self-Evolution Log",
        "description": "Recent self-evolution log entries for the mother system.",
        "mimeType": "application/json",
    },
}

RESOURCE_TEMPLATE_DEFS = {
    "superbrain://trading/research-queue/{candidate_slug}/approval-summary": {
        "uriTemplate": "superbrain://trading/research-queue/{candidate_slug}/approval-summary",
        "name": "superbrain_trading_research_queue_approval_summary",
        "title": "Trading ResearchQueue Approval Summary",
        "description": "Approval summary for one ResearchQueue candidate, including recent decisions, governance counts, and workflow status.",
        "mimeType": "application/json",
    },
    "superbrain://trading/research-queue/{candidate_slug}/watchlist": {
        "uriTemplate": "superbrain://trading/research-queue/{candidate_slug}/watchlist",
        "name": "superbrain_trading_research_queue_watchlist",
        "title": "Trading ResearchQueue Watchlist",
        "description": "Watchlist rows for one ResearchQueue candidate, including governance buckets and next review hints.",
        "mimeType": "application/json",
    },
    "superbrain://trading/research-queue/{candidate_slug}/review-agenda": {
        "uriTemplate": "superbrain://trading/research-queue/{candidate_slug}/review-agenda",
        "name": "superbrain_trading_research_queue_review_agenda",
        "title": "Trading ResearchQueue Review Agenda",
        "description": "Review agenda for one ResearchQueue candidate, grounded in the mother-system approval history and governance buckets.",
        "mimeType": "application/json",
    },
    "superbrain://trading/research-queue/{candidate_slug}/next-validation-slice": {
        "uriTemplate": "superbrain://trading/research-queue/{candidate_slug}/next-validation-slice",
        "name": "superbrain_trading_research_queue_next_validation_slice",
        "title": "Trading ResearchQueue Next Validation Slice",
        "description": "Mother-system plan for the next replay or validation slice of one ResearchQueue candidate, including blocker-focused execution hints.",
        "mimeType": "application/json",
    },
    "superbrain://trading/research-queue/{candidate_slug}/latest-validation-summary": {
        "uriTemplate": "superbrain://trading/research-queue/{candidate_slug}/latest-validation-summary",
        "name": "superbrain_trading_research_queue_latest_validation_summary",
        "title": "Trading ResearchQueue Latest Validation Summary",
        "description": "Latest validation summary for one ResearchQueue candidate, including baseline comparisons, governance hints, and replay lineage.",
        "mimeType": "application/json",
    },
}

PROMPT_DEFS = {
    "brain_decision_review": {
        "name": "brain_decision_review",
        "description": "Build a cautious decision-review prompt that forces evidence, counter-evidence, confidence, invalidation conditions, and next actions.",
        "arguments": [
            {"name": "topic", "description": "Decision topic or question.", "required": True},
            {"name": "context", "description": "Optional extra context.", "required": False},
        ],
    },
    "trading_research_review": {
        "name": "trading_research_review",
        "description": "Build a trading research review prompt grounded in A-share rules, ResearchQueue status, and no-trade governance.",
        "arguments": [
            {"name": "symbol", "description": "A-share symbol.", "required": False},
            {"name": "timeframe", "description": "Timeframe, default 1d.", "required": False},
        ],
    },
    "trading_research_queue_approval_review": {
        "name": "trading_research_queue_approval_review",
        "description": "Build an approval-aware trading ResearchQueue review prompt using the latest mother-system bulletin snapshot, blockers, readiness, and abstain rules.",
        "arguments": [
            {"name": "symbol", "description": "A-share symbol.", "required": False},
            {"name": "timeframe", "description": "Timeframe, default 1d.", "required": False},
            {"name": "candidate_slug", "description": "Optional candidate slug override.", "required": False},
        ],
    },
}

TOOLS = {
    "brain_search": {
        "name": "brain_search",
        "description": (
            "[语义知识检索 - 查「该怎么做/是什么」] "
            "搜索第二大脑知识库中的专业知识和策略。\n"
            "\n"
            "【使用规则】\n"
            "用这个: 用户问「怎么做/是什么/该怎么选」(专业技术问题)\n"
            "  例: AI视频提示词写法、影视运镜技法、A股策略、系统架构设计\n"
            "别用这个: 回忆「你们之前聊过什么」(那是 query_memory 的活)\n"
            "别用这个: 简单闲聊打招呼\n"
            "\n"
            "【优先级规则】\n"
            "- 如果 brain_search 返回的结果与 query_memory 返回的记忆矛盾，\n"
            "  以 brain_search 为准 (第二大脑是经过验证的专家知识库)"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题, 尽量用中文",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量 (1-20, 默认 5)",
                    "default": 5,
                },
                "category": {
                    "type": "string",
                    "description": "可选分类过滤: film-video(影视) / tech-ai(技术) / business(商业) / decision-lessons(决策教训) / girlfriend(AI女友)",
                },
            },
            "required": ["query"],
        },
    },
    "brain_consult": {
        "name": "brain_consult",
        "description": (
            "[决策前安全检查 - 查「有没有踩过这个坑」] "
            "查询第二大脑中与决策主题相关的历史教训、硬规则。\n"
            "\n"
            "【使用规则】\n"
            "用这个: 面临选择/方案决策/设计决策时\n"
            "  例: 选什么模型参数、用哪种架构、要不要优化这个\n"
            "别用这个: 日常闲聊、简单问答、不需要做选择的事\n"
            "\n"
            "【典型工作流】\n"
            "1. brain_consult(topic) -> 获取教训和红线\n"
            "2. 如果有高风险教训 -> 先消化教训再继续\n"
            "3. 如果无教训 -> 结合 brain_search 知识继续"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "决策主题，如 \"选择AI视频模型参数\" 或 \"设计系统架构\"",
                },
            },
            "required": ["topic"],
        },
    },
    "brain_digest": {
        "name": "brain_digest",
        "description": (
            "[知识摄入 - 把学到的东西存进长期知识库] "
            "将从对话中获得的洞察、经验教训、技术发现存入第二大脑。\n"
            "\n"
            "【使用规则】\n"
            "用这个: 对话中出现了有价值的新知识 (新发现、教训、技术要点)\n"
            "别用这个: 日常闲聊内容、临时信息\n"
            "\n"
            "【提示】写 title 时用简短总结 (如「发现: xxx」)，方便未来检索"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要摄入的文本内容",
                },
                "title": {
                    "type": "string",
                    "description": "可选标题，不填则自动生成",
                },
                "source": {
                    "type": "string",
                    "description": "来源标记，默认 maibot-mcp",
                    "default": "maibot-mcp",
                },
            },
            "required": ["text"],
        },
    },
    "brain_read": {
        "name": "brain_read",
        "description": (
            "[知识图谱探查 — 浏览知识库的结构] "
            "不传 node_id 返回全图分类统计；传入 node_id 返回该节点的关联邻居。\n"
            "用于了解知识库覆盖范围或深入探索某个节点的上下文。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "可选，节点 ID",
                },
                "depth": {
                    "type": "integer",
                    "description": "关联深度 (默认 1)",
                    "default": 1,
                },
            },
        },
    },
    "brain_trading_replay": {
        "name": "brain_trading_replay",
        "description": (
            "[交易研究态 replay 摘要] "
            "读取母系统中交易最小闭环的 replay summary，查看候选策略、治理动作、样本外结果与当前研究态结论。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "A股代码，默认 300418"},
                "timeframe": {"type": "string", "description": "时间框架，默认 1d"},
                "data_path": {"type": "string", "description": "可选，本地历史数据路径"},
            },
        },
    },
    "brain_a_share_realtime_crosscheck": {
        "name": "brain_a_share_realtime_crosscheck",
        "description": (
            "[A股三路实时交叉校验摘要] "
            "读取母系统已登记的 TDX / 腾讯 qt / WorkBuddy 三路研究态交叉校验摘要，用于实时数据连通性与方向一致性审计。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "A股代码，默认 300418"},
                "timeframe": {"type": "string", "description": "时间框架，默认 1d"},
            },
        },
    },
    "brain_trading_research_queue_approve": {
        "name": "brain_trading_research_queue_approve",
        "description": (
            "[交易 ResearchQueue 人工审批写回] "
            "把 approved / deferred / rejected 研究治理结果写回母系统，"
            "同步 LearningEntry、SelfEvolutionLog、SkillRegistry、ModuleStatusRecord 与 BulletinStateRecord。"
            "该工具只允许研究治理写回，不允许触发实盘执行。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "candidate_slug": {"type": "string", "description": "ResearchQueue 候选 slug，例如 vwap。"},
                "decision": {
                    "type": "string",
                    "description": "审批结论：approved / deferred / rejected。",
                    "enum": ["approved", "deferred", "rejected"],
                },
                "reviewer": {"type": "string", "description": "审阅人标识。"},
                "rationale": {"type": "string", "description": "审批理由。"},
                "follow_up_items": {
                    "type": "array",
                    "description": "可选，后续需要补做的事项。",
                    "items": {"type": "string"},
                },
                "evidence_notes": {
                    "type": "array",
                    "description": "可选，附带的证据说明。",
                    "items": {"type": "string"},
                },
            },
            "required": ["candidate_slug", "decision", "reviewer", "rationale"],
        },
    },
    "brain_trading_research_queue_run_next_validation_slice": {
        "name": "brain_trading_research_queue_run_next_validation_slice",
        "description": (
            "[交易 ResearchQueue 下一轮验证切片执行] "
            "调用母系统已有的 next validation slice replay 入口，执行研究态 replay 并把结果回写母系统记录链。"
            "该工具只允许 research replay，不允许开启实盘交易。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "candidate_slug": {"type": "string", "description": "ResearchQueue 候选 slug，例如 vwap。"},
                "variant_key": {
                    "type": "string",
                    "description": "可选，指定下一轮 replay 变体 key。",
                },
                "min_approvals": {
                    "type": "integer",
                    "description": "可选，最小审批计数，默认 1。",
                    "default": 1,
                },
                "top_limit": {
                    "type": "integer",
                    "description": "可选，候选上限，默认 3。",
                    "default": 3,
                },
            },
            "required": ["candidate_slug"],
        },
    },
}

TOOL_FUNCTIONS = {
    "brain_search": tool_brain_search,
    "brain_consult": tool_brain_consult,
    "brain_digest": tool_brain_digest,
    "brain_read": tool_brain_read,
    "brain_trading_replay": tool_brain_trading_replay,
    "brain_a_share_realtime_crosscheck": tool_brain_a_share_realtime_crosscheck,
    "brain_trading_research_queue_approve": tool_brain_trading_research_queue_approve,
    "brain_trading_research_queue_run_next_validation_slice": tool_brain_trading_research_queue_run_next_validation_slice,
}


def _resolve_protocol_version(params: dict) -> str:
    requested = str((params or {}).get("protocolVersion", "") or "").strip()
    if requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return SUPPORTED_PROTOCOL_VERSIONS[0]


def _read_resource(uri: str) -> dict:
    if uri == "superbrain://status":
        payload = _v0_status()
    elif uri == "superbrain://board":
        payload = _v0_board()
    elif uri == "superbrain://trading/status":
        payload = {"trading_status": _v0_status().get("trading_status", {})}
    elif uri == "superbrain://trading/research-queue/latest":
        payload = {
            "latest_trading_research_queue_bulletin_state": _v0_status().get(
                "latest_trading_research_queue_bulletin_state", {}
            )
        }
    elif uri == "superbrain://trading/probability-fusion/latest":
        payload = {
            "latest_workbuddy_probability_fusion_mock": _v0_status().get(
                "latest_workbuddy_probability_fusion_mock", {}
            )
        }
    elif uri == "superbrain://governance/latest":
        status = _v0_status()
        payload = {
            "latest_skill_registry_entry": status.get("latest_skill_registry_entry", {}),
            "latest_module_status_record": status.get("latest_module_status_record", {}),
            "latest_bulletin_state_record": status.get("latest_bulletin_state_record", {}),
            "latest_trading_skill_registry_entry": status.get("latest_trading_skill_registry_entry", {}),
            "latest_trading_module_status_record": status.get("latest_trading_module_status_record", {}),
            "latest_trading_bulletin_state_record": status.get("latest_trading_bulletin_state_record", {}),
            "latest_trading_self_evolution_log": status.get("latest_trading_self_evolution_log", {}),
        }
    elif uri == "superbrain://evolution/latest":
        payload = _v0_evolution_log(limit=10)
    elif uri.startswith("superbrain://trading/research-queue/") and uri.endswith("/approval-summary"):
        candidate_slug = uri.removeprefix("superbrain://trading/research-queue/").removesuffix("/approval-summary")
        payload = _trading_research_queue_approval_summary(candidate_slug=candidate_slug)
    elif uri.startswith("superbrain://trading/research-queue/") and uri.endswith("/watchlist"):
        candidate_slug = uri.removeprefix("superbrain://trading/research-queue/").removesuffix("/watchlist")
        payload = _trading_research_queue_watchlist(candidate_slug=candidate_slug)
    elif uri.startswith("superbrain://trading/research-queue/") and uri.endswith("/review-agenda"):
        candidate_slug = uri.removeprefix("superbrain://trading/research-queue/").removesuffix("/review-agenda")
        payload = _trading_research_queue_review_agenda(candidate_slug=candidate_slug)
    elif uri.startswith("superbrain://trading/research-queue/") and uri.endswith("/next-validation-slice"):
        candidate_slug = uri.removeprefix("superbrain://trading/research-queue/").removesuffix("/next-validation-slice")
        payload = _trading_research_queue_next_validation_slice(candidate_slug=candidate_slug)
    elif uri.startswith("superbrain://trading/research-queue/") and uri.endswith("/latest-validation-summary"):
        candidate_slug = uri.removeprefix("superbrain://trading/research-queue/").removesuffix("/latest-validation-summary")
        payload = _trading_research_queue_latest_validation_summary(candidate_slug=candidate_slug)
    else:
        raise KeyError(uri)
    return {
        "contents": [
            {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        ]
    }


def _get_prompt(name: str, arguments: dict | None = None) -> dict:
    arguments = arguments or {}
    if name == "brain_decision_review":
        topic = str(arguments.get("topic", "") or "").strip() or "unknown_topic"
        extra = str(arguments.get("context", "") or "").strip()
        text = (
            "Use SuperBrain as the mother-system evidence layer.\n"
            f"Decision topic: {topic}\n"
            f"Extra context: {extra or 'none'}\n\n"
            "Required output sections:\n"
            "1. Situation summary\n"
            "2. Supporting evidence\n"
            "3. Counter-evidence / disconfirming signals\n"
            "4. Confidence and uncertainty\n"
            "5. Invalidation conditions\n"
            "6. Risk exposure\n"
            "7. Next action / abstain option\n"
            "Do not claim certainty. If evidence is thin, explicitly abstain."
        )
    elif name == "trading_research_review":
        symbol = str(arguments.get("symbol", "300418") or "300418").strip() or "300418"
        timeframe = str(arguments.get("timeframe", "1d") or "1d").strip() or "1d"
        text = (
            "Use SuperBrain trading governance, not standalone chart intuition.\n"
            f"Symbol: {symbol}\n"
            f"Timeframe: {timeframe}\n\n"
            "Required output sections:\n"
            "1. A-share regime constraints (T+1 / time window / no-trade gates)\n"
            "2. Replay / ResearchQueue status\n"
            "3. Sample in / sample out comparison\n"
            "4. Probability-style judgment (watch / wait / no_trade unless higher gate clears)\n"
            "5. Evidence, counter-evidence, blocker list\n"
            "6. What must be true before promotion\n"
            "Never convert Experimental or Interface outputs into live-trading conclusions."
        )
    elif name == "trading_research_queue_approval_review":
        symbol = str(arguments.get("symbol", "300418") or "300418").strip() or "300418"
        timeframe = str(arguments.get("timeframe", "1d") or "1d").strip() or "1d"
        status = _v0_status()
        snapshot = dict(status.get("latest_trading_research_queue_bulletin_state", {}) or {})
        candidate_slug = str(
            arguments.get("candidate_slug", "") or snapshot.get("candidate_slug", "") or "unknown_candidate"
        ).strip() or "unknown_candidate"
        approval_status = str(snapshot.get("approval_status", "not_reported") or "not_reported")
        can_submit_now = bool(snapshot.get("can_submit_now", False))
        missing_keys = list(snapshot.get("missing_keys", []) or [])
        ready_count = int(snapshot.get("ready_count", 0) or 0)
        total_count = int(snapshot.get("total_count", 0) or 0)
        primary_blocker = str(snapshot.get("primary_blocker", "") or "unknown")
        queue_recommendation = str(snapshot.get("queue_recommendation", "") or "unknown")
        out_of_sample_result = str(snapshot.get("out_of_sample_result", "") or "unknown")
        text = (
            "Use the mother-system ResearchQueue governance snapshot before any promotion judgment.\n"
            f"Symbol: {symbol}\n"
            f"Timeframe: {timeframe}\n"
            f"Candidate: {candidate_slug}\n"
            f"Approval status: {approval_status}\n"
            f"Can submit now: {can_submit_now}\n"
            f"Readiness: {ready_count}/{total_count}\n"
            f"Primary blocker: {primary_blocker}\n"
            f"Queue recommendation: {queue_recommendation}\n"
            f"Out-of-sample result: {out_of_sample_result}\n"
            f"Missing keys: {', '.join(missing_keys) if missing_keys else 'none'}\n\n"
            "Required output sections:\n"
            "1. Current governance state\n"
            "2. Evidence already present\n"
            "3. Missing evidence / blockers\n"
            "4. Whether approval is justified now\n"
            "5. Why abstain, defer, freeze, or keep Experimental if not ready\n"
            "6. Exact next data or replay step needed\n"
            "Never convert pending_evidence or blocked ResearchQueue candidates into live-trading approval."
        )
    else:
        raise KeyError(name)
    prompt_def = PROMPT_DEFS[name]
    return {
        "name": name,
        "description": prompt_def.get("description", ""),
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": text,
                },
            }
        ],
    }


def dispatch_request(req: dict) -> dict | None:
    req_id = req.get("id", 0)
    method = req.get("method", "")
    params = req.get("params", {}) or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": _resolve_protocol_version(params),
                "capabilities": {
                    "tools": {},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
                "instructions": (
                    "SuperBrain MCP exposes the mother-system knowledge base, bulletin state, trading governance "
                    "snapshots, and ingestion/search tools. Treat trading outputs as research-only unless explicit "
                    "promotion gates are cleared."
                ),
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": list(TOOLS.values())}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {}) or {}
        if tool_name in TOOL_FUNCTIONS:
            try:
                result = TOOL_FUNCTIONS[tool_name](arguments)
            except Exception as e:
                result = f"[{tool_name}] execution error: {type(e).__name__}: {e}"
                logger.exception("Tool %s failed", tool_name)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": result}]},
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True},
        }

    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": list(RESOURCE_DEFS.values())}}

    if method == "resources/templates/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"resourceTemplates": list(RESOURCE_TEMPLATE_DEFS.values())},
        }

    if method == "resources/read":
        uri = str(params.get("uri", "") or "").strip()
        try:
            result = _read_resource(uri)
        except KeyError:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": f"Unknown resource: {uri}"},
            }
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": list(PROMPT_DEFS.values())}}

    if method == "prompts/get":
        name = str(params.get("name", "") or "").strip()
        arguments = params.get("arguments", {}) or {}
        try:
            result = _get_prompt(name, arguments)
        except KeyError:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": f"Unknown prompt: {name}"},
            }
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/capabilities":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"capabilities": {"tools": {}, "resources": {}, "prompts": {}}},
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def handle_request():
    """MCP stdio 协议主循环"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        resp = dispatch_request(req)
        if resp is not None:
            respond(resp)


def respond(resp: dict):
    """发送 JSON-RPC 响应"""
    try:
        print(json.dumps(resp, ensure_ascii=False), flush=True)
    except BrokenPipeError:
        sys.exit(0)


if __name__ == "__main__":
    # 启动时做一次健康检查
    healthy = _brain_healthy()
    logger.info("Second brain health check: %s", "OK" if healthy else "FAIL")
    handle_request()
