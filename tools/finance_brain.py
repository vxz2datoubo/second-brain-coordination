"""Second Brain helpers for finance tools.

The finance pipeline can generate reports repeatedly while testing or rerunning
a trading day. These helpers keep ingestion idempotent by checking for an exact
title/source match before posting a new node.
"""
from __future__ import annotations

import json
import urllib.request


def _post_json(url: str, payload: dict, timeout: int = 20) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_brain(title: str, brain_url: str, top_k: int = 10) -> list[dict]:
    result = _post_json(
        f"{brain_url.rstrip('/')}/api/retrieve/search",
        {"query": title, "top_k": top_k},
        timeout=10,
    )
    return result.get("results", [])


def find_existing_report(title: str, source: str, brain_url: str) -> dict | None:
    for item in search_brain(title, brain_url):
        if item.get("title") == title and item.get("source") == source:
            return item
    return None


def ingest_report_once(report: str, title: str, source: str, brain_url: str) -> dict:
    existing = find_existing_report(title, source, brain_url)
    if existing:
        return {
            "success": True,
            "skipped": True,
            "reason": "duplicate-title-source",
            "node": existing,
        }
    result = _post_json(
        f"{brain_url.rstrip('/')}/api/digest/text",
        {"title": title, "text": report, "source": source},
        timeout=20,
    )
    result["skipped"] = False
    return result
