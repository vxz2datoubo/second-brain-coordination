import sys; sys.path.insert(0, 'F:/AiGirl/QQSafeChat')
from core.sakura_brain_bridge import SakuraBrainBridge

bridge = SakuraBrainBridge()

print("=== search didi ===")
memories = bridge.remember("迪迪 第二大脑 QClaw")
for m in memories[:3]:
    print(f"  [{m['category']}] {m['title'][:40]} ({m['score']:.0f})")

print()
print("=== search aivideo ===")
memories2 = bridge.remember("AI视频 提示词 王家卫")
for m in memories2[:3]:
    print(f"  [{m['category']}] {m['title'][:40]} ({m['score']:.0f})")

print()
print("=== mood ===")
mood = bridge.mood_from_diary()
for k, v in sorted(mood.items(), key=lambda x: -x[1])[:5]:
    print(f"  {k}: {v}")

print()
print("=== lessons ===")
lessons = bridge.read_lessons()
for l in lessons[:3]:
    print(f"  {l['title'][:40]}")

print()
print("=== context ===")
ctx = bridge.build_context("我今天写AI视频prompt好累")
print(ctx[:400])

print()
print("bridge: OK")
