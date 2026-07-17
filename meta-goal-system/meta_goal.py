#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meta_goal.py — 元方法论·目标模式自治系统 的闭环引擎（多实例版）。

这是最小闭环的"测试 / 状态 / 注册表"核心：保证每一轮都能 运行 / 测试 / 复盘 / 扩展。
本系统可被**任何对话窗口**调用：窗口把任务交给它，它 spawn 一个目标实例，
写进注册表，由【每实例专属独立自动化】并行、无限推进到完成；并发上限=3，
超出排队，槽位空出由任意活跃实例每轮 dispatch 唤醒（详见 dispatch / spawn）。

子命令:
  status [id|path]     打印某目标实例的控制标志（默认 bootstrap 实例）
  list                 列出注册表里所有目标实例
  spawn <name> --task "..."   新建一个目标实例（任何窗口都能调）
  next                 从注册表挑下一个可推进的目标 id（供自动化轮询）
  guard [id|path]      读控制标志，返回 CONTINUE / PAUSE / COMPLETE（代码级刹车）
  validate [id|path]   校验报告含 9 点 + 四象限，返回 PASS/FAIL (exit 0/1)
  scaffold <n>         在 bootstrap ROADMAP.md 追加第 n 轮 9 点报告模板（兼容旧用法）

运行:
  python meta_goal.py status
  python meta_goal.py list
  python meta_goal.py spawn "做T系统回测" --task "对昆仑做3个月分钟线回测，输出胜率"
  python meta_goal.py next
  python meta_goal.py guard g_20260711230000
  python meta_goal.py validate goals/g_xxx/ROADMAP.md
"""
import sys
import os
import re
import json
import subprocess
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROADMAP = os.path.join(HERE, "ROADMAP.md")          # bootstrap 实例（首个目标）
GOALS_DIR = os.path.join(HERE, "goals")
REGISTRY = os.path.join(GOALS_DIR, "registry.json")
SB_GOAL_ENDPOINT = "http://localhost:8766/api/goal/create"
BOOTSTRAP_SB_ID = "goal_85449be5441c43"

# 并发上限：同时最多 N 个活跃实例（用户拍板=3）。超出排队，槽位空出由任意活跃实例每轮 dispatch 唤醒（无独立定时触发器）。
# 可用环境变量 MG_MAX_CONCURRENT 覆盖。
MAX_CONCURRENT = int(os.environ.get("MG_MAX_CONCURRENT", "3"))

# 9 点报告必备小节（关键词匹配，顺序无关）
REQUIRED_SECTIONS = [
    "本轮目标", "修改文件", "设计原因", "运行方法", "测试方法",
    "已完成内容", "未完成内容", "风险", "下一轮建议",
]
# 四象限必备标签
QUADRANT_TAGS = ["已知·已说", "已知·未说", "未知·可懂", "未知·不懂"]

CONTROL_KEYS = [
    "STATUS", "ROUND", "MODE", "PAUSE", "COMPLETE",
    "MAX_ROUNDS_PER_RUN", "STALL_LIMIT", "STALL_COUNT", "RISK_TIER",
]

INSTANCE_TEMPLATE = """STATUS: ACTIVE
ROUND: 0
MODE: FULL_AUTO
PAUSE: 0
COMPLETE: 0
MAX_ROUNDS_PER_RUN: 8
STALL_LIMIT: 2
STALL_COUNT: 0
RISK_TIER: BOLD
# ===== 控制说明（自治执行器每轮先读这里）=====
# PAUSE:1 或 COMPLETE:1 → 立即停止
# MODE: FULL_AUTO=单次触发内批量连续推进多轮 / SEMI_AUTO=每次只一轮
# MAX_ROUNDS_PER_RUN=单次触发最多连续推进轮数（软上限，防烧穿 token）
# STALL_LIMIT=连续无实质进展 N 轮 → 自动 PAUSE 并记录（停滞熔断）
# STALL_COUNT=当前连续无进展计数（执行器自动增减）
# RISK_TIER: BOLD=允许大步试错(带回滚+备份) / SAFE=仅小步探针
# 触发器：每小时一次；FULL_AUTO 下每次会连续跑多轮 → 近似不停

