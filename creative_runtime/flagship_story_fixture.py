"""Approved synthetic flagship prelude: three acts, six chapters, twelve choices."""

from __future__ import annotations

from .script_registry import build_script_package, style_profiles_v1
from .story_bibles import CharacterBible, SceneBible, StoryBibleBundle, validate_story_bibles
from .story_graph import (
    ChoiceOption,
    ImmutableStoryGraph,
    MajorChoicePoint,
    StaticConsequence,
    StoryAct,
    StoryChapter,
    validate_graph_for_package,
)


def _option(option_id: str, label: str, summary: str, changes: tuple[str, ...], *,
            next_choice_id: str | None = None, ending_id: str | None = None,
            rewards: tuple[str, ...] = (), costs: tuple[str, ...] = ()) -> ChoiceOption:
    return ChoiceOption(
        option_id=option_id,
        label=label,
        consequence=StaticConsequence(summary, changes, rewards, costs),
        next_choice_id=next_choice_id,
        ending_id=ending_id,
    )


def _choices() -> tuple[MajorChoicePoint, ...]:
    authored = (
        ("c01_storm_signal", "act01", "ch01", "storm_pier", "暴雨中的求救灯，是追查还是陷阱？",
         _option("c01_decode", "先解码灯号", "获得伪造灯号的第一条线索，但错过救援窗口。", ("clue", "risk"), next_choice_id="c02_castaway", rewards=("evidence",), costs=("time",)),
         _option("c01_rescue", "先救落水者", "救下证人并赢得林澜信任，但消耗唯一信号弹。", ("relationship", "resource"), next_choice_id="c02_castaway", rewards=("ally_trust",), costs=("flare",))),
        ("c02_castaway", "act01", "ch01", "storm_pier", "证人口袋里的封条应当交给谁？",
         _option("c02_share", "向队友公开", "队伍形成共同证据链，敌人也更早察觉追查。", ("relationship", "risk"), next_choice_id="c03_archive_entry", rewards=("team_cohesion",), costs=("exposure",)),
         _option("c02_hide", "暂时隐瞒", "保留独占线索，却在队伍中埋下不信任。", ("clue", "relationship"), next_choice_id="c03_archive_entry", rewards=("private_leverage",), costs=("trust",))),
        ("c03_archive_entry", "act01", "ch02", "customs_archive", "海关档案馆只剩一次进入机会。",
         _option("c03_bluff", "伪装稽查员", "保全开锁工具并进入内库，但风险上升。", ("scene", "risk"), next_choice_id="c04_red_ledger", rewards=("tool_saved",), costs=("suspicion",)),
         _option("c03_breach", "从排水渠潜入", "秘密进入内库，却损坏一件攀爬装备。", ("scene", "resource"), next_choice_id="c04_red_ledger", rewards=("stealth",), costs=("climbing_kit",))),
        ("c04_red_ledger", "act01", "ch02", "customs_archive", "红色账本与失踪名单相互矛盾。",
         _option("c04_copy", "完整复制账本", "获得可公开验证的犯罪账目，但延误撤离。", ("clue", "risk"), next_choice_id="c05_market_contact", rewards=("ledger_copy",), costs=("time",)),
         _option("c04_mark", "只记关键页码", "快速撤离并保留行动优势，证据强度较低。", ("clue", "resource"), next_choice_id="c05_market_contact", rewards=("initiative",), costs=("evidence_strength",))),
        ("c05_market_contact", "act02", "ch03", "night_market", "夜市线人要求先兑现旧承诺。",
         _option("c05_pay", "交出备用燃料", "换得塔台暗号，同时失去追艇资源。", ("clue", "resource"), next_choice_id="c06_tail", rewards=("tower_code",), costs=("fuel",)),
         _option("c05_vouch", "让林澜担保", "保住燃料，但把队友声誉押进交易。", ("relationship", "risk"), next_choice_id="c06_tail", rewards=("fuel_saved",), costs=("ally_reputation",))),
        ("c06_tail", "act02", "ch03", "night_market", "敌方跟踪者在拥挤人群中逼近。",
         _option("c06_split", "分队诱敌", "开启两路调查任务，但队伍暂时分散。", ("quest", "risk"), next_choice_id="c07_drydock_choice", rewards=("flank_route",), costs=("separation",)),
         _option("c06_confront", "公开反跟踪", "迫使敌人撤退并看清其身份，却暴露主角。", ("clue", "risk"), next_choice_id="c07_drydock_choice", rewards=("enemy_identity",), costs=("exposure",))),
        ("c07_drydock_choice", "act02", "ch04", "dry_dock", "干船坞里，救人和截获货物只能先做一件。",
         _option("c07_free", "先解救工人", "解锁工人证词与盟友支线，走私货被转移。", ("quest", "relationship"), next_choice_id="c08_manifest", rewards=("witness_network",), costs=("cargo_lost",)),
         _option("c07_tag", "先标记货柜", "锁定走私路线，但被困工人承受更大风险。", ("clue", "risk"), next_choice_id="c08_manifest", rewards=("cargo_trace",), costs=("moral_pressure",))),
        ("c08_manifest", "act02", "ch04", "dry_dock", "清单显示乔岑并非唯一幕后人。",
         _option("c08_tell", "告知全队", "队伍共同承担真相并开启内部调查。", ("relationship", "quest"), next_choice_id="c09_tower_ascent", rewards=("shared_mission",), costs=("internal_doubt",)),
         _option("c08_withhold", "只告诉米拉", "强化与米拉的秘密同盟，但林澜信任下降。", ("relationship", "clue"), next_choice_id="c09_tower_ascent", rewards=("analyst_bond",), costs=("captain_trust",))),
        ("c09_tower_ascent", "act03", "ch05", "signal_tower", "塔台上行路线被封锁。",
         _option("c09_power", "切断主电路", "打开维修通道并削弱敌方监控，备用灯也熄灭。", ("scene", "resource"), next_choice_id="c10_qiao_offer", rewards=("blind_spot",), costs=("beacon_power",)),
         _option("c09_climb", "攀爬外墙", "保住灯塔电力并取得壮观制高点，但身体风险上升。", ("scene", "risk"), next_choice_id="c10_qiao_offer", rewards=("high_ground",), costs=("injury_risk",))),
        ("c10_qiao_offer", "act03", "ch05", "signal_tower", "乔岑提出用人质交换账本。",
         _option("c10_trade", "接受交换", "人质暂时安全，但关键证据落入敌手。", ("relationship", "resource"), next_choice_id="c11_breakwater", rewards=("hostage_safe",), costs=("ledger",)),
         _option("c10_stall", "拖延并套话", "获得幕后主使录音，却让人质处境恶化。", ("clue", "risk"), next_choice_id="c11_breakwater", rewards=("confession_audio",), costs=("hostage_risk",))),
        ("c11_breakwater", "act03", "ch06", "dawn_breakwater", "黎明前，队伍只能控制一个出口。",
         _option("c11_harbor", "封锁港口", "阻断走私船并推进公开审判任务。", ("quest", "scene"), next_choice_id="c12_final_broadcast", rewards=("escape_blocked",), costs=("shore_open",)),
         _option("c11_shore", "守住岸线", "保护证人与市民，却放走部分犯罪资产。", ("relationship", "resource"), next_choice_id="c12_final_broadcast", rewards=("civilians_safe",), costs=("assets_escape",))),
        ("c12_final_broadcast", "act03", "ch06", "dawn_breakwater", "真相应当如何被交给这座城市？",
         _option("c12_broadcast", "公开全部证据", "解锁公开真相结局，也让所有关系接受审视。", ("ending", "relationship"), ending_id="ending_public_truth", rewards=("public_truth",), costs=("privacy",)),
         _option("c12_rescue", "优先完成营救", "解锁守护者结局，保住生命但延后制度清算。", ("ending", "quest"), ending_id="ending_guardian_dawn", rewards=("lives_saved",), costs=("justice_delayed",))),
    )
    return tuple(
        MajorChoicePoint(choice_id, act_id, chapter_id, scene_id, index, question, (left, right))
        for index, (choice_id, act_id, chapter_id, scene_id, question, left, right) in enumerate(authored, 1)
    )


