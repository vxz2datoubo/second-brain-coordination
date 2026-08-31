# 剧本、互动、导演与媒体契约

本文件定义跨模块的稳定公共接口。所有对象均为 JSON 可序列化数据；未知字段必须被版本化处理，任何版本不匹配必须 fail closed。对象本身不授予外部调用或私有数据读取权限。

## 内容与剧本

### `ScriptPackage/v1`

必填字段：`script_id`、`script_revision`、`genre`、`content_rating`、`season_catalog`、`chapter_catalog`、`scene_catalog`、`world_bible_ref`、`character_bible_refs`、`scene_bible_refs`、`story_beats`、`legal_choices`、`consequence_rules`、`reward_rules`、`ending_rules`、`style_profiles`、`asset_manifest_ref`、`source_provenance`、`approval_status`。

`approval_status` 不是装饰字段：只有 `approved_for_runtime` 的剧本版本才可建立新 campaign。旧合成场景将以一个内置测试剧本包迁入，作为迁移和回放底座。Eustia 仅能在独立来源审查后成为 `private_adaptation` 剧本包，永不作为默认值。

### 内容圣经与资产

- `CharacterBible/v1`：`character_id`、`revision`、`dramatic_want`、`secret_boundary`、`knowledge_boundary`、`relationship_rules`、`appearance_anchor_ref`、`approval_status`。
- `SceneBible/v1`（`ScriptPackage` 内嵌或引用）：`scene_id`、空间、时间、可见物、允许节拍、进入/退出条件和连续性要求。
- `StyleProfile/v1`（`ScriptPackage` 内嵌）：`style_profile_id`、视觉表达规则、声音表达规则、禁止变化、批准状态。风格只能改变渲染表达。
- `AssetApproval/v1`：`asset_ref`、`asset_hash`、`asset_role`、`source_provenance`、`approval_status`、`reviewed_by`、`reviewed_at`。缺失批准资产应产生 `missing_asset`，不得伪造路径。

## 玩家、候选与验证状态

### `PlayerCampaign/v1`

必填：`campaign_id`、`player_private_ref`、`script_id`、`script_revision`、`campaign_status`、`ledger_ref`、`latest_state_hash`、`current_scene_id`、`avatar_revision_refs`、`created_at`。玩家 ID 必须是本地私有引用，GitHub 不保存真实身份。

### `ChoiceIntent/v1`

必填：`intent_id`、`campaign_id`、`source_type`、`source_event_ref`、`normalized_choice_id`、`confidence`、`clarification_required`、`content_gate_status`、`received_at`。自由文本可映射到已批准意图；低置信、歧义、越界或未知输入只能请求澄清/退回可选项。

### `NarrativeProposal/v1`

这是模型或离线模拟器的**候选**，而非事实。必填：`proposal_id`、`campaign_id`、`based_on_state_hash`、`candidate_dialogue`、`candidate_character_reactions`、`candidate_beat_ids`、`candidate_presentation`、`model_or_simulator_ref`、`policy_revision`。禁止包含直接状态写入权限。

### `NarrativeState/v1` 与子状态

`NarrativeState/v1` 持有 `state_hash`、`scene_id`、`beat_id`、`QuestState/v1`、`RewardState/v1`、`RelationshipState/v1`、`EvidenceItem/v1[]`、资源、风险、角色知识边界、flags 与连续性引用。

- `QuestState/v1`：`quest_id`、`phase`、`objectives`、`deadline_or_pressure`、`status`。
- `RewardState/v1`：`reward_id`、`reward_type`、`source_event_id`、`mechanical_or_emotional_effect`、`tradeoff`。
- `RelationshipState/v1`：`character_id`、`trust`、`conflict`、`commitment`、`known_by_character`。
- `EvidenceItem/v1`：`evidence_id`、`source_event_id`、`fact`、`visibility`、`confidence`、`tamper_hash`。
- `DramaticBeatSelection/v1`：`selection_id`、`campaign_id`、`eligible_beat_ids`、`selected_beat_id`、`selection_reason`、`preserved_player_facts_hash`、`policy_revision`。

