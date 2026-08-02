schema_version: "1.0"
record_type: "StoragePlacementMatrix"
task_id: "QCLAW-OFFLINE-FIRST-KNOWLEDGE-SYNC-0001-PHASE0"
status: "proposed"

placement:
  source_artifacts:
    description: "原始材料 (不可变)"
    sizes: "文档KB-MB级"
    local: "00-inbox-raw/ (文件系统)"
    private_git: "hash-only reference (NOT the raw file)"
    object_storage: "raw file (if >10MB or binary)"
    supabase: "metadata only (hash, source, license)"
    public_git: "NEVER"

  candidate_packets:
    description: "QCLAW产出的结构化知识包"
    sizes: "每包10-500KB"
    local: "02-candidate-packets/ (JSONL)"
    private_git: "full content (authoritative)"
    object_storage: "not needed (<500KB per packet)"
    supabase: "full text + vector embedding (projection)"
    public_git: "NEVER (private knowledge)"

  knowledge_atoms:
    description: "不可再分的知识单元"
    sizes: "每atom 100B-10KB"
    local: "embedded in LearningPacket JSONL"
    private_git: "embedded in packets (versioned)"
    object_storage: "N/A"
    supabase: "full text index + vector + structured fields"
    public_git: "NEVER"

  relations:
    description: "atom之间的关系边"
    sizes: "每rel 50-500B"
    local: "embedded in LearningPacket"
    private_git: "embedded in packets"
    object_storage: "N/A"
    supabase: "relational tables"
    public_git: "schema only (not data)"

  skills:
    description: "可复用的技能定义"
    sizes: "每skill 1-50KB"
    local: "embedded in LearningPacket"
    private_git: "embedded in packets"
    object_storage: "N/A"
    supabase: "full text index"
    public_git: "schema only"

  manifests:
    description: "哈希/来源/批次清单"
    sizes: "每manifest 1-100KB"
    local: "manifests/ (JSON)"
    private_git: "full content"
    object_storage: "not needed"
    supabase: "not needed"
    public_git: "sanitized summary only"

  state_and_cursors:
    description: "SQLite状态数据库"
    sizes: "初始<1MB, 随packet数增长"
    local: "state/state.sqlite"
    private_git: "backup only (not authoritative)"
    object_storage: "periodic backup"
    supabase: "NEVER"
    public_git: "NEVER"

  large_raw_artifacts:
    description: "PDF/音频/视频/大CSV"
    sizes: "10MB-10GB"
    local: "00-inbox-raw/ or dedicated archive"
    private_git: "NEVER (Git bloat)"
    object_storage: "primary storage"
    supabase: "metadata only"
    public_git: "NEVER"

  logs:
    description: "运行和错误日志"
    sizes: "初始<1MB"
    local: "logs/ (轮转)"
    private_git: "NEVER"
    object_storage: "NEVER"
    supabase: "NEVER"
    public_git: "NEVER"

git_anti_bloat_rules:
  - "单个packet >1MB: 拆分或引用外部存储"
  - "原始二进制: 只存hash+object_id在Git, 本体在对象存储"
  - "Git LFS: 如必须存大文件, 使用LFS track"
  - "定期运行 git gc --aggressive"
  - "单次提交不超过1000个文件"
