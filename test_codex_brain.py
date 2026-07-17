import sys
sys.path.insert(0, "F:/aidanao")
from core.codex_brain_bridge import CodexBrain

brain = CodexBrain(mode="local")

# Test consult
print("=== Consult Test ===")
result = brain.consult("追高买入风险")
print("Confidence:", result["confidence"])
print("Warnings:", result["warnings"])
print("Blind spots:", result["reasoning_gaps"])

# Test pre-decision check
print("\n=== Pre-Decision Check ===")
check = brain.pre_decision_check("追高买入300418")
print("Risk level:", check["risk_level"])
print("Warnings:", check["warnings"])

# Test rules check
print("\n=== Rules Check ===")
rules = brain.check_rules("开盘30分钟内追高买入")
print("Allowed:", rules["allowed"])
print("Checks:", rules["checks"])

# Test cross-think
print("\n=== Cross-Domain Think ===")
cross = brain.cross_think("AI技术与投资")
print("Domains:", cross["discovered_domains"])
print("Insights:", cross["insights"])

# Test decision
print("\n=== Decision Test ===")
decision = brain.make_decision("test", {"topic": "test"}, ["A", "B", "C"])
print("Decision ID:", decision["decision_id"])
print("Chosen:", decision["chosen"])

# Test learn
print("\n=== Learn ===")
learn = brain.learn(decision["decision_id"], "Success", True, ["Test lesson"])
print("Accuracy:", learn["accuracy"])

# Get stats
print("\n=== Stats ===")
stats = brain.get_stats()
for k, v in stats.items():
    print(f"  {k}: {v}")

print("\nAll tests passed!")
