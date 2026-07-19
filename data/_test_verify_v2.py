import sys, traceback
sys.path.insert(0, ".")
from core.graph import KnowledgeGraph
from core.digest import TextDigester
from core.memory import MemoryEngine
from core.memory_health import MemoryHealthManager
from core.self_verify import SelfVerify
from pathlib import Path

DATA = Path("data")
try:
    g = KnowledgeGraph(DATA)
    d = TextDigester(g, DATA)
    m = MemoryEngine(DATA)
    h = MemoryHealthManager(g, m, DATA)
    sv = SelfVerify(g, m, h, DATA)
    print("Init OK")
    result = sv.stats(v2=True)
    print("stats(v2=True) OK:")
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    result2 = sv.verify_all_nodes()
    print("\nverify_all_nodes() OK:")
    print(json.dumps(result2, ensure_ascii=False, indent=2))
except Exception as e:
    traceback.print_exc()