# 目标实例 — {name}
# 创建于 {now}

## Bootstrap 任务（来自调用窗口）
{task}

> 此文件是该目标实例的跨轮持久化权威状态。自动化每轮读 NEXT_ROUND，做一件事，追加报告，轮次 +1。

---

## 四象限知识映射（待本技能填充 — 捕获当前任务后第一时间补齐）

### Q1 已知·已说（用户/窗口明确陈述的需求）
- (待填充)

### Q2 已知·未说（隐含假设 / 环境 / 已有资产）
- (待填充)

### Q3 未知·可懂（可联网研究掌握的点）
- (待填充)

### Q4 未知·不懂（看不懂的盲点 → 标 TODO/Interface/Mock，禁止假装完成）
- (待填充)

---

## 任务清单（本技能分解后逐条执行，完成打钩）
- [ ] (待分解)

---

## Iteration Log

## NEXT_ROUND
(待本技能设置首轮目标 — 通常是：完成 2x2 分解 + 第 1 轮执行 + 追加 Round 1 报告)
"""


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write(path, txt):
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------- 注册表 ----------------

def ensure_registry():
    if not os.path.exists(GOALS_DIR):
        os.makedirs(GOALS_DIR)
    if not os.path.exists(REGISTRY):
        seed = {
            "goals": [
                {
                    "id": "bootstrap",
                    "name": "元方法论·目标模式自治系统(bootstrap)",
                    "path": ROADMAP,
                    "task": "见 ROADMAP.md 顶部 Bootstrap 想法",
                    "status": "active",
                    "round": read_round(ROADMAP),
                    "created_at": _now(),
                    "sb_goal_id": BOOTSTRAP_SB_ID,
                }
            ]
        }
        _write(REGISTRY, json.dumps(seed, ensure_ascii=False, indent=2))
    return json.loads(_read(REGISTRY))


def save_registry(data):
    _write(REGISTRY, json.dumps(data, ensure_ascii=False, indent=2))


# ---------------- 目标解析 ----------------

def resolve(target):
    """把 id / name / 路径 解析成 ROADMAP 文件路径。"""
    if target is None:
        return ROADMAP
    if target.endswith(".md"):
        return target
    reg = ensure_registry()
    for g in reg["goals"]:
        if g["id"] == target or g.get("name") == target:
            return g["path"]
    return None


def read_flags(path):
    txt = _read(path) if os.path.exists(path) else ""
    flags = {}
    for k in CONTROL_KEYS:
        m = re.search(rf"^{k}\s*[:=]\s*(.+)$", txt, re.MULTILINE)
        flags[k] = m.group(1).strip() if m else None
    return flags


def read_round(path):
    try:
        return int(read_flags(path).get("ROUND") or 0)
    except Exception:
        return 0


def read_next(path):
    txt = _read(path) if os.path.exists(path) else ""
    m = re.search(r"##\s+NEXT_ROUND\s*\n(.*?)(?:\n---|\Z)", txt, re.DOTALL)
    return (m.group(1).strip() if m else "(无 NEXT_ROUND)")[:400]


# ---------------- 子命令 ----------------

def status(target=None):
    path = resolve(target)
    if path is None:
        print("找不到目标:", target)
        return 1
    if not os.path.exists(path):
        print("ROADMAP 不存在:", path)
        return 1
    flags = read_flags(path)
    label = target or "bootstrap"
    print(f"===== 控制标志 [{label}] =====")
    for k in CONTROL_KEYS:
        print(f"{k:18s}: {flags.get(k) or '(未设置)'}")
    rounds = re.findall(r"^##\s+Round\s+(\d+)", _read(path), re.MULTILINE)
    print(f"已记录轮次: {len(rounds)}  (Round {', '.join(rounds) or '-'})")
    return 0


def list_goals():
    reg = ensure_registry()
    print("===== 目标实例注册表（每个实例独立并行运行）=====")
    print(f"{'ID':<22} {'ROUND':<6} {'STATUS':<8} {'AUTO':<14} NAME")
    for g in reg["goals"]:
        print(f"{g['id']:<22} {g.get('round',0):<6} {g.get('status','?'):<8} {str(g.get('automation_id')):<14} {g['name']}")
    running = count_running()
    queued = sum(1 for g in reg["goals"] if g.get("status") == "queued")
    print(f"\n共 {len(reg['goals'])} 个实例 | 活跃(running)={running} / 上限={MAX_CONCURRENT} | 排队(queued)={queued}")
    return 0


def _sb_create_goal(name, task):
    """best-effort 在第二大脑建 goal，返回 id 或 None。"""
    try:
        payload = json.dumps({
            "title": name, "goal_type": "life",
            "description": task, "priority": "high",
            "success_criteria": ["2x2 分解完成", "任务清单完成", "9点报告逐轮追加"],
            "motivation": "由 meta-method-goal-mode 技能跨窗口 spawn",
        })
        out = subprocess.run(
            ["curl", "-s", "--max-time", "8", "-X", "POST", SB_GOAL_ENDPOINT,
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=12,
        )
        d = json.loads(out.stdout)
        return d.get("id") or (d.get("goal", {}) or {}).get("id")
    except Exception:
        return None


# 每实例专属独立自动化的 prompt 模板。
# {ID} 在 spawn 时填充；{AUTO_ID} 在创建自动化拿到 id 后回填（用于自我停止）。
AUTOMATION_PROMPT_TEMPLATE = """你是 meta-method-goal-mode 技能为【实例 {ID}】启动的专属独立自动化。该实例与其他窗口的任务完全独立、并行运行，互不干扰。你拥有最大权限，允许小步/大步试错，但必须带刹车。使命：把该实例的目标持续推进到完成，无需人工干预。

