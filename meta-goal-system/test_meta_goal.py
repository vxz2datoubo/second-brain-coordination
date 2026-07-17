#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_meta_goal.py — 闭环引擎的测试（多实例版）。
规则要求：修改后必须更新相关测试。本文件即为"相关测试"。
运行: python test_meta_goal.py
"""
import os
import sys
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import meta_goal as mg

VALID = """## Round 1

### 1. 本轮目标
测试目标

### 2. 修改文件
a.py

### 3. 设计原因
原因

### 4. 运行方法
python a.py

### 5. 测试方法
python test_a.py

### 6. 已完成内容
做了

### 7. 未完成内容
TODO: 没做完

### 8. 风险
风险低

### 9. 下一轮建议
做下一件

四象限映射:
- 已知·已说: x
- 已知·未说: y
- 未知·可懂: z
- 未知·不懂: w
"""

BROKEN = """## Round 1
### 1. 本轮目标
只有目标，缺其他小节，也没有四象限。
"""


def _cleanup_goal(gid):
    reg = mg.ensure_registry()
    reg["goals"] = [g for g in reg["goals"] if g["id"] != gid]
    mg.save_registry(reg)
    gdir = os.path.join(mg.GOALS_DIR, gid)
    if os.path.isdir(gdir):
        shutil.rmtree(gdir)


def test_validate_pass():
    with __temp(VALID) as path:
        assert mg.validate(path) == 0, "合法报告应 PASS"
    print("[ok] test_validate_pass")


def test_validate_fail():
    with __temp(BROKEN) as path:
        assert mg.validate(path) == 1, "破损报告应 FAIL"
    print("[ok] test_validate_fail")


def test_status_runs():
    assert os.path.exists(mg.ROADMAP), "ROADMAP.md 必须存在"
    assert mg.status() == 0
    print("[ok] test_status_runs")


def test_scaffold_appends():
    before = len(mg._read(mg.ROADMAP))
    mg.scaffold("99")
    after = len(mg._read(mg.ROADMAP))
    assert after > before, "scaffold 应追加内容"
    txt = mg._read(mg.ROADMAP)
    txt = txt.split("## Round 99")[0].rstrip() + "\n"
    with open(mg.ROADMAP, "w", encoding="utf-8") as f:
        f.write(txt)
    print("[ok] test_scaffold_appends (已清理模板)")


def test_spawn_creates_instance():
    before = len(mg.ensure_registry()["goals"])
    gid = mg.spawn("__test_goal__", "测试任务")
    assert gid.startswith("g_")
    reg = mg.ensure_registry()
    assert len(reg["goals"]) == before + 1
    assert any(g["id"] == gid for g in reg["goals"])
    rpath = os.path.join(mg.GOALS_DIR, gid, "ROADMAP.md")
    assert os.path.exists(rpath)
    _cleanup_goal(gid)
    assert len(mg.ensure_registry()["goals"]) == before
    print("[ok] test_spawn_creates_instance (已清理)")


def test_validate_fresh_instance_fails():
    # 鲜实例（ROUND:0，无 9 点报告）应 FAIL —— 证明 validator 正确拦截未分解实例
    gid = mg.spawn("__test_fresh__", "x")
    rpath = os.path.join(mg.GOALS_DIR, gid, "ROADMAP.md")
    assert mg.validate(rpath) == 1, "鲜实例(无轮次报告)应 FAIL"
    _cleanup_goal(gid)
    print("[ok] test_validate_fresh_instance_fails (已清理)")


def test_guard_logic():
    assert mg.guard(mg.ROADMAP) == 0, "bootstrap 应 CONTINUE"
    assert mg.guard("goals/nope/ROADMAP.md") == 2, "不可达路径应 PAUSE"
    print("[ok] test_guard_logic")


def test_register_automation_roundtrip():
    # spawn 一个实例，注册其专属自动化 id，再取回，最后清理
    gid = mg.spawn("__test_auto__", "x")
    assert mg.register_automation(gid, "automation-demo123") is True
    assert mg.get_automation(gid) == "automation-demo123"
    # 切回 None 也应可写回
    assert mg.register_automation(gid, None) is True
    assert mg.get_automation(gid) is None
    _cleanup_goal(gid)
    print("[ok] test_register_automation_roundtrip (已清理)")


def test_spawn_prints_automation_prompt():
    # spawn 输出应包含每实例独立自动化 prompt 模板（含 {ID} 已填、{AUTO_ID} 占位）
    import io, contextlib
    buf = io.StringIO()
    gid = None
    with contextlib.redirect_stdout(buf):
        gid = mg.spawn("__test_prompt__", "demo")
    out = buf.getvalue()
    assert "专属独立自动化" in out, "spawn 应输出专属自动化说明"
    assert "AUTOMATION_PROMPT_TEMPLATE" not in out  # 不应泄露常量名
    assert "{AUTO_ID}" in out, "应保留 {AUTO_ID} 占位待回填"
    _cleanup_goal(gid)
    print("[ok] test_spawn_prints_automation_prompt (已清理)")


def test_list_and_next_run():
    assert mg.list_goals() == 0
    assert mg.next_goal() == 0, "注册表有 active 实例 → next 应产出 id"
    print("[ok] test_list_and_next_run")


def test_max_concurrent_default():
    assert mg.MAX_CONCURRENT == 3, "默认并发上限应为 3"
    print("[ok] test_max_concurrent_default")


def test_concurrency_cap_and_dispatch():
    # 受控注册表验证：满 3 活跃 → 第 4 个排队；满槽 dispatch=NO_PROMOTION；
    # 释放 1 槽 → dispatch=PROMOTE 排队项。
    import io, contextlib, shutil as _sh
    reg_path = mg.REGISTRY
    backup = reg_path + ".bak"
    had = os.path.exists(reg_path)
    if had:
        _sh.copy(reg_path, backup)
    gid4 = None
    base = [{
        "id": "bootstrap", "name": "b", "path": mg.ROADMAP, "task": "t",
        "status": "active", "round": 0, "created_at": "2020-01-01",
        "sb_goal_id": None, "automation_id": None,
    }]
    for i in range(3):
        gid = "g_capactive%d" % i
        gdir = os.path.join(mg.GOALS_DIR, gid)
        os.makedirs(gdir, exist_ok=True)
        mg._write(os.path.join(gdir, "ROADMAP.md"),
                  mg.INSTANCE_TEMPLATE.format(name="a%d" % i, task="t", now=mg._now()))
        base.append({
            "id": gid, "name": "a%d" % i, "path": os.path.join(gdir, "ROADMAP.md"),
            "task": "t", "status": "active", "round": 0,
            "created_at": "2020-01-0%d" % (i + 1), "sb_goal_id": None,
            "automation_id": "automation-cap-%d" % i,  # 真实活跃实例应当已有专属自动化
        })
    mg.save_registry({"goals": base})
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            gid4 = mg.spawn("cap4", "t4")
        reg = mg.ensure_registry()
        assert mg.count_running() == 3, "占满时 active 应为 3，实际 %d" % mg.count_running()
        queued = [g for g in reg["goals"] if g.get("status") == "queued"]
        assert len(queued) == 1 and queued[0]["id"] == gid4, "第4个应 queued"
        assert "queued" in buf.getvalue(), "spawn 应提示排队"
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc = mg.dispatch()
        assert rc == 1 and "NO_PROMOTION" in buf2.getvalue(), "满槽应 NO_PROMOTION"
        mg.deactivate("g_capactive0", "paused")
        assert mg.count_running() == 2, "释放后应剩 2"
        buf3 = io.StringIO()
        with contextlib.redirect_stdout(buf3):
            rc2 = mg.dispatch()
        assert rc2 == 0 and ("PROMOTE " + gid4) in buf3.getvalue(), "空槽应 PROMOTE 排队项"
        print("[ok] test_concurrency_cap_and_dispatch")
    finally:
        if had:
            _sh.move(backup, reg_path)
        else:
            if os.path.exists(reg_path):
                os.remove(reg_path)
        for i in range(3):
            _sh.rmtree(os.path.join(mg.GOALS_DIR, "g_capactive%d" % i), ignore_errors=True)
        if gid4:
            _sh.rmtree(os.path.join(mg.GOALS_DIR, gid4), ignore_errors=True)


def test_dispatch_starts_orphan_active_without_automation():
    # 兜底：活跃但没自动化_id 的孤儿实例，dispatch 应输出 START（而非被遗忘假死）
    import io, contextlib, shutil as _sh
    reg_path = mg.REGISTRY
    backup = reg_path + ".bak"
    had = os.path.exists(reg_path)
    if had:
        _sh.copy(reg_path, backup)
    g_orphan = "g_orphan_x"
    g_ok = "g_automated_y"
    base = [{
        "id": "bootstrap", "name": "b", "path": mg.ROADMAP, "task": "t",
        "status": "active", "round": 0, "created_at": "2020-01-01",
        "sb_goal_id": None, "automation_id": None,
    }]
    for gid, auto in [(g_orphan, None), (g_ok, "automation-123")]:
        gdir = os.path.join(mg.GOALS_DIR, gid)
        os.makedirs(gdir, exist_ok=True)
        mg._write(os.path.join(gdir, "ROADMAP.md"),
                  mg.INSTANCE_TEMPLATE.format(name=gid, task="t", now=mg._now()))
        base.append({
            "id": gid, "name": gid, "path": os.path.join(gdir, "ROADMAP.md"),
            "task": "t", "status": "active", "round": 0,
            "created_at": "2020-01-02", "sb_goal_id": None, "automation_id": auto,
        })
    mg.save_registry({"goals": base})
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mg.dispatch()
        out = buf.getvalue()
        assert rc == 0, "应有动作"
        assert ("START " + g_orphan) in out, "孤儿应被 START 兜底"
        assert ("START " + g_ok) not in out, "已有自动化的不应重复 START"
        assert "PROMOTE" not in out, "无排队项不应 PROMOTE"
        print("[ok] test_dispatch_starts_orphan_active_without_automation")
    finally:
        if had:
            _sh.move(backup, reg_path)
        else:
            if os.path.exists(reg_path):
                os.remove(reg_path)
        for gid in (g_orphan, g_ok):
            _sh.rmtree(os.path.join(mg.GOALS_DIR, gid), ignore_errors=True)


def test_per_round_dispatch_fallback_in_prompt():
    # 移除独立调度闸门后，兜底唤醒能力必须落在每个实例每轮动作里，防回归
    tpl = mg.AUTOMATION_PROMPT_TEMPLATE
    assert "每轮开头" in tpl, "模板须在每轮动作开头兜底 dispatch"
    assert "NO_PROMOTION" in tpl, "模板须处理无动作情形"
    assert "调度闸门" not in tpl, "模板不应再提已删除的调度闸门"
    print("[ok] test_per_round_dispatch_fallback_in_prompt")


def test_event_driven_in_prompt_template():
    # 完成事件即时触发是本系统"全程不停"的关键特性，必须在自动化模板里，防回归丢失
    tpl = mg.AUTOMATION_PROMPT_TEMPLATE
    assert "完成事件即时触发" in tpl, "模板须含完成事件即时触发指令"
    assert "dispatch" in tpl, "模板须指示自停止前先跑 dispatch 唤醒下一个"
    assert "register-automation" in tpl, "模板须指示把新自动化绑定到实例"
    print("[ok] test_event_driven_in_prompt_template")


def test_register_automation_cli():
    # 验证 main() 暴露 register-automation 子命令（Round 5 修复的 CLI 缺口）
    gid = mg.spawn("__test_cli__", "x")
    import io, contextlib
    buf = io.StringIO()
    old = sys.argv[:]
    try:
        sys.argv = ["meta_goal.py", "register-automation", gid, "automation-cliX"]
        with contextlib.redirect_stdout(buf):
            try:
                mg.main()
            except SystemExit as e:
                assert e.code == 0, "CLI 成功应 exit 0"
        assert mg.get_automation(gid) == "automation-cliX", "CLI 应写入绑定"
    finally:
        sys.argv = old
        _cleanup_goal(gid)
    print("[ok] test_register_automation_cli (已清理)")


class __temp:
    def __init__(self, content):
        self.content = content
        self.path = None
    def __enter__(self):
        import tempfile
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        f.write(self.content)
        f.close()
        self.path = f.name
        return self.path
    def __exit__(self, *a):
        if self.path and os.path.exists(self.path):
            os.unlink(self.path)


if __name__ == "__main__":
    test_validate_pass()
    test_validate_fail()
    test_status_runs()
    test_scaffold_appends()
    test_spawn_creates_instance()
    test_validate_fresh_instance_fails()
    test_guard_logic()
    test_register_automation_roundtrip()
    test_spawn_prints_automation_prompt()
    test_list_and_next_run()
    test_max_concurrent_default()
    test_concurrency_cap_and_dispatch()
    test_per_round_dispatch_fallback_in_prompt()
    test_event_driven_in_prompt_template()
    test_register_automation_cli()
    print("\n所有测试通过 ✅")
