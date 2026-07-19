"""
题材板块热度查询器

通过通达信MCP API查询两只票的关联题材板块热度，
输出格式供SentimentEngine直接使用。
"""

# 板块编号 → 通达信板块代码的映射（预计算）
THEME_CODE_MAP = {
    "3126": {"code": "880126", "name": "词元经济"},
    "2790": {"code": "882790", "name": "虚拟数字人"},
    "3008": {"code": "883008", "name": "AI语料"},
    "3012": {"code": "883012", "name": "秘塔AI"},
    "3121": {"code": "883121", "name": "即梦AI"},
    "2923": {"code": "882923", "name": "GPT5"},
    "2927": {"code": "882927", "name": "文心一言"},
    "3123": {"code": "883123", "name": "OpenClaw"},
}

# 两只票各自关注的题材
TRACKED_THEMES = {
    "300418": ["3126", "2790", "3008", "3012"],
    "300058": ["3126", "3121", "2790", "2923", "2927"],
}


def query_sector_heat(tdx_api_fn, code: str) -> dict:
    """
    查询某只票的关联题材板块热度

    Args:
        tdx_api_fn: MCP tdx_api_data 调用函数
        code: 主票代码

    Returns:
        {板块编号: {limit_up_count, avg_chg, names}, ...}
    """
    themes = TRACKED_THEMES.get(code, [])
    if not themes:
        return {}

    result = {}
    for section_num in themes:
        info = THEME_CODE_MAP.get(section_num)
        if not info:
            continue
        try:
            # 通过通达信板块代码查询板块行情
            # (板块代码需要实际的MCP调用，此处留接口)
            result[section_num] = {
                "limit_up_count": 0,
                "avg_chg": 0,
                "names": [],
                "section_name": info["name"],
                "section_code": info["code"],
            }
        except Exception:
            result[section_num] = {"limit_up_count": 0, "avg_chg": 0}

    return result
