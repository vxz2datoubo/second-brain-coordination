"""
Tushare 代理桥接 — 统一数据接口
通过 gyzcloud.top 代理访问 tushare 全量API
所有技能统一通过此模块获取历史数据
"""
import requests
import json
import time
import os
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_CREDENTIALS = ROOT / "config" / "local_credentials.json"
ENV_TUSHARE_TOKEN = "TUSHARE_TOKEN"
ENV_TUSHARE_PROXY_BASE_URL = "TUSHARE_PROXY_BASE_URL"
ENV_LOCAL_CREDENTIALS_PATH = "AIDANAO_LOCAL_CONFIG"


def _local_credential_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get(ENV_LOCAL_CREDENTIALS_PATH, "").strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(DEFAULT_LOCAL_CREDENTIALS)
    out: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        normalized = str(path).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(path)
    return out


def _read_local_credentials() -> dict:
    for path in _local_credential_candidates():
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
    return {}


def _resolve_tushare_token(explicit_token=None) -> str:
    if explicit_token is not None:
        return str(explicit_token).strip()
    env_token = os.environ.get(ENV_TUSHARE_TOKEN, "").strip()
    if env_token:
        return env_token
    local_credentials = _read_local_credentials()
    for key in ("tushare_token", "TUSHARE_TOKEN", "token"):
        value = local_credentials.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""