== 单实例 FULL_AUTO 循环 ==
每轮触发（每小时）进入循环，直到命中停止条件：
  (a) `python F:/aidanao/meta-goal-system/meta_goal.py guard {ID}` 返回 PAUSE / COMPLETE
  (b) 本次已推进轮数 >= 该实例 MAX_ROUNDS_PER_RUN（读其 ROADMAP 顶部，默认 8）
  (c) 连续 STALL_LIMIT 轮无实质进展 → 自动把该实例 ROADMAP 顶部 PAUSE 置 1、写明停滞原因、并自我停止（见下）

== 每轮动作 ==
0. **每轮开头先 `python F:/aidanao/meta-goal-system/meta_goal.py dispatch`（兜底唤醒，替代原独立定时触发器）**：若输出 `PROMOTE g_xxxx` 或 `START g_xxxx`，对每个 id 依次 —— (a) `automation-prompt g_xxxx` 取专属 prompt → (b) automation_update(mode=create,...) 建自动化拿新 id → (c) automation_update(mode=update, id=<新id>, prompt=<回填 {AUTO_ID}>) → (d) `register-automation g_xxxx <新id>` → (e) 仅 PROMOTE 才 `activate g_xxxx`（START 已是 active）。本系统已去掉独立定时触发器，排队项/孤儿由活跃实例每轮顺手唤醒，确保"持续不断"且不假死。（NO_PROMOTION 跳过）
A. `python F:/aidanao/meta-goal-system/meta_goal.py status {ID}` 看控制标志。
B. 若 ROUND==0（鲜实例）：先 2x2 四象限分解（Q1–Q4 + 任务清单）写入 ROADMAP，执行清单首批项，追加 Round 1 的 9 点报告（含四象限标签）。
C. 若 ROUND>0：读 NEXT_ROUND，定唯一目标，实现改进（脚本/文档/接线），默认不大规模重构；必须重构则先写明理由。
D. 需新知识→WebSearch/WebFetch 真实联网，禁止凭记忆编。
E. 验证：`python F:/aidanao/meta-goal-system/meta_goal.py validate <该实例ROADMAP路径>` 必须 PASS；改了代码再跑 `python F:/aidanao/meta-goal-system/test_meta_goal.py`。不过=无进展(STALL++)。
F. 追加 9 点报告到该实例 Iteration Log；ROUND +1；无进展 STALL_COUNT+1，有进展归零；更新 NEXT_ROUND。
G. best-effort：第二大脑在跑(localhost:8766)用该实例 sb_goal_id 调 POST /api/goal/milestone 落库；失败不阻塞。
H. 绝不假装完成：Q4/未完成标 TODO/Interface/Mock。

