import re

path = r"F:\aidanao\daytrade_system\medallion\signal_pipeline.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

matches = re.findall(r'\s+if .* in f\d+\.signals:', content)
print("要修复的行:")
for m in matches:
    print(f"  {m}")

replacements = [
    ('if "卖" in f1.signals:', 'if any("卖" in s for s in f1.signals):'),
    ('elif "买" in f1.signals:', 'elif any("买" in s for s in f1.signals):'),
    ('if "卖" in f2.signals:', 'if any("卖" in s for s in f2.signals):'),
    ('elif "买" in f2.signals:', 'elif any("买" in s for s in f2.signals):'),
    ('if "卖" in f3.signals:', 'if any("卖" in s for s in f3.signals):'),
    ('elif "买" in f3.signals:', 'elif any("买" in s for s in f3.signals):'),
    ('if "卖" in f4.signals:', 'if any("卖" in s for s in f4.signals):'),
    ('if "卖" in f5.signals:', 'if any("卖" in s for s in f5.signals):'),
    ('if "卖" in f6.signals:', 'if any("卖" in s for s in f6.signals):'),
    ('elif "买" in f6.signals:', 'elif any("买" in s for s in f6.signals):'),
]

count = 0
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        count += 1
        print(f"[OK] {old}")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print(f"\nDone: {count}/10 replaced")