验证器逐项确认：选择合法、前置状态相等、角色知情边界、资源/风险/奖励规则、节拍可达性、内容等级、每个主选择至少一项真实后果及追加式哈希链。一项失败即拒绝整个变化。

## 私有外貌与连续性

- `AvatarIdentity/v1`：`avatar_id`、`private_owner_ref`、`consent_revision`、`first_approved_asset_ref`、`identity_status`。只存本地私有引用。
- `AvatarRevision/v1`：`avatar_revision_id`、`avatar_id`、`private_asset_ref`、`approval_ref`、`effective_from_event_id`、`replacement_reason`。原因 `appearance_change` 要求显式“整容 + 角色 + 新图片”命令。
- `CharacterAppearanceAnchor/v1`：`character_id`、`anchor_revision`、服装、道具、伤势、情绪和已批准参考的私有/可共享受控引用。
- `AppearanceContinuityRecord/v1`：`segment_id`、`campaign_id`、`cast_revision_ids`、`wardrobe_refs`、`prop_refs`、`injury_state`、`space_state`、`continuity_ledger_hash`、`validation_status`。

历史 `CinematicSegment` 的 cast revision 一经完成不可替换。私有资产缓存键必须包含 `campaign_id` 和 avatar revision，不得跨玩家使用。

## 导演、镜头与媒体

### `DirectorBrief/v2`

必填：`script_id`、`script_revision`、`campaign_id`、`verified_story_state_hash`、`style_profile_id`、`cast_revision_ids`、`scene_asset_refs`、`continuity_ledger_hash`、`director_policy_revision`、剧情事实、角色目标/知情边界、空间关系、镜头责任、内容限制。

### `ShotBundle/v1` 与 `CinematicSegment/v1`

`ShotBundle/v1`：`bundle_id`、`director_brief_hash`、`shots[]`、动作线、机位、轴线、表演任务、灯光、声音、时长、参考资产职责。硬门检查身份、空间连续、轴线、知情边界、动作因果、内容、资产职责、主导变化与时长。

`CinematicSegment/v1`：`segment_id`、`campaign_id`、`shot_bundle_hash`、`duration_seconds`、`audio_plan`、`style_profile_id`、`continuity_record_ref`、`generation_authorization_status`。未来真实段以 4–15 秒为目标；当前仅允许 deterministic offline segment。

### `MediaJob/v1`、`MediaResult/v1`、`MediaQualityReport/v1`

`MediaJob/v1`：`job_id`、`request_hash`、`segment_ref`、`provider_adapter`、`confirmation_status`、`budget_gate_ref`、`idempotency_key`、`status`。未确认/未过质量门/无预算门时禁止外发。

`MediaResult/v1`：`job_id`、`provider_ref`、`result_ref`、`result_hash`、`created_at`、`status`、`failure_reason`。失败不得自动消耗性重试。

`MediaQualityReport/v1`：`job_id`、`identity_check`、`continuity_check`、`content_check`、`audio_check`、`policy_check`、`verdict`、`evidence_refs`。当前离线适配器可产出确定性模拟结果与报告；真实结果仅在 A5。

## 运营与抖音

- `ManualIntake/v1`：`intake_id`、`campaign_id`、`operator_ref`、`text_input_ref`、`private_image_ref`、`consent_revision`、`status`。
- `DouyinCommentIngest/v1`：`ingest_id`、`platform_comment_ref`、`comment_text_hash`、`received_at`、`dedup_key`、`campaign_routing_status`。不存真实评论文本于 GitHub。
- `DouyinImageCapabilityGate/v1`：`gate_id`、`official_capability_ref`、`permission_status`、`observed_fields`、`image_path_enabled`、`fallback_notification_status`。默认 `image_path_enabled=false`。

## 第二大脑候选

- `CreativeKnowledgeCandidate/v1`：来源事件和证据哈希、候选规则、范围、置信度、状态。
- `CorrectionProposal/v1`：可审计纠正、提出者、目标、理由和证据。
- `HumanReviewDecision/v1`：审核人、决定、时间、证据、适用范围。
- `ReusableSkillCandidate/v1`：只有关联 `HumanReviewDecision/v1` 的批准结论，才可成为可复用技能候选。

生成结果、玩家偏好、导演解释都不能改写历史事实或自动升级为正式知识。