== 试错与刹车（RISK_TIER=BOLD）==
- Q4 主动小步探针（假设→最小实验→记录成/败/回滚），方向对再大步。
- 写操作限 F:/aidanao/meta-goal-system/ + 第二大脑 API。越界/破坏性操作须先记录回滚+备份。硬禁 rm -rf / 清空目录 / 动个人文件夹 / 泄露密钥。

== 自我停止（释放并发槽位 + 完成事件即时唤醒下一个）==
当 guard 返回 COMPLETE 或 PAUSE：
1. `python F:/aidanao/meta-goal-system/meta_goal.py deactivate {ID} paused`（释放并发槽位）。
2. **完成事件即时触发调度**：紧接着运行 `python F:/aidanao/meta-goal-system/meta_goal.py dispatch`。对输出里每一行 `PROMOTE g_xxxx` 或 `START g_xxxx`：依次 —— (a) `automation-prompt g_xxxx` 取专属 prompt → (b) automation_update(mode=create,...) 建自动化拿到新 id → (c) automation_update(mode=update, id=<新id>, prompt=<回填 {AUTO_ID}>) → (d) `register-automation g_xxxx <新id>` → (e) 仅当是 PROMOTE 才 `activate g_xxxx`（START 已是 active）。这就是"全程不停"：一个任务完成，下一个立刻接上；活跃但没循环的孤儿也在此补建。若输出 `NO_PROMOTION`（无人排队、无孤儿）则跳过。
3. 在本实例 ROADMAP 写明完成/暂停原因。
4. 调用 automation_update（mode=update, id={AUTO_ID}, status=PAUSED）把本自动化自身暂停，不再占用资源。