def flagship_story_fixture():
    """Return a fresh immutable package, graph and bible bundle."""

    choices = _choices()
    raw_characters = (
        {"character_id": "yao", "adult": True, "goal": "find the missing crew", "asset_id": "character_yao_v1"},
        {"character_id": "lin", "adult": True, "goal": "clear her crew", "asset_id": "character_lin_v1"},
        {"character_id": "mira", "adult": True, "goal": "preserve evidence", "asset_id": "character_mira_v1"},
        {"character_id": "qiao", "adult": True, "goal": "contain the scandal", "asset_id": "character_qiao_v1"},
    )
    scene_specs = (
        ("storm_pier", "暴雨码头"), ("customs_archive", "海关档案馆"),
        ("night_market", "雾港夜市"), ("dry_dock", "废弃干船坞"),
        ("signal_tower", "旧信号塔"), ("dawn_breakwater", "黎明防波堤"),
    )
    assets = tuple(
        {"asset_id": item["asset_id"], "role": "character_anchor", "synthetic": True}
        for item in raw_characters
    ) + tuple(
        {"asset_id": f"scene_{scene_id}_v1", "role": "scene_anchor", "synthetic": True}
        for scene_id, _ in scene_specs
    )
    package = build_script_package(
        script_id="synthetic_mist_harbor_echoes", script_revision="1.0.0",
        genre=("adventure", "mystery", "crime", "emotional"), content_rating="non_explicit",
        world_bible={"title": "雾港回声", "format": "45-60 minute interactive season prelude",
                     "immutable_facts": ("all principal characters are adults", "the story spans one storm night")},
        character_bibles=raw_characters,
        scene_bibles=tuple({"scene_id": scene_id, "name": name} for scene_id, name in scene_specs),
        story_beats=tuple({"beat_id": item.choice_id, "scene_id": item.scene_id,
                           "purpose": item.dramatic_question} for item in choices),
        legal_choices={item.choice_id: tuple(option.option_id for option in item.options) for item in choices},
        consequence_rules={option.option_id: option.consequence.to_dict()
                           for item in choices for option in item.options},
        reward_rules={"meaningful_feedback_required": True,
                      "allowed": ("evidence", "relationship", "resource", "spectacle", "quest", "ending")},
        ending_rules={"ending_public_truth": {"final_choice": "c12_broadcast"},
                      "ending_guardian_dawn": {"final_choice": "c12_rescue"}},
        style_profiles=style_profiles_v1(), asset_manifest=assets,
        source_provenance={"source_id": "r179_synthetic_flagship_prelude", "classification": "SYNTHETIC",
                           "approved_for_reuse": True, "approval_record": "ISSUE-540-R179"},
        approval_status="approved",
    )
    graph = ImmutableStoryGraph(
        script_id=package.script_id, script_revision=package.script_revision, package_hash=package.package_hash,
        entry_choice_id=choices[0].choice_id,
        acts=(StoryAct("act01", 1, "迷雾召唤", ("ch01", "ch02")),
              StoryAct("act02", 2, "代价与背叛", ("ch03", "ch04")),
              StoryAct("act03", 3, "黎明审判", ("ch05", "ch06"))),
        chapters=tuple(StoryChapter(f"ch{i:02d}", f"act{((i - 1) // 2) + 1:02d}", i, name,
                                    (choices[(i - 1) * 2].choice_id, choices[(i - 1) * 2 + 1].choice_id))
                       for i, name in enumerate(("暴雨来客", "封存账本", "夜市交易", "船坞抉择", "塔顶人质", "黎明广播"), 1)),
        choices=choices, ending_ids=("ending_public_truth", "ending_guardian_dawn"),
    )
    characters = (
        CharacterBible("yao", "姚岚", 29, "player_investigator", "找回失踪船员", "揭开雾港真相", ("生命", "真相"), ("再次失去队友",), ("起初不知道港务局内应",), "character_yao_v1", ("c01_storm_signal", "c07_drydock_choice", "c12_final_broadcast")),
        CharacterBible("lin", "林澜", 34, "salvage_captain", "洗清船员污名", "带全队活过风暴", ("忠诚", "担当"), ("队伍分裂",), ("不知道米拉保留了旧档案",), "character_lin_v1", ("c02_castaway", "c05_market_contact", "c10_qiao_offer")),
        CharacterBible("mira", "米拉", 31, "archive_analyst", "保存不可篡改的证据", "让失踪者被看见", ("证据", "克制"), ("真相被娱乐化",), ("不知道乔岑的人质位置",), "character_mira_v1", ("c04_red_ledger", "c08_manifest", "c12_final_broadcast")),
        CharacterBible("qiao", "乔岑", 46, "harbor_director_antagonist", "控制丑闻扩散", "保住港务体系", ("秩序", "权力"), ("群众得知全貌",), ("误以为主角没有完整账本",), "character_qiao_v1", ("c06_tail", "c10_qiao_offer", "c12_final_broadcast")),
    )
    scenes = tuple(
        SceneBible(scene_id, name, "雾港", "同一暴雨夜至黎明", f"{name}的主轴与出口位置固定",
                   ("保持人物进出方向连续", "关键证据位置不得漂移"), f"scene_{scene_id}_v1",
                   tuple(item.choice_id for item in choices if item.scene_id == scene_id))
        for scene_id, name in scene_specs
    )
    bundle = StoryBibleBundle(package.script_id, package.script_revision, package.package_hash,
                              graph.graph_hash, characters, scenes)
    validate_graph_for_package(graph, package)
    validate_story_bibles(bundle, graph, package)
    return package, graph, bundle
