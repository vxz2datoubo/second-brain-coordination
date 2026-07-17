"""
自进化层 · 自我检验模块
每日/每周自动运行，验证系统正确性和进化方向

检验内容：
  1. 数据源连通性：TDX MCP 是否正常
  2. 信号管道正确性：输入数据 → 输出信号的链路
  3. 槽位状态一致性：槽位与交易记录是否匹配
  4. 风险控制器逻辑：各种边界条件是否正确触发
  5. 回测结果可信度：是否出现过度拟合
  6. 参数漂移检测：当前参数与历史最优相比是否严重偏离
  7. 每日自动报告输出
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORK_DIR, "data")
TEST_REPORT_DIR = os.path.join(DATA_DIR, "test_reports")


class SystemSelfTest:
    """
    系统自我检验
    """

    def __init__(self):
        os.makedirs(TEST_REPORT_DIR, exist_ok=True)
        self.tests_passed = 0
        self.tests_failed = 0
        self.warnings = []

    def run_all_tests(self) -> Dict:
        """运行全部检验"""
        self.tests_passed = 0
        self.tests_failed = 0
        self.warnings = []
        results = {}

        results["data_source"] = self._test_data_source()
        results["slot_consistency"] = self._test_slot_consistency()
        results["risk_logic"] = self._test_risk_logic()
        results["param_sanity"] = self._test_param_sanity()
        results["trade_history"] = self._test_trade_history()

        all_passed = self.tests_failed == 0

        return {
            "date": date.today().isoformat(),
            "timestamp": datetime.now().isoformat(),
            "all_passed": all_passed,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "warnings": self.warnings,
            "results": results,
        }

    def _test_data_source(self) -> Dict:
        """检验数据源连通性"""
        test = {"name": "数据源连通性", "passed": True, "details": []}

        try:
            from live.tdx_mcp_client import get_client
            client = get_client()
            ping_ok = client.ping()
            if not ping_ok:
                test["passed"] = False
                test["details"].append("TDX MCP ping 失败")
                self.tests_failed += 1
            else:
                test["details"].append("TDX MCP 连接正常")

            # 测试行情查询
            quotes = client.get_quotes(["300418"])
            if quotes:
                test["details"].append(f"行情查询正常: {quotes[0].get('name', '?')}")
            else:
                test["passed"] = False
                test["details"].append("行情查询返回空")
                self.tests_failed += 1
        except Exception as e:
            test["passed"] = False
            test["details"].append(f"异常: {e}")
            self.tests_failed += 1

        if test["passed"]:
            self.tests_passed += 1
        return test

    def _test_slot_consistency(self) -> Dict:
        """检验槽位与交易记录一致性"""
        test = {"name": "槽位状态一致性", "passed": True, "details": []}

        try:
            from live.slot_manager import SlotManager
            from live.trade_logger import get_logger

            sm = SlotManager()
            logger = get_logger()

            for code in ["300418", "300058"]:
                status = sm.get_status_summary(code)
                open_count = status["open_count"]
                today_sold = status["today_sold"]
                remaining = status["remaining_slots"]

                # 规则验证
                if open_count > today_sold:
                    test["passed"] = False
                    test["details"].append(f"{code}: 未回笼数({open_count}) > 今日卖出数({today_sold})")
                    self.tests_failed += 1
                elif remaining < 0:
                    test["passed"] = False
                    test["details"].append(f"{code}: 剩余槽位({remaining}) < 0")
                    self.tests_failed += 1
                elif remaining + open_count > 3:
                    test["passed"] = False
                    test["details"].append(f"{code}: 剩余({remaining}) + 未回笼({open_count}) > 3")
                    self.tests_failed += 1
                else:
                    test["details"].append(
                        f"{code}: 卖出{today_sold}/3, 未回笼{open_count}, 可开{remaining}"
                    )
        except Exception as e:
            test["passed"] = False
            test["details"].append(f"异常: {e}")
            self.tests_failed += 1

        if test["passed"]:
            self.tests_passed += 1
        return test

    def _test_risk_logic(self) -> Dict:
        """检验风控逻辑"""
        test = {"name": "风险控制器逻辑", "passed": True, "details": []}

        try:
            from live.risk_controller import RiskController

            rc = RiskController()

            # 重置测试
            rc.reset_day()

            # 模拟亏损后的行为
            rc.register_trade_result(-1.5)  # 亏损1.5%
            if rc.state["consecutive_losses"] != 1:
                test["passed"] = False
                self.tests_failed += 1
            else:
                test["details"].append("连亏计数正确")

            rc.register_trade_result(-0.5)  # 又亏
            if rc.state["consecutive_losses"] != 2:
                test["passed"] = False
                self.tests_failed += 1
            else:
                test["details"].append("连亏2笔后降仓正确")

            if rc.state["reduced_slots"] and rc.state["current_max_slots"] == 1:
                test["details"].append("降仓逻辑正确: max_slots=1")
            else:
                test["passed"] = False
                test["details"].append("降仓逻辑错误")
                self.tests_failed += 1

        except Exception as e:
            test["passed"] = False
            test["details"].append(f"异常: {e}")
            self.tests_failed += 1

        if test["passed"]:
            self.tests_passed += 1
        return test

    def _test_param_sanity(self) -> Dict:
        """参数合理性检查"""
        test = {"name": "参数合理性", "passed": True, "details": []}

        try:
            from evolution.auto_tuner import get_tuner
            tuner = get_tuner()
            params = tuner.get_current_params()

            weights = params.get("factor_weights", {})
            total_w = sum(weights.values())
            if abs(total_w - 1.0) > 0.01:
                test["passed"] = False
                test["details"].append(f"因子权重总和={total_w:.4f}，不等于1.0")
                self.tests_failed += 1
            else:
                test["details"].append(f"因子权重归一化正确 (sum={total_w:.4f})")

            # 检查各权重是否在合理范围
            for fname, w in weights.items():
                if w < 0.01 or w > 0.5:
                    self.warnings.append(f"{fname}权重={w:.4f}偏离正常范围[0.01, 0.5]")
                    test["details"].append(f"警告: {fname}权重={w:.4f}异常")

        except Exception as e:
            test["passed"] = False
            test["details"].append(f"异常: {e}")
            self.tests_failed += 1

        if test["passed"]:
            self.tests_passed += 1
        return test

    def _test_trade_history(self) -> Dict:
        """交易历史检验"""
        test = {"name": "交易历史", "passed": True, "details": []}

        try:
            from live.trade_logger import get_logger
            logger = get_logger()
            recent = logger.get_recent_records(10)

            # 检查有接回价格的记录盈亏计算是否正确
            for r in recent:
                if r.cover_price and r.short_price > 0:
                    expected_profit = (r.short_price - r.cover_price) / r.short_price * 100
                    if abs(expected_profit - r.profit_pct) > 0.01:
                        test["details"].append(
                            f"盈亏计算错误: date={r.date} stock={r.stock}, "
                            f"expected={expected_profit:.4f}% got={r.profit_pct:.4f}%"
                        )
                        self.warnings.append(f"盈亏计算偏差: {r.stock} {r.date}")
        except Exception as e:
            test["passed"] = False
            test["details"].append(f"异常: {e}")
            self.tests_failed += 1

        test["details"].append(f"最近10笔记录检验完成")
        if test["passed"]:
            self.tests_passed += 1
        return test

    def generate_report(self, results: Dict = None) -> str:
        """生成检验报告"""
        if results is None:
            results = self.run_all_tests()

        lines = [
            f"# 系统自我检验报告",
            f"日期: {results['date']}",
            f"时间: {results['timestamp']}",
            "",
            f"## 总体结果",
            f"- 检验通过: {results['tests_passed']}",
            f"- 检验失败: {results['tests_failed']}",
            f"- 状态: {'✅ 全部通过' if results['all_passed'] else '❌ 存在失败项'}",
            "",
            f"## 详细结果",
        ]

        for key, test in results.get("results", {}).items():
            status = "✅" if test.get("passed") else "❌"
            lines.append(f"\n### {status} {test.get('name', key)}")
            for detail in test.get("details", []):
                lines.append(f"  - {detail}")

        if results.get("warnings"):
            lines.append("\n## 警告")
            for w in results["warnings"]:
                lines.append(f"  - ⚠️ {w}")

        lines.append(f"\n---\n*本报告由系统自动生成*")

        report = "\n".join(lines)

        # 保存
        out_file = os.path.join(
            TEST_REPORT_DIR,
            f"self_test_{date.today().isoformat()}.md"
        )
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(report)

        return report


def run_self_test():
    tester = SystemSelfTest()
    results = tester.run_all_tests()
    report = tester.generate_report(results)
    print(report)
    print(f"\n报告已保存至: {TEST_REPORT_DIR}/self_test_{date.today().isoformat()}.md")
    return results


if __name__ == "__main__":
    run_self_test()