语言：中文，直接、有主见、不废话。没有真实价值的一轮宁可判无进展触发熔断。"""


def spawn(name, task):
    ensure_registry()
    gid = "g_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    gdir = os.path.join(GOALS_DIR, gid)
    while os.path.exists(gdir):
        gid = "g_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        gdir = os.path.join(GOALS_DIR, gid)
    os.makedirs(gdir)
    rpath = os.path.join(gdir, "ROADMAP.md")
    _write(rpath, INSTANCE_TEMPLATE.format(name=name, task=task, now=_now()))
    sb_id = _sb_create_goal(name, task)
    running = count_running()
    status = "active" if running < MAX_CONCURRENT else "queued"
    reg = ensure_registry()
    reg["goals"].append({
        "id": gid, "name": name, "path": rpath, "task": task,
        "status": status, "round": 0, "created_at": _now(),
        "sb_goal_id": sb_id, "automation_id": None,
    })
    save_registry(reg)
    print(f"已创建目标实例: id={gid}")
    print(f"  ROADMAP : {rpath}")
    print(f"  第二大脑 goal: {sb_id or '(未运行/失败, 不影响)'}")
    if status == "active":
        print(f"  状态: active（在并发上限 {MAX_CONCURRENT} 内，将启动专属独立自动化）")
        print(f"  下一步: 创建该实例【专属独立自动化】(见下方 prompt)，独立、并行、无限执行直到完成。")
        print(f"  ----- 自动化 prompt 模板（创建 automation 时填入；{{ID}} 已填，{{AUTO_ID}} 待创建后回填）-----")
        print(AUTOMATION_PROMPT_TEMPLATE.format(ID=gid, AUTO_ID="{AUTO_ID}"))
    else:
        print(f"  状态: queued（当前活跃实例已达上限 {MAX_CONCURRENT}，排队等待唤醒）")
        print(f"  暂不为其创建自动化；当某活跃实例完成/暂停释放槽位时，会【完成事件即时触发】dispatch 唤醒本项(PROMOTE→建专属自动化→activate)，或由任意活跃实例每轮 dispatch 兜底唤醒。")
    return gid


def register_automation(gid, auto_id):
    """记录某实例对应的专属自动化 id（创建自动化后回填）。"""
    reg = ensure_registry()
    for g in reg["goals"]:
        if g["id"] == gid:
            g["automation_id"] = auto_id
            break
    else:
        return False
    save_registry(reg)
    return True


def get_automation(gid):
    reg = ensure_registry()
    for g in reg["goals"]:
        if g["id"] == gid:
            return g.get("automation_id")
    return None


# ---------------- 并发控制（上限=3，超出排队，闸门唤醒） ----------------

def count_running():
    """当前"活跃"实例数（非 bootstrap、status=active）。用于并发上限判定。"""
    reg = ensure_registry()
    n = 0
    for g in reg["goals"]:
        if g["id"] == "bootstrap":
            continue
        if g.get("status") == "active":
            n += 1
    return n


def dispatch():
    """每实例每轮兜底用：输出需唤醒/兜底创建的实例（无独立定时触发器，由活跃实例 self-stop 或每轮开头调 dispatch）。
    ① PROMOTE <id> = 排队实例，占用空槽后唤醒（建自动化→activate）
    ② START   <id> = 活跃但尚无专属自动化的孤儿实例（窗口只 spawn 没建自动化时兜底）
    ③ NO_PROMOTION    = 无事可做
    返回 0 表示有动作，1 表示无动作。"""
    reg = ensure_registry()
    running = count_running()
    slots = MAX_CONCURRENT - running
    queued = [g for g in reg["goals"] if g.get("status") == "queued"]
    queued.sort(key=lambda g: g.get("created_at", "") or "")
    promote = queued[:max(0, slots)]
    # 兜底：活跃但没有专属自动化 → 防止"spawn 了但没建循环"导致假死
    # 排除 bootstrap（系统自身，非待跑任务，其 automation_id 始终为 None）
    orphans = [g for g in reg["goals"]
               if g.get("id") != "bootstrap"
               and g.get("status") == "active" and not g.get("automation_id")]
    actions = [("PROMOTE", g["id"]) for g in promote] + [("START", g["id"]) for g in orphans]
    if not actions:
        print(f"NO_PROMOTION (running={running}, queued={len(queued)}, orphans={len(orphans)}, max={MAX_CONCURRENT})")
        return 1
    for verb, gid in actions:
        print(f"{verb} {gid}")
    return 0


def activate(gid):
    """把排队实例置 active（闸门唤醒后调用）。"""
    reg = ensure_registry()
    for g in reg["goals"]:
        if g["id"] == gid:
            g["status"] = "active"
            save_registry(reg)
            print(f"已激活实例 {gid}（状态置 active）")
            return 0
    print("找不到实例:", gid)
    return 1


def deactivate(gid, status="paused"):
    """实例完成/暂停时释放并发槽位（置 paused/complete），让排队实例可被调度。"""
    reg = ensure_registry()
    for g in reg["goals"]:
        if g["id"] == gid:
            g["status"] = status
            save_registry(reg)
            print(f"已将实例 {gid} 状态置为 {status}（释放并发槽位）")
            return 0
    print("找不到实例:", gid)
    return 1


def automation_prompt(gid):
    """打印某实例的专属自动化 prompt 文本（{ID} 已填，{AUTO_ID} 占位），供实例每轮兜底创建自动化。"""
    reg = ensure_registry()
    for g in reg["goals"]:
        if g["id"] == gid:
            print(AUTOMATION_PROMPT_TEMPLATE.format(ID=gid, AUTO_ID="{AUTO_ID}"))
            return 0
    print("找不到实例:", gid)
    return 1


def next_goal():
    """从注册表挑下一个可推进的目标（active 且未 PAUSE/COMPLETE），按 round 升序（最少推进优先）。"""
    reg = ensure_registry()
    candidates = []
    for g in reg["goals"]:
        path = g["path"]
        if not os.path.exists(path):
            continue
        flags = read_flags(path)
        if flags.get("PAUSE") == "1" or flags.get("COMPLETE") == "1":
            continue
        if flags.get("STATUS") not in (None, "ACTIVE", "active"):
            continue
        candidates.append((g.get("round", 0), g["id"]))
    if not candidates:
        print("NO_ACTIONABLE_GOAL")
        return 1
    candidates.sort()
    chosen = candidates[0][1]
    print(chosen)
    return 0


def guard(target=None):
    """代码级刹车：返回 CONTINUE / PAUSE / COMPLETE。"""
    path = resolve(target)
    if path is None or not os.path.exists(path):
        print("PAUSE  # 目标不可达")
        return 2
    flags = read_flags(path)
    if flags.get("COMPLETE") == "1":
        print("COMPLETE")
        return 0
    if flags.get("PAUSE") == "1":
        print("PAUSE")
        return 2
    try:
        stall = int(flags.get("STALL_COUNT") or 0)
        limit = int(flags.get("STALL_LIMIT") or 2)
        if stall >= limit:
            print(f"PAUSE  # 停滞熔断 STALL_COUNT={stall}>={limit}")
            return 2
    except Exception:
        pass
    print("CONTINUE")
    return 0


def validate(path):
    if path is None:
        path = ROADMAP
    if not os.path.exists(path):
        print(f"[FAIL] 文件不存在: {path}")
        return 1
    txt = _read(path)
    missing_sec = [s for s in REQUIRED_SECTIONS if s not in txt]
    missing_q = [q for q in QUADRANT_TAGS if q not in txt]
    ok = (not missing_sec) and (not missing_q)
    print(f"===== 校验: {os.path.basename(path)} =====")
    print(f"9 点报告小节: {'PASS' if not missing_sec else 'FAIL -> 缺 ' + str(missing_sec)}")
    print(f"四象限标签:   {'PASS' if not missing_q else 'FAIL -> 缺 ' + str(missing_q)}")
    print("结果:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


def scaffold(n):
    if not os.path.exists(ROADMAP):
        print("ROADMAP.md 不存在，无法 scaffold")
        return 1
    tpl = f"""

