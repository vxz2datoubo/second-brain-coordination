# 第二大脑认知系统启动器
# 直接运行此文件，自动加载所有模块

import sys
import os

# 添加项目路径
sys.path.insert(0, "F:/aidanao")
os.chdir("F:/aidanao")

print("=" * 60)
print("第二大脑认知系统")
print("=" * 60)

# 1. 加载核心模块
from core.codex_brain_bridge import CodexBrain, get_codex_brain

print("\n初始化中...")

try:
    brain = get_codex_brain()
    print("✅ 第二大脑加载成功!")
except Exception as e:
    print(f"❌ 加载失败: {e}")
    sys.exit(1)

print("\n可用功能:")
print("  brain.consult(topic)           - 咨询问题")
print("  brain.pre_decision_check(action) - 决策前检查")
print("  brain.cross_think(topic)      - 跨领域联想")
print("  brain.check_rules(action)     - 规则检查")
print("  brain.make_decision(...)      - 做出决策")
print("  brain.learn(...)              - 记录学习")
print("  brain.get_wisdom()            - 获取历史智慧")
print("  brain.get_stats()             - 获取统计")

print("\n示例:")
print("  brain.consult('AI对金融的影响')")
print("  brain.pre_decision_check('追高买入')")
print("  brain.cross_think('心理学与投资')")

print("\n" + "=" * 60)
print("输入命令开始使用，或按 Ctrl+C 退出")
print("=" * 60)

# 交互模式
while True:
    try:
        cmd = input("\n> ").strip()
        if not cmd:
            continue
        if cmd.lower() in ["exit", "quit", "q"]:
            break
        
        # 简单命令处理
        if cmd.startswith("consult "):
            topic = cmd[8:]
            result = brain.consult(topic)
            print(f"\n置信度: {result['confidence']:.0%}")
            print(f"警告: {result['warnings']}")
            print(f"盲点: {result['reasoning_gaps']}")
            
        elif cmd.startswith("check "):
            action = cmd[6:]
            result = brain.check_rules(action)
            print(f"\n允许: {result['allowed']}")
            print(f"检查: {result['checks']}")
            print(f"警告: {result['warnings']}")
            
        elif cmd.startswith("cross "):
            topic = cmd[6:]
            result = brain.cross_think(topic)
            print(f"\n发现领域: {result['discovered_domains']}")
            print(f"洞察: {result['insights']}")
            
        elif cmd == "stats":
            stats = brain.get_stats()
            for k, v in stats.items():
                print(f"  {k}: {v}")
                
        elif cmd == "wisdom":
            items = brain.get_wisdom()
            for item in items[:5]:
                print(f"[{item['type']}] {item['content']}")
                
        elif cmd == "help":
            print("\n可用命令:")
            print("  consult <问题>    - 咨询问题")
            print("  check <行动>      - 检查行动规则")
            print("  cross <主题>      - 跨领域思考")
            print("  stats             - 查看统计")
            print("  wisdom            - 查看历史智慧")
            print("  help              - 显示帮助")
            print("  exit              - 退出")
            
        else:
            print("未知命令，输入 'help' 查看帮助")
            
    except KeyboardInterrupt:
        print("\n\n退出...")
        break
    except Exception as e:
        print(f"错误: {e}")
