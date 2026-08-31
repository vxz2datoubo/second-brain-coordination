from mids_opportunity_detector import detect_mids_opportunity


def test_original_style_vague_project_need_is_high():
    result = detect_mids_opportunity(
        "我有很多想法和思路，但不知道具体怎么落地，也没办法像程序员一样把需求说清楚，想让AI不断问我一起确认整体方向。",
        material_project_decision=True,
        unresolved_dependencies=True,
    )
    assert result.level == "HIGH"


def test_world_design_expert_blind_zone_is_high():
    result = detect_mids_opportunity(
        "我想做一个AI世界，但不知道能力系统应该怎么设计，你帮我一起推演有没有更好的方向。",
        material_project_decision=True,
    )
    assert result.level == "HIGH"


def test_small_open_design_request_is_medium():
    result = detect_mids_opportunity("我想增加一个功能，大概应该怎么设计比较好？")
    assert result.level == "MEDIUM"


def test_simple_translation_stays_low():
    result = detect_mids_opportunity("把这句话翻译成英文。")
    assert result.level == "LOW"


def test_precise_spec_can_bypass_discovery():
    result = detect_mids_opportunity(
        "按照已经确认的规格实现这个函数。",
        explicit_spec_is_sufficient=True,
        material_project_decision=True,
    )
    assert result.level == "LOW"


def test_explicit_rejection_is_suppressed():
    result = detect_mids_opportunity(
        "这个任务不要问我，直接执行。",
        material_project_decision=True,
        unresolved_dependencies=True,
    )
    assert result.level == "SUPPRESSED"


def test_declined_slice_remains_suppressed():
    result = detect_mids_opportunity(
        "我又想到一个方向。",
        material_project_decision=True,
        user_declined_for_slice=True,
    )
    assert result.level == "SUPPRESSED"


def test_forgotten_method_name_not_required():
    result = detect_mids_opportunity(
        "我不一定知道最后要做成什么样，你先帮我想一想，然后通过提问把需求弄清楚。",
        material_project_decision=True,
    )
    assert result.level == "HIGH"
    assert "MIDS" not in "我不一定知道最后要做成什么样，你先帮我想一想，然后通过提问把需求弄清楚。"