---

## Round {n}（待填写）

> 本轮只做 ONE 个最小有价值改进。

### 1. 本轮目标

### 2. 修改文件

### 3. 设计原因

### 4. 运行方法

### 5. 测试方法

### 6. 已完成内容

### 7. 未完成内容（必须标 TODO / Interface / Mock / Future Roadmap）

### 8. 风险

### 9. 下一轮建议

"""
    with open(ROADMAP, "a", encoding="utf-8") as f:
        f.write(tpl)
    print(f"已追加 Round {n} 模板到 bootstrap ROADMAP.md")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1].lower()
    if cmd == "status":
        t = sys.argv[2] if len(sys.argv) > 2 else None
        return status(t)
    if cmd == "list":
        return list_goals()
    if cmd == "spawn":
        if len(sys.argv) < 3:
            print("用法: spawn <name> --task \"...\"")
            return 1
        name = sys.argv[2]
        task = ""
        if "--task" in sys.argv:
            ti = sys.argv.index("--task") + 1
            task = sys.argv[ti] if ti < len(sys.argv) else ""
        return spawn(name, task) or 0
    if cmd == "next":
        return next_goal()
    if cmd == "guard":
        t = sys.argv[2] if len(sys.argv) > 2 else None
        return guard(t)
    if cmd == "validate":
        p = sys.argv[2] if len(sys.argv) > 2 else None
        return validate(p)
    if cmd == "scaffold":
        n = sys.argv[2] if len(sys.argv) > 2 else "N"
        return scaffold(n)
    if cmd == "dispatch":
        return dispatch()
    if cmd == "activate":
        t = sys.argv[2] if len(sys.argv) > 2 else None
        return activate(t) if t else (print("用法: activate <id>") or 1)
    if cmd == "deactivate":
        t = sys.argv[2] if len(sys.argv) > 2 else None
        s = sys.argv[3] if len(sys.argv) > 3 else "paused"
        return deactivate(t, s) if t else (print("用法: deactivate <id> [paused|complete]") or 1)
    if cmd == "automation-prompt":
        t = sys.argv[2] if len(sys.argv) > 2 else None
        return automation_prompt(t) if t else (print("用法: automation-prompt <id>") or 1)
    if cmd == "register-automation":
        t = sys.argv[2] if len(sys.argv) > 2 else None
        a = sys.argv[3] if len(sys.argv) > 3 else None
        return register_automation(t, a) if (t and a) else (print("用法: register-automation <id> <auto_id>") or 1)
    print(f"未知子命令: {cmd}\n")
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
