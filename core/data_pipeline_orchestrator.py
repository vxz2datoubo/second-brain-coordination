#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二大脑 · 统一数据管道调度器 (Data Pipeline Orchestrator)
═══════════════════════════════════════════════════════════

核心职责:
  1. 管理三源数据 (Tushare/TDX/WeStock) 的统一索引
  2. 提供统一加载接口——任意模块通过 dataset_id 即可获取数据
  3. 技能↔数据集映射——什么技能需要什么数据、从哪里加载
  4. 数据质量校验——完整性、时效性、格式一致性
  5. 自动归集——新数据落盘后自动更新 manifest

架构:
  DataRegistry  ───  manifest.json (主索引)
  UnifiedLoader  ───  统一加载接口 (懒加载 + 缓存)
  SkillMapper    ───  skill_data_map.json (技能→数据映射)
  Validator      ───  数据质量检查
  SyncEngine     ───  增量同步 + 自动归集

目录结构:
  data/unified/
  ├── manifest.json           # 主索引: 所有数据集的元信息
  ├── skill_data_map.json     # 技能↔数据集映射
  ├── reference/              # 参考数据(股票列表/板块映射)
  │   ├── stock_list.json
  │   └── sector_map.json
  ├── snapshots/              # WeStock 实时查询快照
  │   ├── hot_news/
  │   └── sector_ranking/
  └── _cache/                 # 加载缓存(按需)
