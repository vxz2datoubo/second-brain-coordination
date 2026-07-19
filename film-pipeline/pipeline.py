"""
film-pipeline · 执行器
=====================
读剧本块 + 改编决策卡 → 运行 9 模块 → 生成即梦 prompt → 调 CLI 生成

使用方式:
  python pipeline.py corpus/尤斯蒂亚/scenes/block-0001.md --adapt adaptations/尤斯蒂亚-改编决策卡.yaml --dry-run
  python pipeline.py corpus/尤斯蒂亚/scenes/block-0001.md --style 写实克制 --shots 3,6,9

架构原则（来自 pragmatic-blueprint）:
  - 最小闭环优先：今天下午就能跑出第一段视频
  - 模块拆因为它坏了，不是因为设计文档说要拆
  - 验证 > 完美
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# 路径
PROJECT_ROOT = Path(__file__).parent
CORPUS_DIR = Path(os.environ.get("FILM_CORPUS", r"C:\Users\Administrator\.workbuddy\skills\film-pipeline\corpus"))
ADAPT_DIR = PROJECT_ROOT / "adaptations"
OUTPUT_DIR = PROJECT_ROOT / "output"
DREAMINA = r"F:\aidanao\tools\dreamina\dreamina.exe"

# UPS 默认参数
DEFAULT_UPS = {
    "style_tendency": "写实克制",
    "intensity": 0.70,
    "light_mood": "硬光高反差",
    "pacing": "张弛交错",
    "aspect": "2.39:1",
    "camera_language": "观察式",
    "platform": "即梦",
    "model": "seedance-2.0",
}

# 模块调用顺序
PIPELINE_ORDER = ["01", "02", "03", "08", "04", "06", "07", "09", "05"]


def load_corpus_block(block_path: str) -> dict:
    """读剧本块，返回原文和元数据"""
    path = Path(block_path)
    if not path.exists():
        # 尝试相对路径从 CORPUS_DIR
        alt = CORPUS_DIR / block_path.split("corpus/")[-1] if "corpus/" in block_path else CORPUS_DIR / block_path
        if alt.exists():
            path = alt
    if not path.exists():
        raise FileNotFoundError(f"找不到剧本块: {block_path} (也试了 {path})")
    
    text = path.read_text(encoding="utf-8")
    
    # 解析 frontmatter
    lines = text.split("\n")
    meta = {}
    if lines[0].strip() == "---":
        end = lines[1:].index("---") + 1
        for line in lines[1:end]:
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = "\n".join(lines[end+1:]).strip()
    else:
        body = text
    
    return {"meta": meta, "body": body, "path": str(path.absolute())}


def load_adaptations(adapt_path: str = None) -> dict:
    """加载改编决策卡。返回{settings, characters, terms, content_rules, style_overrides}"""
    if not adapt_path:
        return None

    path = Path(adapt_path)
    if not path.exists():
        path = ADAPT_DIR / adapt_path
    if not path.exists():
        print(f"⚠️  改编卡不存在: {adapt_path}，将使用原文")
        return None

    text = path.read_text(encoding="utf-8")
    adapt = {
        "settings": [],
        "characters": [],
        "terms": [],
        "content_rules": [],
        "style_overrides": [],
        "world_building": [],
    }

    # 简易 YAML 解析（够用，不引入 pyyaml 依赖）
    current_section = None
    current_rule = None
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue

        # 顶级段名
        if stripped == "settings:":
            current_section = "settings"
            continue
        if stripped == "characters:":
            current_section = "characters"
            continue
        if stripped == "terms:":
            current_section = "terms"
            continue
        if stripped == "content_rules:":
            current_section = "content_rules"
            continue
        if stripped == "world_building:":
            current_section = "world_building"
            continue
        if stripped == "style_overrides:":
            current_section = "style_overrides"
            continue

        # 条目
        if current_section in ("settings", "characters", "terms", "world_building"):
            if stripped.startswith("- original:"):
                current_rule = {
                    "original": stripped.split('"', 2)[1] if '"' in stripped else "",
                }
            elif stripped.startswith("adapted:") and current_rule:
                current_rule["adapted"] = stripped.split('"', 2)[1] if '"' in stripped else ""
            elif stripped.startswith("reason:") and current_rule:
                current_rule["reason"] = stripped.split('"', 2)[1] if '"' in stripped else ""
            elif stripped.startswith("applied:") and current_rule:
                current_rule["applied"] = stripped.endswith("true")
                adapt[current_section].append(current_rule)
                current_rule = None

        elif current_section == "content_rules":
            if stripped.startswith("- rule:"):
                current_rule = {
                    "rule": stripped.split('"', 2)[1] if '"' in stripped else "",
                }
            elif stripped.startswith("applied:") and current_rule:
                current_rule["applied"] = stripped.endswith("true")
                adapt[current_section].append(current_rule)
                current_rule = None

        elif current_section == "style_overrides":
            if stripped.startswith("- param:"):
                current_rule = {
                    "param": stripped.split(":", 1)[1].strip(),
                }
            elif stripped.startswith("overridden:") and current_rule:
                current_rule["overridden"] = stripped.split('"', 2)[1] if '"' in stripped else ""
                adapt[current_section].append(current_rule)
                current_rule = None

    # 只返回 applied=true 的
    active = {}
    for section, items in adapt.items():
        active[section] = [i for i in items if i.get("applied")]
    return active


def apply_adaptations(text: str, adapt: dict) -> str:
    """对文本应用所有 applied=true 的改编规则"""
    if not adapt:
        return text

    for rule in adapt.get("settings", []):
        if rule.get("original") and rule.get("adapted"):
            text = text.replace(rule["original"], rule["adapted"])

    for rule in adapt.get("characters", []):
        if rule.get("original") and rule.get("adapted"):
            text = text.replace(rule["original"], rule["adapted"])

    for rule in adapt.get("terms", []):
        if rule.get("original") and rule.get("adapted"):
            text = text.replace(rule["original"], rule["adapted"])

    for rule in adapt.get("world_building", []):
        if rule.get("original") and rule.get("adapted"):
            text = text.replace(rule["original"], rule["adapted"])

    return text


def run_pipeline(block: dict, ups: dict, shot_filter: list = None, adapt: dict = None) -> dict:
    """
    执行 01→09 模块流水线。
    
    当前实现：模块规则由 LLM（对话层）执行，此函数负责：
    1. 加载 ShotManifest 模板
    2. 写入上下文供 LLM 使用
    3. 返回 ShotManifest 基础骨架
    
    未来：接入 LLM API 自动化（Phase 2）
    """
    manifest = {
        "project_id": f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "source": block["path"],
        "meta": ups,
        "scenes": [{"scene_id": 1, "name": "待命名", "env": ""}],
        "shots": [],
        "compliance": {"passed": True, "violations": []},
        "evolution": [],
    }
    
    # 把原文和 UPS 写入上下文文件供 LLM 读取
    context = {
        "block_meta": block["meta"],
        "body_preview": block["body"][:500],
        "ups": ups,
        "pipeline_order": PIPELINE_ORDER,
    }
    ctx_path = OUTPUT_DIR / f"context-{manifest['project_id']}.json"
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"上下文已写入: {ctx_path}")
    print(f"请在对话层执行以下模块: {PIPELINE_ORDER}")
    print(f"模块规范路径: .workbuddy/skills/film-pipeline/modules/")
    
    return manifest


def fuse_prompt(shotmanifest_path: str) -> str:
    """读 ShotManifest JSON → 用融合器规则生成最终 prompt"""
    manifest = json.loads(Path(shotmanifest_path).read_text(encoding="utf-8"))
    
    prompts = []
    for shot in manifest["shots"]:
        sid = shot["shot_id"]
        adapt = shot.get("m01_adapt", {})
        concept = shot.get("m02_concept", {})
        shot_design = shot.get("m03_shot", {})
        light = shot.get("m04_light", {})
        perform = shot.get("m06_perform", {})
        action = shot.get("m07_action", {})
        sound = shot.get("m09_sound", {})
        pace = shot.get("m05_pace", {})
        
        # 材质
        materials = []
        for cc in concept.get("character_concepts", []):
            materials.append(f"{cc['name']}:{cc['material']}")
        material_str = "、".join(materials) if materials else ""
        
        # 动作
        action_str = ""
        if action.get("moves"):
            moves = [f"{m['actor']}{m['move']}({m['effect']})" for m in action["moves"]]
            action_str = "; ".join(moves)
            if action.get("violence_grade"):
                action_str += f" | violence:{action['violence_grade']}"
        
        # 拼接
        prompt = (
            f"[shot {sid}] {adapt.get('description','')} "
            f"{material_str + '。' if material_str else ''}"
            f"camera: {shot_design.get('shot_type','')} {shot_design.get('camera_move','')} {shot_design.get('lens','')}。"
            f"light: {light.get('key_light',{}).get('type','')} {light.get('mood_note','')}。"
            f"act: {perform.get('expression','')} {perform.get('action','')}。"
            f"{'motion: '+action_str+'。' if action_str else ''}"
            f"atmosphere: {pace.get('emotion_tag','')}，{pace.get('pace','')}。"
            f"audio: {sound.get('diegetic','')} {' '.join(sound.get('auditory_layers',[]))}，energy {sound.get('energy_density',0.3)}。"
        )
        prompts.append(prompt)
    
    full = "\n\n".join(prompts)
    full += "\n\nneg: low quality, blurry, static face, stiff pose, over-exposed, flat lighting, poor composition, unnatural anatomy, text overlay, watermark"
    
    # 清理：移除所有 ← 解释（导演备注，不输出到即梦 prompt）
    import re
    full = re.sub(r' ← 因[^。]*。?', '', full)
    full = re.sub(r' ← [^。,\n]*[。,\n]?', '', full)
    
    return full


def generate_video(prompt: str, shot_id: int, reference_image: str = None, duration: int = 5):
    """调用 dreamina CLI 生成视频"""
    cmd = [
        DREAMINA, "multimodal2video",
        "--prompt", prompt,
        "--duration", str(duration),
        "--resolution", "1080p",
    ]
    if reference_image:
        cmd.extend(["--reference-image", reference_image])
    
    print(f"调用: dreamina multimodal2video --prompt <shot_{shot_id}> --duration {duration}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0:
        print(f"✅ shot_{shot_id} 提交成功")
        return result.stdout
    else:
        print(f"❌ shot_{shot_id} 失败: {result.stderr}")
        return None


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="film-pipeline 执行器")
    parser.add_argument("block", help="剧本块路径 (e.g. corpus/尤斯蒂亚/scenes/block-0001.md)")
    parser.add_argument("--adapt", help="改编决策卡路径 (e.g. adaptations/尤斯蒂亚-改编决策卡.yaml)")
    parser.add_argument("--style", default="写实克制", help=f"风格倾向 (可选: {list(DEFAULT_UPS.keys())})")
    parser.add_argument("--intensity", type=float, default=0.70)
    parser.add_argument("--shots", help="仅处理指定镜头 (逗号分隔, e.g. 3,6,9)")
    parser.add_argument("--dry-run", action="store_true", help="仅输出 prompt，不生成视频")
    parser.add_argument("--ref-image", help="角色参考图 URL")
    parser.add_argument("--duration", type=int, default=5, help="单镜时长(秒)")
    
    args = parser.parse_args()
    
    # 加载改编决策卡
    adapt = None
    if args.adapt:
        adapt = load_adaptations(args.adapt)
        if adapt:
            print(f"📋 改编决策卡: {args.adapt}")
            for section, rules in adapt.items():
                for r in rules:
                    print(f"   [{section}] {r.get('original','')} → {r.get('adapted','')} ({r.get('reason','')})")
    
    # 加载剧本
    print(f"📖 加载剧本块: {args.block}")
    block = load_corpus_block(args.block)
    
    # 应用改编
    if adapt:
        block["body"] = apply_adaptations(block["body"], adapt)
        print(f"   已应用 {sum(len(v) for v in adapt.values())} 条改编规则")
    
    print(f"   元数据: {block['meta']}")
    print(f"   原文前 200 字: {block['body'][:200]}...")
    
    # 配置 UPS
    ups = {**DEFAULT_UPS, "style_tendency": args.style, "intensity": args.intensity}
    
    # 过滤镜头
    shot_filter = [int(s) for s in args.shots.split(",")] if args.shots else None
    
    # 准备上下文
    manifest = run_pipeline(block, ups, shot_filter)
    
    # 生成 prompt（如果有现成的 ShotManifest）
    shotmanifest = OUTPUT_DIR / f"shotmanifest-oz-elopement.json"
    if shotmanifest.exists():
        prompt = fuse_prompt(str(shotmanifest))
        prompt_path = OUTPUT_DIR / f"prompt-{manifest['project_id']}.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        print(f"\n📝 融合提示词已写入: {prompt_path}")
        print(f"   提示词长度: {len(prompt)} 字符")
        
        if not args.dry_run:
            print("\n🎬 开始生成...")
            # 逐镜生成
            for shot_id in (shot_filter or [1]):
                shot_prompt = prompt  # 简化：整段提示词
                generate_video(shot_prompt, shot_id, args.ref_image, args.duration)
    else:
        print("\n⚠️  需要先在对话层生成 ShotManifest JSON")
        print(f"   原文已就绪，请在 WorkBuddy 中执行 9 模块流水线")
