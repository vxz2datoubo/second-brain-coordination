"""
资产钱包管理器 — 存储、查询、分类管理所有API tokens/账号/订阅
集成到第二大脑知识图谱 (localhost:8766)
"""
import json
import os
import hashlib
import time
from datetime import datetime

WALLET_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'wallet.json')
KB_API = "http://localhost:8766"

def _load():
    with open(WALLET_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def _save(data):
    with open(WALLET_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_asset(name, category, value, notes="", expires=None, tags=None):
    """添加资产到钱包。tags 为可模糊搜索的关键词列表(自动归类用)。"""
    wallet = _load()
    
    # Generate ID
    ts = str(int(time.time() * 1000000))
    aid = hashlib.md5(f"{name}{category}{ts}".encode()).hexdigest()[:8]
    
    # 计算下一个序号(时间序列)
    seq = 1
    for a in wallet["assets"].values():
        if a.get("seq", 0) >= seq:
            seq = a["seq"] + 1

    asset = {
        "id": aid,
        "seq": seq,
        "name": name,
        "category": category,
        "value": value,
        "notes": notes,
        "tags": tags or [],
        "expires": expires,
        "created_at": datetime.now().isoformat(),
        "last_used": None
    }
    
    wallet["assets"][aid] = asset
    # 更新时间线索引(按存入先后)
    meta = wallet.setdefault("meta", {})
    tl = meta.setdefault("timeline", [])
    tl.append({
        "seq": seq,
        "id": aid,
        "name": name,
        "category": category,
        "created_at": asset["created_at"]
    })
    tl.sort(key=lambda x: x["seq"])
    _save(wallet)
    print(f"✅ 已存入(序号#{seq}): [{category}] {name} (id={aid})")
    return aid

def list_assets(category=None):
    """列出资产"""
    wallet = _load()
    assets = list(wallet["assets"].values())
    if category:
        assets = [a for a in assets if a["category"] == category]
    assets.sort(key=lambda a: a.get("seq", 0))  # 时间顺序
    
    cat_names = {k: v["name"] for k, v in wallet["categories"].items()}
    
    if not assets:
        print("📭 钱包为空")
        return []
    
    print(f"\n{'='*60}")
    print(f"  💼 资产钱包 ({len(assets)}项, 按时间顺序)")
    print(f"{'='*60}")
    
    by_cat = {}
    for a in assets:
        cat = a["category"]
        if cat not in by_cat: by_cat[cat] = []
        by_cat[cat].append(a)
    
    for cat, items in by_cat.items():
        icon = wallet["categories"].get(cat, {}).get("icon", "📦")
        name = wallet["categories"].get(cat, {}).get("name", cat)
        print(f"\n  {icon} {name} ({len(items)}项):")
        for item in items:
            exp = f" ⏰到期:{item['expires']}" if item.get('expires') else ""
            seq = item.get('seq', '?')
            print(f"    [#{seq}] [{item['id']}] {item['name']}{exp}")
            if item.get('tags'):
                print(f"         🏷️ {', '.join(item['tags'])}")
            if item.get('notes'):
                print(f"         {item['notes'][:60]}")
    
    return by_cat

def list_timeline():
    """按时间顺序(存入先后)列出全部资产，不按分类分组"""
    wallet = _load()
    tl = wallet.get("meta", {}).get("timeline", [])
    assets = wallet["assets"]
    cat_names = {k: v["name"] for k, v in wallet["categories"].items()}
    if not tl:
        print("📭 钱包为空")
        return []
    print(f"\n{'='*60}")
    print(f"  🕒 资产时间线 (按存入先后, 共{len(tl)}项)")
    print(f"{'='*60}")
    for i, e in enumerate(tl, 1):
        a = assets.get(e["id"], {})
        icon = wallet["categories"].get(e["category"], {}).get("icon", "📦")
        cname = cat_names.get(e["category"], e["category"])
        exp = f" ⏰到期:{a.get('expires')}" if a.get('expires') else ""
        print(f"\n  [{i}] {icon} {e['name']}")
        print(f"      类型:{cname} | 存入:{e['created_at']}{exp}")
        if a.get('notes'):
            print(f"      备注:{a['notes'][:60]}")
    return tl

def get_asset(aid):
    """获取单个资产"""
    wallet = _load()
    asset = wallet["assets"].get(aid)
    if not asset:
        print(f"❌ 未找到资产: {aid}")
        return None
    asset["last_used"] = datetime.now().isoformat()
    _save(wallet)
    return asset

def remove_asset(aid):
    """删除资产"""
    wallet = _load()
    if aid in wallet["assets"]:
        a = wallet["assets"].pop(aid)
        _save(wallet)
        print(f"🗑️ 已删除: {a['name']}")
        return True
    print(f"❌ 未找到: {aid}")
    return False

def search_assets(query):
    """模糊搜索资产：覆盖 名称+备注+分类+标签"""
    wallet = _load()
    q = query.lower()
    cat_names = {k: v["name"] for k, v in wallet["categories"].items()}
    results = []
    for a in wallet["assets"].values():
        hay = " ".join([
            a["name"].lower(),
            a.get("notes", "").lower(),
            a["category"].lower(),
            cat_names.get(a["category"], "").lower(),
            " ".join(a.get("tags", [])).lower()
        ])
        if q in hay:
            results.append(a)
    if not results:
        print(f"🔍 未找到匹配: {query}")
        return []
    print(f"\n🔍 模糊搜索 '{query}' → {len(results)} 项:")
    for a in results:
        print(f"  [{a['id']}] {a['category']}: {a['name']}")
        if a.get('tags'):
            print(f"       🏷️ {', '.join(a['tags'])}")
    return results

# CLI
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python pocket.py add|list|get|search|remove [args]")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "add":
        if len(sys.argv) < 5:
            print("用法: python pocket.py add <名称> <分类> <值> [备注] [到期日] [标签逗号分隔]")
        else:
            name = sys.argv[2]
            cat = sys.argv[3]
            val = sys.argv[4]
            notes = sys.argv[5] if len(sys.argv) > 5 else ""
            expires = sys.argv[6] if len(sys.argv) > 6 else None
            tags = sys.argv[7].split(",") if len(sys.argv) > 7 else None
            add_asset(name, cat, val, notes, expires, tags)
    
    elif cmd == "list":
        cat = sys.argv[2] if len(sys.argv) > 2 else None
        list_assets(cat)

    elif cmd == "timeline":
        list_timeline()
    
    elif cmd == "get":
        get_asset(sys.argv[2]) if len(sys.argv) > 2 else print("需要资产ID")
    
    elif cmd == "search":
        search_assets(sys.argv[2]) if len(sys.argv) > 2 else print("需要搜索词")
    
    elif cmd == "remove":
        remove_asset(sys.argv[2]) if len(sys.argv) > 2 else print("需要资产ID")