"""

import json, os, time, glob as glob_mod
from datetime import datetime, timedelta
from typing import Optional, Any
from collections import OrderedDict

# ═══════════════════════════════════════════════════════════
# 路径常量
# ═══════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw", "tushare")
UNIFIED_DIR = os.path.join(BASE_DIR, "data", "unified")
MANIFEST_PATH = os.path.join(UNIFIED_DIR, "manifest.json")
SKILL_MAP_PATH = os.path.join(UNIFIED_DIR, "skill_data_map.json")
CACHE_DIR = os.path.join(UNIFIED_DIR, "_cache")
SNAPSHOT_DIR = os.path.join(UNIFIED_DIR, "snapshots")
REFERENCE_DIR = os.path.join(UNIFIED_DIR, "reference")

# ═══════════════════════════════════════════════════════════
# 统一数据格式定义 (Schema v1.0)
# ═══════════════════════════════════════════════════════════
UNIFIED_SCHEMA_VERSION = "1.0"

# 字段映射: 将各数据源的字段名归一化到统一字段
FIELD_MAP = {
    "daily": {
        # tushare原始字段 → 统一字段
        "ts_code": "code",
        "trade_date": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "pre_close": "pre_close",
        "change": "change",
        "pct_chg": "pct_change",
        "vol": "volume",
        "amount": "amount",
    },
    "moneyflow": {
        "trade_date": "date",
        "buy_sm_vol": "buy_small",      # 小单买入
        "sell_sm_vol": "sell_small",     # 小单卖出
        "buy_md_vol": "buy_medium",      # 中单买入
        "sell_md_vol": "sell_medium",    # 中单卖出
        "buy_lg_vol": "buy_large",       # 大单买入
        "sell_lg_vol": "sell_large",     # 大单卖出
        "buy_elg_vol": "buy_xlarge",     # 超大单买入
        "sell_elg_vol": "sell_xlarge",   # 超大单卖出
        "net_mf_vol": "net_flow",        # 净流入
        "net_mf_amount": "net_amount",   # 净流入额
    },
}

# 已知的数据集定义——每个数据集有唯一 ID、来源、字段列表
DATASET_REGISTRY = OrderedDict()


# ═══════════════════════════════════════════════════════════
# 1. DataRegistry — 数据集注册与索引
# ═══════════════════════════════════════════════════════════

class DataRegistry:
    """管理所有数据集的元信息索引。"""

    def __init__(self):
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        if os.path.exists(MANIFEST_PATH):
            with open(MANIFEST_PATH, encoding="utf-8") as f:
                return json.load(f)
        return {"schema_version": UNIFIED_SCHEMA_VERSION, "datasets": {}, "meta": {}}

    def _save_manifest(self):
        os.makedirs(UNIFIED_DIR, exist_ok=True)
        self.manifest["meta"]["updated"] = datetime.now().isoformat()
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)

    def register(self, dataset_id: str, **meta):
        """注册或更新一个数据集。

        meta 必填字段:
          - source: "tushare" | "tdx" | "westock"
          - data_type: "daily_kline" | "moneyflow" | "index" | "sector" | "news" | "reference"
          - file_path: 相对于 BASE_DIR 的路径
          - fields: 字段列表
          - frequency: "daily" | "weekly" | "realtime" | "static"
        可选:
          - stock_code: 股票代码
          - date_range: [start, end]
          - record_count: 记录数
          - update_frequency: "daily" | "weekly" | "manual"
        """
        meta["registered_at"] = datetime.now().isoformat()
        meta["schema_version"] = UNIFIED_SCHEMA_VERSION
        self.manifest["datasets"][dataset_id] = meta
        self._save_manifest()
        return dataset_id

    def get(self, dataset_id: str) -> Optional[dict]:
        return self.manifest["datasets"].get(dataset_id)

    def list_datasets(self, source: str = None, data_type: str = None, stock_code: str = None) -> list:
        """按条件列出数据集。"""
        result = []
        for dsid, meta in self.manifest["datasets"].items():
            if source and meta.get("source") != source:
                continue
            if data_type and meta.get("data_type") != data_type:
                continue
            if stock_code and meta.get("stock_code") != stock_code:
                continue
            result.append((dsid, meta))
        return result

    def auto_discover(self):
        """自动扫描 raw/ 目录，发现未注册的数据集。"""
        if not os.path.exists(RAW_DIR):
            return 0

        discovered = 0
        for fname in os.listdir(RAW_DIR):
            if not fname.endswith(".json"):
                continue
            if fname.startswith("_"):  # 跳过状态文件
                continue

            filepath = os.path.join(RAW_DIR, fname)
            dataset_id = fname.replace(".json", "")

            # 推断元信息
            meta = self._infer_meta(dataset_id, filepath)
            if meta and dataset_id not in self.manifest["datasets"]:
                self.register(dataset_id, **meta)
                discovered += 1

        return discovered

    def _infer_meta(self, dataset_id: str, filepath: str) -> Optional[dict]:
        """从文件名和数据内容推断数据集元信息。"""
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list) or not data:
                return None

            record_count = len(data)
            first = data[0] if isinstance(data[0], list) else list(data[0].values())
            last = data[-1] if isinstance(data[-1], list) else list(data[-1].values())

            # 按命名规则推断
            meta = {
                "source": "tushare",
                "file_path": os.path.relpath(filepath, BASE_DIR),
                "record_count": record_count,
            }

            # index_XXXXXX_daily
            if dataset_id.startswith("index_"):
                parts = dataset_id.replace("index_", "").split("_")
                meta.update({
                    "data_type": "index",
                    "index_code": parts[0],
                    "frequency": "daily",
                    "update_frequency": "daily",
                })
                if len(parts) > 1 and parts[-1] == "basic":
                    meta["data_type"] = "index_basic"
                return meta

            # stock code pattern: 6 digits
            code = None
            for part in dataset_id.split("_"):
                if part.isdigit() and len(part) == 6:
                    code = part
                    break

            if code:
                meta["stock_code"] = code
                meta["update_frequency"] = "daily"

                if dataset_id.endswith("_daily"):
                    meta["data_type"] = "daily_kline"
                    meta["frequency"] = "daily"
                elif dataset_id.endswith("_daily_basic"):
                    meta["data_type"] = "daily_basic"
                    meta["frequency"] = "daily"
                elif dataset_id.endswith("_moneyflow"):
                    meta["data_type"] = "moneyflow"
                    meta["frequency"] = "daily"
                elif dataset_id.endswith("_fina_indicator"):
                    meta["data_type"] = "financial"
                    meta["frequency"] = "quarterly"
                elif "holdernumber" in dataset_id:
                    meta["data_type"] = "chip"
                    meta["frequency"] = "monthly"

            # concept_flow / industry_flow
            if dataset_id in ("concept_flow", "industry_flow"):
                meta["data_type"] = "sector_flow"
                meta["frequency"] = "daily"

            return meta
        except Exception:
            return None

    def get_stats(self) -> dict:
        """返回数据集统计概览。"""
        ds = self.manifest["datasets"]
        from collections import Counter
        sources = Counter(v.get("source") for v in ds.values())
        types = Counter(v.get("data_type") for v in ds.values())
        total_records = sum(v.get("record_count", 0) for v in ds.values())
        return {
            "total_datasets": len(ds),
            "total_records": total_records,
            "by_source": dict(sources),
            "by_type": dict(types),
            "last_updated": self.manifest["meta"].get("updated"),
        }

    def ensure_dir(self):
        """确保所有统一目录存在。"""
        for d in [UNIFIED_DIR, CACHE_DIR, SNAPSHOT_DIR, REFERENCE_DIR,
                  os.path.join(SNAPSHOT_DIR, "hot_news"),
                  os.path.join(SNAPSHOT_DIR, "sector_ranking")]:
            os.makedirs(d, exist_ok=True)


# ═══════════════════════════════════════════════════════════
# 2. UnifiedLoader — 统一加载接口
# ═══════════════════════════════════════════════════════════

class UnifiedLoader:
    """通过 dataset_id 加载任意数据，带懒加载缓存。"""

    def __init__(self, registry: DataRegistry):
        self.registry = registry
        self._cache = {}
        self._cache_max = 20  # 最多缓存 20 个数据集

    def load(self, dataset_id: str, force_reload: bool = False) -> Optional[list]:
        """加载指定数据集。

        Returns:
            list of dict: 每条记录的字典列表（已做字段归一化）
            如果数据集不存在或文件缺失，返回 None
        """
        # 缓存命中
        if not force_reload and dataset_id in self._cache:
            return self._cache[dataset_id]

        meta = self.registry.get(dataset_id)
        if not meta:
            print(f"[Orchestrator] 数据集 {dataset_id} 未注册")
            return None

        filepath = os.path.join(BASE_DIR, meta["file_path"])
        if not os.path.exists(filepath):
            print(f"[Orchestrator] 文件不存在: {filepath}")
            return None

        try:
            with open(filepath, encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"[Orchestrator] 加载失败 {dataset_id}: {e}")
            return None

        # 如果已经是 dict 格式（如 concept_flow），直接返回
        if isinstance(raw, dict) and "data" not in raw:
            # 可能是 {date: values} 格式，直接返回
            pass

        # 应用字段映射
        data_type = meta.get("data_type", "")
        if data_type in FIELD_MAP and isinstance(raw, list) and raw:
            raw = self._normalize_fields(raw, data_type)

        # 缓存
        if len(self._cache) >= self._cache_max:
            # 淘汰最旧的
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[dataset_id] = raw

        return raw

    def _normalize_fields(self, data: list, data_type: str) -> list:
        """将原始字段名归一化为统一字段名。"""
        mapping = FIELD_MAP.get(data_type, {})
        if not mapping or not data:
            return data

        # 检测格式: list of lists or list of dicts
        normalized = []
        for row in data:
            if isinstance(row, list):
                # 旧格式: list of lists —— 不做归一化，tag 格式标记
                normalized.append(row)
            elif isinstance(row, dict):
                new_row = {}
                for old_key, val in row.items():
                    new_key = mapping.get(old_key, old_key)
                    new_row[new_key] = val
                normalized.append(new_row)
        return normalized

    def load_multi(self, dataset_ids: list, force_reload: bool = False) -> dict:
        """批量加载多个数据集。

        Returns:
            {dataset_id: data | None}
        """
        return {dsid: self.load(dsid, force_reload) for dsid in dataset_ids}

    def load_for_skill(self, skill_name: str) -> dict:
        """根据技能名加载其所需的所有数据。

        Returns:
            {dataset_id: data | None}
        """
        mapper = SkillMapper()
        deps = mapper.get_required_data(skill_name)
        return self.load_multi(deps)

    def latest_date(self, dataset_id: str) -> Optional[str]:
        """获取数据集的最新日期。"""
        data = self.load(dataset_id)
        if not data:
            return None
        meta = self.registry.get(dataset_id)
        data_type = meta.get("data_type", "") if meta else ""
        if isinstance(data, list) and data:
            row = data[-1]
            if isinstance(row, list):
                # 按数据类型确定日期字段位置
                # daily/daily_basic: 日期在 index 1
                # moneyflow: 日期在 index 0
                date_idx = 0 if data_type in ("moneyflow", "chip") else 1
                if len(row) > date_idx:
                    raw = str(row[date_idx])
                    # 验证是否像日期格式 YYYYMMDD
                    if len(raw) >= 8 and raw[:4].isdigit() and int(raw[:4]) > 2000:
                        return raw[:8]
                # 回退: 遍历找第一个像日期的字段
                for val in row:
                    s = str(val)
                    if len(s) >= 8 and s[:4].isdigit() and 2000 < int(s[:4]) < 2100:
                        return s[:8]
            if isinstance(row, dict):
                return row.get("date") or row.get("trade_date")
        return None

    def data_freshness(self, dataset_id: str) -> dict:
        """检查数据新鲜度。"""
        meta = self.registry.get(dataset_id)
        latest = self.latest_date(dataset_id)
        stale = False
        days_behind = None

        if latest and meta:
            freq = meta.get("frequency", "daily")
            try:
                latest_dt = datetime.strptime(str(latest)[:8], "%Y%m%d")
                now = datetime.now()
                days_behind = (now - latest_dt).days
                if freq == "daily" and days_behind > 2:
                    stale = True
                elif freq == "weekly" and days_behind > 10:
                    stale = True
            except Exception:
                pass

        return {
            "dataset_id": dataset_id,
            "latest_date": latest,
            "days_behind": days_behind,
            "stale": stale,
            "record_count": meta.get("record_count") if meta else None,
        }

    def invalidate_cache(self, dataset_id: str = None):
        """使缓存失效。"""
        if dataset_id:
            self._cache.pop(dataset_id, None)
        else:
            self._cache.clear()


# ═══════════════════════════════════════════════════════════
# 3. SkillMapper — 技能↔数据集映射
# ═══════════════════════════════════════════════════════════

class SkillMapper:
    """管理技能与所需数据集之间的映射关系。"""

    def __init__(self):
        self.mapping = self._load_mapping()

    def _load_mapping(self) -> dict:
        if os.path.exists(SKILL_MAP_PATH):
            with open(SKILL_MAP_PATH, encoding="utf-8") as f:
                return json.load(f)
        return self._default_mapping()

    def _default_mapping(self) -> dict:
        """内置默认映射——覆盖所有核心技能的数据需求。"""
        return {
            # ── 持仓分析 ──
            "volume-profile-chip": {
                "required": ["300418_daily", "300058_daily"],
                "optional": ["300418_moneyflow", "300058_moneyflow"],
                "frequency": "daily",
                "description": "Volume Profile + 筹码分布——需要日K和资金流数据",
            },
            "vwap-analyzer": {
                "required": ["300418_daily", "300058_daily"],
                "optional": [],
                "frequency": "intraday",
                "description": "VWAP/AVWAP分析——需要日K（做锚定）和盘中实时价",
            },
            "anchoring-detection": {
                "required": ["300418_daily", "300058_daily"],
                "optional": ["300418_moneyflow", "300058_moneyflow"],
                "frequency": "daily",
                "description": "散户锚定检测——需要日K和资金流对比",
            },
            "t1-lockup-tracking": {
                "required": ["300418_daily", "300058_daily"],
                "optional": ["300418_moneyflow", "300058_moneyflow"],
                "frequency": "daily",
                "description": "T+1锁仓追踪——需要日K+换手率+资金流",
            },
            # ── 市场全景 ──
            "market-perception": {
                "required": ["index_000001_daily", "index_000300_daily"],
                "optional": ["concept_flow", "industry_flow", "ths_hot_concept", "ths_hot_industry"],
                "frequency": "daily",
                "description": "全局盘面感知——需要指数数据+板块数据",
            },
            "market-context": {
                "required": ["index_000001_daily", "index_000300_daily", "index_399006_daily"],
                "optional": ["concept_flow", "ths_hot_concept"],
                "frequency": "daily",
                "description": "市场环境分析——需要三大指数+板块共振",
            },
            "market-panic-index": {
                "required": ["index_000001_daily", "index_000300_daily"],
                "optional": [],
                "frequency": "daily",
                "description": "恐慌指数——需要大盘指数涨跌分布",
            },
            # ── 资金流 ──
            "money-flow-warfare": {
                "required": ["300418_moneyflow", "300058_moneyflow"],
                "optional": ["concept_flow"],
                "frequency": "daily",
                "description": "资金博弈——需要个股+板块资金流",
            },
            "money-flow-divergence": {
                "required": ["300418_daily", "300418_moneyflow"],
                "optional": [],
                "frequency": "daily",
                "description": "资金流背离——需要日K+资金流对比",
            },
            "fund-pool-tracker": {
                "required": ["300418_moneyflow", "300058_moneyflow"],
                "optional": [],
                "frequency": "daily",
                "description": "资金池追踪——需要四渠道资金流数据",
            },
            # ── 技术分析 ──
            "cause-effect-projection": {
                "required": ["300418_daily", "300058_daily"],
                "optional": [],
                "frequency": "daily",
                "description": "威科夫因果法则——需要日K计算横盘区间",
            },
            "supply-test": {
                "required": ["300418_daily", "300058_daily"],
                "optional": ["300418_moneyflow", "300058_moneyflow"],
                "frequency": "daily",
                "description": "供应测试——需要日K+量价关系",
            },
            "phase-c-d-transition": {
                "required": ["300418_daily", "300058_daily"],
                "optional": [],
                "frequency": "daily",
                "description": "C-D阶段转换——需要日K识别结构转换",
            },
            # ── 板块/选股 ──
            "sector-flow-radar": {
                "required": ["concept_flow", "industry_flow"],
                "optional": ["ths_hot_concept", "ths_hot_industry"],
                "frequency": "daily",
                "description": "板块资金雷达——需要全市场板块资金流",
            },
            "sector-rotation-detection": {
                "required": ["concept_flow", "industry_flow"],
                "optional": ["ths_hot_concept"],
                "frequency": "daily",
                "description": "板块轮动检测——需要板块资金流+热度排行",
            },
            "cross-stock-scanner": {
                "required": ["300418_daily", "300058_daily"],
                "optional": [],
                "frequency": "daily",
                "description": "全市场对标扫描——需要持仓标的数据做基准",
            },
            # ── 新闻/事件 ──
            "high-value-alert": {
                "required": [],
                "optional": [],
                "frequency": "realtime",
                "description": "高价值消息预警——主要依赖WeStock MCP实时查询",
            },
            "news-catalyst-monitor": {
                "required": [],
                "optional": [],
                "frequency": "realtime",
                "description": "新闻催化剂监控——依赖WeStock data_news",
            },
            # ── 基本面 ──
            "fundamental-quick-view": {
                "required": ["300418_fina_indicator", "300058_fina_indicator"],
                "optional": ["300418_share_float", "300058_share_float"],
                "frequency": "quarterly",
                "description": "快速基本面——需要财务指标+流通股本",
            },
            "lockup-depth-analysis": {
                "required": ["300418_share_float", "300058_share_float"],
                "optional": ["300418_fina_indicator", "300058_fina_indicator"],
                "frequency": "quarterly",
                "description": "锁仓深度分析——需要股本结构+股东数据",
            },
        }

    def save_default(self):
        """保存默认映射到磁盘。"""
        os.makedirs(UNIFIED_DIR, exist_ok=True)
        with open(SKILL_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(self._default_mapping(), f, ensure_ascii=False, indent=2)

    def get_required_data(self, skill_name: str) -> list:
        """获取某技能所需的数据集列表。"""
        skill = self.mapping.get(skill_name, {})
        return skill.get("required", [])

    def get_all_deps(self, skill_name: str) -> list:
        """获取所有依赖（required + optional）。"""
        skill = self.mapping.get(skill_name, {})
        return skill.get("required", []) + skill.get("optional", [])

    def get_skill_info(self, skill_name: str) -> Optional[dict]:
        return self.mapping.get(skill_name)

    def list_skills(self) -> list:
        return sorted(self.mapping.keys())

    def skills_needing_dataset(self, dataset_id: str) -> list:
        """反向查询：哪些技能需要这个数据集？"""
        result = []
        for skill, deps in self.mapping.items():
            all_deps = deps.get("required", []) + deps.get("optional", [])
            if dataset_id in all_deps:
                result.append(skill)
        return result


# ═══════════════════════════════════════════════════════════
# 4. Validator — 数据质量校验
# ═══════════════════════════════════════════════════════════

class Validator:
    """数据质量检查——完整性、时效性、格式正确性。"""

    def __init__(self, registry: DataRegistry, loader: UnifiedLoader):
        self.registry = registry
        self.loader = loader

    def check_all_freshness(self) -> list:
        """检查所有已注册数据集的新鲜度。"""
        results = []
        for dataset_id in self.registry.manifest["datasets"]:
            result = self.loader.data_freshness(dataset_id)
            results.append(result)
        return results

    def check_stale(self) -> list:
        """返回所有数据过期的数据集。"""
        return [r for r in self.check_all_freshness() if r["stale"]]

    def check_completeness(self, dataset_id: str) -> dict:
        """检查一个数据集的时间连续性。"""
        data = self.loader.load(dataset_id)
        if not data:
            return {"dataset_id": dataset_id, "status": "missing", "gaps": []}

        # 提取日期序列
        dates = []
        for row in data:
            if isinstance(row, list) and len(row) > 1:
                dates.append(str(row[1]))
            elif isinstance(row, dict):
                d = row.get("date") or row.get("trade_date")
                if d:
                    dates.append(str(d))

        if len(dates) < 2:
            return {"dataset_id": dataset_id, "status": "ok", "gaps": []}

        # 检测断档（超过3天的间隔）
        gaps = []
        try:
            parsed = sorted(set(datetime.strptime(d[:8], "%Y%m%d") for d in dates if len(d) >= 8))
            for i in range(1, len(parsed)):
                diff = (parsed[i] - parsed[i - 1]).days
                if diff > 3:
                    gaps.append({
                        "from": parsed[i - 1].strftime("%Y-%m-%d"),
                        "to": parsed[i].strftime("%Y-%m-%d"),
                        "gap_days": diff,
                    })
        except Exception:
            pass

        return {
            "dataset_id": dataset_id,
            "status": "gaps_found" if gaps else "ok",
            "total_dates": len(dates),
            "gaps": gaps,
        }

    def check_holdings_freshness(self) -> list:
        """专项检查：持仓股数据是否最新。"""
        holdings = ["300418_daily", "300058_daily", "300418_moneyflow", "300058_moneyflow"]
        results = []
        for dsid in holdings:
            f = self.loader.data_freshness(dsid)
            results.append(f)
        return results

    def report(self) -> str:
        """生成质量报告。"""
        fresh = self.check_all_freshness()
        stale = [f for f in fresh if f["stale"]]
        lines = [
            "=" * 50,
            "  数据质量报告",
            f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 50,
            f"\n总数据集: {len(fresh)}",
            f"数据过期: {len(stale)}",
        ]
        if stale:
            lines.append("\n⚠️ 过期数据集:")
            for s in stale:
                lines.append(f"  - {s['dataset_id']}: 滞后 {s['days_behind']} 天")
        else:
            lines.append("\n✅ 所有数据新鲜。")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 5. SyncEngine — 增量同步与自动归集
# ═══════════════════════════════════════════════════════════

class SyncEngine:
    """处理增量数据同步——新数据落盘后自动更新 manifest。"""

    def __init__(self, registry: DataRegistry, loader: UnifiedLoader):
        self.registry = registry
        self.loader = loader

    def full_sync(self) -> dict:
        """全量同步：扫描 raw/ 目录，注册所有未注册数据集。"""
        discovered = self.registry.auto_discover()
        return {
            "discovered": discovered,
            "total": len(self.registry.manifest["datasets"]),
            "stats": self.registry.get_stats(),
        }

    def incremental_sync(self, dataset_ids: list = None) -> dict:
        """增量同步：刷新指定数据集的最新日期和记录数。

        如果 dataset_ids 为 None，则刷新所有数据集。
        """
        updated = []
        targets = dataset_ids or list(self.registry.manifest["datasets"].keys())

        for dsid in targets:
            meta = self.registry.get(dsid)
            if not meta:
                continue
            filepath = os.path.join(BASE_DIR, meta["file_path"])
            if not os.path.exists(filepath):
                continue

            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)

                new_count = len(data) if isinstance(data, list) else len(data)
                if new_count != meta.get("record_count"):
                    self.registry.register(dsid, **{**meta, "record_count": new_count})
                    updated.append({"dataset_id": dsid, "old_count": meta.get("record_count"), "new_count": new_count})
            except Exception:
                continue

        return {"updated": len(updated), "details": updated}

    def build_reference_data(self):
        """构建参考数据集（股票列表、板块映射）。"""
        os.makedirs(REFERENCE_DIR, exist_ok=True)

        # 股票列表 — 从已拉取的 stock_basic 提取
        stock_list_path = os.path.join(RAW_DIR, "stock_basic.json")
        if os.path.exists(stock_list_path):
            try:
                stocks = json.load(open(stock_list_path, encoding="utf-8"))
                ref = []
                for s in stocks:
                    if isinstance(s, list) and len(s) >= 3:
                        ref.append({"code": str(s[0]).replace(".SZ", "").replace(".SH", ""),
                                    "name": str(s[2])})
                    elif isinstance(s, dict):
                        ref.append({"code": s.get("ts_code", "").replace(".SZ", "").replace(".SH", ""),
                                    "name": s.get("name", "")})
                with open(os.path.join(REFERENCE_DIR, "stock_list.json"), "w", encoding="utf-8") as f:
                    json.dump(ref, f, ensure_ascii=False, indent=2)
                print(f"[SyncEngine] 股票列表已构建: {len(ref)} 只")
            except Exception as e:
                print(f"[SyncEngine] 构建股票列表失败: {e}")

        # 板块映射 — 从 concept_to_stocks 提取
        concept_path = os.path.join(RAW_DIR, "concept_to_stocks.json")
        if os.path.exists(concept_path):
            try:
                concepts = json.load(open(concept_path, encoding="utf-8"))
                sector_map = {}
                for concept_name, stock_list in concepts.items():
                    sector_map[concept_name] = [s.split(".")[0] if "." in str(s) else str(s) for s in stock_list]
                with open(os.path.join(REFERENCE_DIR, "sector_map.json"), "w", encoding="utf-8") as f:
                    json.dump(sector_map, f, ensure_ascii=False, indent=2)
                print(f"[SyncEngine] 板块映射已构建: {len(sector_map)} 个概念")
            except Exception as e:
                print(f"[SyncEngine] 构建板块映射失败: {e}")


# ═══════════════════════════════════════════════════════════
# 6. Orchestrator — 总调度器
# ═══════════════════════════════════════════════════════════

class DataPipelineOrchestrator:
    """统一入口——组合所有子模块。

    用法:
        orch = DataPipelineOrchestrator()
        orch.init()                           # 首次初始化: 建目录+注册+构建参考数据
        data = orch.load("300418_daily")      # 加载数据
        fresh = orch.check_freshness()        # 检查新鲜度
        deps = orch.get_skill_data("volume-profile-chip")  # 获取技能所需数据
    """

    def __init__(self):
        self.registry = DataRegistry()
        self.loader = UnifiedLoader(self.registry)
        self.mapper = SkillMapper()
        self.validator = Validator(self.registry, self.loader)
        self.sync = SyncEngine(self.registry, self.loader)

    def init(self, force_full_sync: bool = False):
        """初始化——首次运行或强制全量同步时调用。"""
        self.registry.ensure_dir()
        if force_full_sync or not self.registry.manifest["datasets"]:
            print("[Orchestrator] 执行全量同步...")
            result = self.sync.full_sync()
            print(f"[Orchestrator] 发现 {result['discovered']} 个新数据集，总计 {result['total']} 个")
        self.mapper.save_default()
        self.sync.build_reference_data()
        stats = self.registry.get_stats()
        print(f"[Orchestrator] 初始化完成: {stats['total_datasets']} 数据集, {stats['total_records']} 条记录")

    def load(self, dataset_id: str, force_reload: bool = False):
        """加载单个数据集。"""
        return self.loader.load(dataset_id, force_reload)

    def load_multi(self, dataset_ids: list, force_reload: bool = False) -> dict:
        """批量加载多个数据集。"""
        return self.loader.load_multi(dataset_ids, force_reload)

    def load_for_skill(self, skill_name: str) -> dict:
        """加载某技能所需的所有数据。"""
        return self.loader.load_for_skill(skill_name)

    def check_freshness(self) -> list:
        """检查所有数据新鲜度。"""
        return self.validator.check_all_freshness()

    def check_stale(self) -> list:
        """返回过期数据集列表。"""
        return self.validator.check_stale()

    def check_holdings(self) -> list:
        """检查持仓股数据新鲜度。"""
        return self.validator.check_holdings_freshness()

    def quality_report(self) -> str:
        """生成数据质量报告。"""
        return self.validator.report()

    def sync_incremental(self, dataset_ids: list = None) -> dict:
        """增量同步。"""
        return self.sync.incremental_sync(dataset_ids)

    def get_skill_deps(self, skill_name: str) -> list:
        """获取某技能的数据依赖。"""
        return self.mapper.get_all_deps(skill_name)

    def get_skills_for_dataset(self, dataset_id: str) -> list:
        """反向查询：哪些技能需要这个数据集。"""
        return self.mapper.skills_needing_dataset(dataset_id)

    def stats(self) -> dict:
        """获取统计概览。"""
        return self.registry.get_stats()


# ═══════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    orch = DataPipelineOrchestrator()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "init":
        force = "--force" in sys.argv
        orch.init(force_full_sync=force)

    elif cmd == "stats":
        print(json.dumps(orch.stats(), ensure_ascii=False, indent=2))

    elif cmd == "freshness":
        stale = orch.check_stale()
        if stale:
            print(f"⚠️ {len(stale)} 个数据集过期:")
            for s in stale:
                print(f"  {s['dataset_id']}: 滞后 {s['days_behind']} 天 (最新: {s['latest_date']})")
        else:
            print("✅ 所有数据新鲜。")

    elif cmd == "holdings":
        for f in orch.check_holdings():
            tag = "⚠️ 过期" if f["stale"] else "✅"
            print(f"  {tag} {f['dataset_id']}: 最新 {f['latest_date']}, {f['record_count']} 条")

    elif cmd == "sync":
        result = orch.sync_incremental()
        print(f"增量同步完成: 更新 {result['updated']} 个")

    elif cmd == "quality":
        print(orch.quality_report())

    elif cmd == "skill-deps":
        skill = sys.argv[2] if len(sys.argv) > 2 else None
        if skill:
            deps = orch.get_skill_deps(skill)
            print(f"{skill}: 需要 {deps}")
        else:
            for s in orch.mapper.list_skills():
                deps = orch.get_skill_deps(s)
                print(f"{s}: {deps}")

    elif cmd == "dataset-skills":
        dsid = sys.argv[2] if len(sys.argv) > 2 else None
        if dsid:
            skills = orch.get_skills_for_dataset(dsid)
            print(f"{dsid} → 被以下技能依赖: {skills}")
        else:
            print("用法: python data_pipeline_orchestrator.py dataset-skills <dataset_id>")

    elif cmd == "load":
        dsid = sys.argv[2] if len(sys.argv) > 2 else None
        if dsid:
            data = orch.load(dsid)
            if data:
                print(f"{dsid}: {len(data)} 条记录")
                if isinstance(data, list) and data:
                    print(f"  首条: {data[0]}")
                    print(f"  末条: {data[-1]}")
            else:
                print(f"{dsid}: 无数据")
        else:
            print("用法: python data_pipeline_orchestrator.py load <dataset_id>")

    else:
        print("""
╔══════════════════════════════════════════╗
║  第二大脑 · 数据管道调度器               ║
╠══════════════════════════════════════════╣
║  init [--force]   初始化/重建索引         ║
║  stats            统计概览                ║
║  freshness        检查数据新鲜度          ║
║  holdings         持仓股数据状态          ║
║  sync             增量同步                ║
║  quality          数据质量报告            ║
║  skill-deps [name] 技能数据依赖           ║
║  dataset-skills <id> 反向查技能依赖       ║
║  load <id>        加载数据集              ║
╚══════════════════════════════════════════╝
        """)