class TushareBridge:
    """Tushare代理接口封装"""
    
    BASE_URL = os.environ.get(ENV_TUSHARE_PROXY_BASE_URL, "https://ts.gyzcloud.top/api")
    
    def __init__(self, token=None):
        self.token = _resolve_tushare_token(token)
        self.base_url = os.environ.get(ENV_TUSHARE_PROXY_BASE_URL, self.BASE_URL).strip() or self.BASE_URL
        self._cache = {}
        self._last_call = 0

    def _require_token(self) -> str:
        if not self.token:
            raise RuntimeError(
                "Tushare token missing. Set TUSHARE_TOKEN or provide config/local_credentials.json."
            )
        return self.token
    
    def _call(self, api_name, params=None, fields=None):
        """统一API调用"""
        if params is None:
            params = {}
        if fields and isinstance(fields, list):
            fields = ",".join(fields)
        token = self._require_token()
        
        # Rate limit: 150/min → 400ms delay min
        elapsed = time.time() - self._last_call
        if elapsed < 0.4:
            time.sleep(0.4 - elapsed)
        
        resp = requests.post(
            self.base_url,
            json={
                "api_name": api_name,
                "token": token,
                "params": params,
                "fields": fields
            },
            timeout=15
        )
        self._last_call = time.time()
        try:
            result = resp.json()
        except Exception:
            raise RuntimeError(f"API {api_name} 返回非JSON (代理异常)")
        if not isinstance(result, dict) or result.get("code") != 0:
            msg = result.get("msg") if isinstance(result, dict) else "empty"
            raise RuntimeError(f"API {api_name} 失败: code={result.get('code') if isinstance(result,dict) else '?'} msg={msg}")
        return result.get("data", {}).get("items", [])
    
    # ── 行情数据 ──
    def daily(self, ts_code, start_date, end_date, fields=None):
        """日线OHLCV"""
        return self._call("daily", {
            "ts_code": ts_code, 
            "start_date": start_date,
            "end_date": end_date
        }, fields)
    
    def daily_basic(self, ts_code, start_date, end_date):
        """每日基本面指标(PE/PB/市值等)"""
        return self._call("daily_basic", {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date
        })
    
    # ── 资金流 ──
    def moneyflow(self, ts_code, start_date, end_date, fields=None):
        """个股四渠道资金流(小/中/大/特大)"""
        default = "trade_date,buy_sm_vol,sell_sm_vol,buy_md_vol,sell_md_vol,buy_lg_vol,sell_lg_vol,buy_elg_vol,sell_elg_vol,net_mf_vol,net_mf_amount"
        return self._call("moneyflow", {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date
        }, fields or default)
    
    def moneyflow_cnt_ths(self, trade_date=None, start_date=None, end_date=None):
        """同花顺概念板块资金流"""
        params = {}
        if trade_date: params["trade_date"] = trade_date
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        return self._call("moneyflow_cnt_ths", params)
    
    def moneyflow_ind_ths(self, trade_date=None, start_date=None, end_date=None):
        """同花顺行业资金流"""
        params = {}
        if trade_date: params["trade_date"] = trade_date
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        return self._call("moneyflow_ind_ths", params)
    
    # ── 筹码数据 ──
    def cyq_chips(self, ts_code, trade_date=None, start_date=None, end_date=None):
        """每日筹码分布"""
        params = {"ts_code": ts_code}
        if trade_date: params["trade_date"] = trade_date
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        return self._call("cyq_chips", params)
    
    def cyq_perf(self, ts_code, trade_date=None, start_date=None, end_date=None):
        """筹码胜率"""
        params = {"ts_code": ts_code}
        if trade_date: params["trade_date"] = trade_date
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        return self._call("cyq_perf", params)
    
    # ── 融资融券 ──
    def margin_detail(self, ts_code, start_date, end_date):
        """个股融资融券明细"""
        return self._call("margin_detail", {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date
        })
    
    # ── 股东 ──
    def stk_holdernumber(self, ts_code, start_date=None, end_date=None):
        """股东户数"""
        params = {"ts_code": ts_code}
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        return self._call("stk_holdernumber", params)
    
    # ── 龙虎榜 ──
    def top_list(self, trade_date, ts_code=None):
        """龙虎榜明细"""
        params = {"trade_date": trade_date}
        if ts_code: params["ts_code"] = ts_code
        return self._call("top_list", params)
    
    def top_inst(self, trade_date, ts_code=None):
        """龙虎榜机构席位"""
        params = {"trade_date": trade_date}
        if ts_code: params["ts_code"] = ts_code
        return self._call("top_inst", params)
    
    # ── 涨跌停 ──
    def limit_list(self, trade_date, limit_type=None):
        """涨跌停列表"""
        params = {"trade_date": trade_date}
        if limit_type: params["limit_type"] = limit_type
        return self._call("limit_list", params)
    
    def limit_cpt_list(self, trade_date=None, start_date=None, end_date=None):
        """涨停最强概念板块"""
        params = {}
        if trade_date: params["trade_date"] = trade_date
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        return self._call("limit_cpt_list", params)
    
    # ── 概念/行业 ──
    def concept(self):
        """概念分类"""
        return self._call("concept", fields="code,name")
    
    def concept_detail(self, concept_id=None, ts_code=None):
        """概念成分股"""
        params = {}
        if concept_id: params["id"] = concept_id
        if ts_code: params["ts_code"] = ts_code
        return self._call("concept_detail", params)
    
    def ths_index(self, type_code="N"):
        """同花顺指数列表 N=概念 I=行业"""
        return self._call("ths_index", {"type": type_code})
    
    def ths_daily(self, ts_code, start_date, end_date):
        """同花顺概念日线"""
        return self._call("ths_daily", {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date
        })
    
    def ths_member(self, ts_code):
        """同花顺概念成分股"""
        return self._call("ths_member", {"ts_code": ts_code})
    
    def ths_hot(self, market="行业板块", is_new="Y"):
        """同花顺热榜"""
        return self._call("ths_hot", {
            "market": market,
            "is_new": is_new
        })
    
    # ── 财务 ──
    def fina_indicator(self, ts_code, start_date=None, end_date=None, period=None):
        """财务指标"""
        params = {"ts_code": ts_code}
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        if period: params["period"] = period
        return self._call("fina_indicator", params)
    
    # ── 基础数据 ──
    def stock_basic(self, list_status="L"):
        """全A股基础信息"""
        return self._call("stock_basic", {"list_status": list_status})
    
    def share_float(self, ts_code=None, start_date=None, end_date=None):
        """限售解禁"""
        params = {}
        if ts_code: params["ts_code"] = ts_code
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        return self._call("share_float", params)


# 单例
ts = TushareBridge()
