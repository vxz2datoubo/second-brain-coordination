# wisdom_brain_api.py
# 因果智慧大脑 - API接口
# 版本: v1.0 | 日期: 2026-07-07

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
sys.path.insert(0, str(Path(__file__).parent))

from atomizer import WisdomAtomizer
from retriever import WisdomRetriever
import json

def learn_knowledge(
    title: str,
    content: str,
    category: str,
    importance: str = "中",
    source: str = "用户输入",
    tags: list = None,
    causal_chain: list = None
) -> dict:
    """学习新知识"""
    atomizer = WisdomAtomizer()
    node = atomizer.atomize(
        title=title,
        content=content,
        category=category,
        importance=importance,
        source=source,
        tags=tags,
        causal_chain=causal_chain
    )
    return {
        "success": True,
        "node_id": node["id"],
        "stats": atomizer.get_stats()
    }

def recall_knowledge(
    query: str,
    category: str = None,
    tags: list = None,
    limit: int = 5
) -> dict:
    """检索知识"""
    retriever = WisdomRetriever()
    results = retriever.retrieve(
        query=query,
        category=category,
        tags=tags,
        limit=limit
    )
    return {
        "query": query,
        "count": len(results),
        "results": [
            {
                "id": r["node"]["id"],
                "title": r["node"]["title"],
                "score": r["score"],
                "summary": r["node"].get("summary", "")[:100],
                "tags": r["node"].get("tags", [])[:5]
            }
            for r in results
        ]
    }

def get_brain_stats() -> dict:
    """获取大脑统计"""
    atomizer = WisdomAtomizer()
    return atomizer.get_stats()

if __name__ == "__main__":
    # 测试
    print("=== 因果智慧大脑 API ===")
    print(f"知识库统计: {get_brain_stats()}")
