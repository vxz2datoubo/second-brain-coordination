"""Normalize daily market/theme notes into finance daily-items JSONL.

Use this when the source is messy: copied news, after-market review notes,
Markdown, CSV exports, JSON, or JSONL. The output schema is the one consumed by
finance_daily_report.py and finance_daily_pipeline.py:
{"title": "...", "text": "...", "date": "YYYY-MM-DD", "source": "..."}
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.finance_advisor import DEFAULT_THEMES, LIFECYCLE_KEYWORDS, analyze_hot_themes  # noqa: E402


TITLE_KEYS = ("title", "标题", "headline", "name", "名称", "subject")
TEXT_KEYS = ("text", "正文", "content", "body", "summary", "摘要", "description", "描述", "note", "notes")
DATE_KEYS = ("date", "日期", "time", "datetime", "发布时间")
SOURCE_KEYS = ("source", "来源", "origin", "channel")


def pick(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return str(row[key]).strip()
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def infer_title(text: str, fallback: str = "market note") -> str:
    first = compact_text(text).split("。", 1)[0].split(".", 1)[0]
    return (first[:60] or fallback).strip()


def item_id(title: str, text: str, date: str, source: str) -> str:
    raw = f"{date}\n{source}\n{compact_text(title)}\n{compact_text(text)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def theme_metadata(title: str, text: str) -> dict:
    haystack = f"{title} {text}".lower()
    matched_themes = []
    for theme, keywords in DEFAULT_THEMES.items():
        hits = [kw for kw in keywords if str(kw).lower() in haystack]
        if hits:
            matched_themes.append({"theme": theme, "keywords": hits[:8]})
    lifecycle_hits = {}
    for phase, keywords in LIFECYCLE_KEYWORDS.items():
        hits = [kw for kw in keywords if str(kw).lower() in haystack]
        if hits:
            lifecycle_hits[phase] = hits[:8]
    return {"matched_themes": matched_themes, "lifecycle_hits": lifecycle_hits}


def normalize_item(raw: dict[str, Any], default_date: str, default_source: str, source_path: str = "") -> dict | None:
    title = compact_text(pick(raw, TITLE_KEYS))
    text = compact_text(pick(raw, TEXT_KEYS))
    date = compact_text(pick(raw, DATE_KEYS))[:10] or default_date
    source = compact_text(pick(raw, SOURCE_KEYS)) or default_source

    if not text:
        parts = []
        for key, value in raw.items():
            if value in (None, ""):
                continue
            parts.append(f"{key}: {value}")
        text = compact_text("；".join(parts))
    if not title:
        title = infer_title(text, Path(source_path).stem if source_path else "market note")
    if not text:
        return None

    metadata = dict(raw.get("metadata") or {}) if isinstance(raw.get("metadata"), dict) else {}
    metadata.update(theme_metadata(title, text))
    if source_path:
        metadata["source_path"] = source_path
    normalized = {
        "title": title,
        "text": text,
        "date": date,
        "source": source,
        "metadata": metadata,
    }
    normalized["id"] = item_id(title, text, date, source)
    return normalized


def parse_json_file(path: Path, default_date: str, default_source: str) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict) and isinstance(data.get("items"), list):
        rows = data["items"]
    elif isinstance(data, dict):
        rows = [data]
    else:
        raise ValueError(f"{path} JSON must be object, list, or object with items")
    out = []
    for row in rows:
        if isinstance(row, dict):
            item = normalize_item(row, default_date, default_source, str(path))
            if item:
                out.append(item)
    return out


def parse_jsonl_file(path: Path, default_date: str, default_source: str) -> list[dict]:
    out = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no} invalid JSON: {exc}") from exc
            if isinstance(raw, dict):
                item = normalize_item(raw, default_date, default_source, str(path))
                if item:
                    out.append(item)
    return out


def parse_csv_file(path: Path, default_date: str, default_source: str) -> list[dict]:
    out = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = normalize_item(dict(row), default_date, default_source, str(path))
            if item:
                out.append(item)
    return out


def split_event_sentences(text: str, min_chars: int) -> list[str]:
    parts = [compact_text(part) for part in re.split(r"(?<=[。！？!?；;])\s*", text)]
    parts = [part for part in parts if len(part) >= min_chars]
    return parts or ([compact_text(text)] if len(compact_text(text)) >= min_chars else [])


def parse_text_file(path: Path, default_date: str, default_source: str, min_chars: int, split_sentences: bool) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    return parse_text_blob(text, default_date, default_source, min_chars, str(path), split_sentences)


def parse_text_blob(
    text: str,
    default_date: str,
    default_source: str,
    min_chars: int,
    source_path: str = "",
    split_sentences: bool = True,
) -> list[dict]:
    chunks = []
    current_title = ""
    current_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current_lines:
                chunks.append((current_title, "\n".join(current_lines)))
                current_lines = []
            continue
        heading = re.match(r"^#{1,4}\s+(.+)$", line)
        if heading:
            if current_lines:
                chunks.append((current_title, "\n".join(current_lines)))
                current_lines = []
            current_title = heading.group(1).strip()
            continue
        current_lines.append(line)
    if current_lines:
        chunks.append((current_title, "\n".join(current_lines)))

    if not chunks and compact_text(text):
        chunks = [("", text)]

    out = []
    for idx, (title, body) in enumerate(chunks, 1):
        body = compact_text(body)
        bodies = split_event_sentences(body, min_chars) if split_sentences else [body]
        for sub_idx, event_text in enumerate(bodies, 1):
            if len(event_text) < min_chars:
                continue
            raw = {
                "title": title or infer_title(event_text, f"market note {idx}"),
                "text": event_text,
                "date": default_date,
                "source": default_source,
                "metadata": {"chunk_index": idx, "sentence_index": sub_idx},
            }
            item = normalize_item(raw, default_date, default_source, source_path)
            if item:
                out.append(item)
    return out


def parse_input(path: Path, default_date: str, default_source: str, min_chars: int, split_sentences: bool = True) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return parse_jsonl_file(path, default_date, default_source)
    if suffix == ".json":
        return parse_json_file(path, default_date, default_source)
    if suffix == ".csv":
        return parse_csv_file(path, default_date, default_source)
    return parse_text_file(path, default_date, default_source, min_chars, split_sentences)


def dedupe_items(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for item in items:
        key = item.get("id") or item_id(item.get("title", ""), item.get("text", ""), item.get("date", ""), item.get("source", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def render_markdown(items: list[dict], output_path: Path, report_date: str) -> str:
    trends = analyze_hot_themes(items, top_k=10)
    lines = [
        f"# 题材事件摄入报告 - {report_date}",
        "",
        "用途：检查今日新闻/复盘/板块摘要是否已经标准化为每日题材 JSONL。",
        "",
        "## 总览",
        "",
        f"- 输出文件: `{output_path}`",
        f"- 事件条数: {len(items)}",
        f"- 命中题材数: {len(trends.get('themes', []))}",
        "",
        "## 命中题材",
        "",
        "| 排名 | 题材 | 阶段 | 风险 | 热度 | 提及 | 建议 |",
        "|---:|---|---|---|---:|---:|---|",
    ]
    for rank, theme in enumerate(trends.get("themes", []), 1):
        lines.append(
            f"| {rank} | {theme['theme']} | {theme.get('lifecycle', '')} | {theme.get('risk_level', '')} | "
            f"{theme.get('score', 0)} | {theme['mentions']} | {str(theme['suggestion']).replace('|', ' ')} |"
        )
    if not trends.get("themes"):
        lines.append("| - | - | - | - | 0 | 0 | 未命中内置题材关键词 |")
    lines.extend(["", "## 事件样例", ""])
    for item in items[:10]:
        matched = ", ".join(m["theme"] for m in item.get("metadata", {}).get("matched_themes", [])) or "未命中"
        lines.append(f"- {item.get('date')} [{item.get('source')}] {item.get('title')} ｜ {matched}")
    return "\n".join(lines) + "\n"


def write_jsonl(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize finance theme/news notes into daily-items JSONL.")
    parser.add_argument("--input", nargs="*", default=[], help="Input files: txt/md/json/jsonl/csv")
    parser.add_argument("--text", default="", help="Inline text to ingest")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--source", default="manual-theme-ingest")
    parser.add_argument("--min-chars", type=int, default=12)
    parser.add_argument("--no-split-sentences", action="store_true", help="Keep text paragraphs as one event")
    parser.add_argument("--output", default="")
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    items = []
    for raw_path in args.input:
        items.extend(parse_input(Path(raw_path), args.date, args.source, args.min_chars, not args.no_split_sentences))
    if args.text:
        items.extend(parse_text_blob(args.text, args.date, args.source, args.min_chars, split_sentences=not args.no_split_sentences))
    items = dedupe_items(items)
    if not items:
        print(json.dumps({"success": False, "error": "no valid items"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    output = Path(args.output) if args.output else ROOT / "qclaw-output" / f"finance-daily-items-{args.date}.jsonl"
    report = Path(args.report) if args.report else output.with_name(output.stem + "-ingest-report.md")
    write_jsonl(output, items)
    report.write_text(render_markdown(items, output, args.date), encoding="utf-8")
    trends = analyze_hot_themes(items, top_k=10)
    print(json.dumps({
        "success": True,
        "output": str(output),
        "report": str(report),
        "count": len(items),
        "themes": [row["theme"] for row in trends.get("themes", [])[:5]],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
