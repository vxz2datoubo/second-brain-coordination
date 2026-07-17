"""market_context.py — 市场环境分析 v1

核心功能:
- 多板块加权对比 → 个股特异度
- 板块共振检测 → 系统性vs独立性判断
- 市场宽度(涨跌比) → 恐慌指数近似

今天学到的教训:
  不对比板块就判断个股 = 瞎判断
  昆仑需要对比AIGC+AI+游戏+数字媒体+海外业务5个板块, 不是1个

联动: supply-test / delta-cvd / opening-range / money-flow-divergence
"""

import os, json

ROOT = os.path.dirname(os.path.abspath(__file__))

# ── 个股→板块映射 ──
STOCK_SECTORS = {
    "300418": {  # 昆仑万维
        "sectors": {
            "880645": 0.30,  # AIGC概念 (SkyReels核心)
            "880948": 0.25,  # 人工智能 (大模型)
            "880590": 0.15,  # 网络游戏 (游戏发行)
            "881376": 0.15,  # 数字媒体 (短剧内容)
            "880786": 0.15,  # 海外业务 (Opera+出海)
        },
        "name": "昆仑万维"
    },
    "300058": {  # 蓝色光标
        "sectors": {
            "880645": 0.25,  # AIGC
            "881368": 0.30,  # 传媒
            "881370": 0.25,  # 广告营销
            "880786": 0.20,  # 海外业务
        },
        "name": "蓝色光标"
    },
}

# ── 大盘指数 ──
MARKET_INDICES = {
    "000001": "上证指数",
    "399001": "深证成指",
}


def compute_context(code, stock_return, sector_returns):
    """
    计算市场环境上下文
    
    Args:
        code: 股票代码
        stock_return: 个股涨跌幅% (如 -1.59)
        sector_returns: {sector_code: return_pct} 各板块涨跌幅
    
    Returns:
        {
            "idiosyncratic": float,     # 个股特异度%
            "weighted_sector": float,   # 加权板块涨跌幅%
            "confluence": int,          # 同板块数(多少板块同向)
            "total_sectors": int,       # 总板块数
            "signal": str,              # "跟随板块"/"独立强势"/"独立弱势"
            "detail": str
        }
    """
    config = STOCK_SECTORS.get(code)
    if not config:
        return {"idiosyncratic": 0, "signal": "未配置板块", "detail": ""}

    sectors = config["sectors"]
    weighted = 0
    matched = 0

    for sec_code, weight in sectors.items():
        if sec_code in sector_returns:
            weighted += weight * sector_returns[sec_code]
            matched += 1

    if matched == 0:
        return {"idiosyncratic": 0, "signal": "无板块数据", "detail": ""}

    # 归一化权重
    if matched < len(sectors):
        norm_factor = sum(sectors[s] for s in sector_returns if s in sectors)
        if norm_factor > 0:
            weighted = weighted / norm_factor
    else:
        # 权重默认归一
        pass

    idiosyncratic = round(stock_return - weighted, 2)

    # 同向检测
    same_dir = 0
    for sec_code, _ in sectors.items():
        if sec_code in sector_returns:
            if (stock_return > 0 and sector_returns[sec_code] > 0) or \
               (stock_return < 0 and sector_returns[sec_code] < 0):
                same_dir += 1

    # 信号判断
    abs_idio = abs(idiosyncratic)
    if abs_idio < 0.5:
        signal = "跟随板块"
        confidence = "高"
    elif abs_idio < 1.5:
        if idiosyncratic > 0:
            signal = "略强于板块"
        else:
            signal = "略弱于板块"
        confidence = "中"
    else:
        if idiosyncratic > 0:
            signal = "独立强势"
        else:
            signal = "独立弱势"
        confidence = "高"

    # 板块共振
    total = len(sectors)
    confluence_pct = same_dir / total * 100

    detail = (
        f"加权板块:{weighted:+.2f}% → 特异度:{idiosyncratic:+.2f}% "
        f"| 共振:{same_dir}/{total}({confluence_pct:.0f}%) → {signal}"
    )

    return {
        "idiosyncratic": idiosyncratic,
        "weighted_sector": round(weighted, 2),
        "confluence": same_dir,
        "total_sectors": total,
        "confluence_pct": round(confluence_pct, 1),
        "signal": signal,
        "confidence": confidence,
        "detail": detail,
    }


def market_sentiment(sector_returns, adv=None, dec=None):
    """
    市场情绪/恐慌度评估
    
    Args:
        sector_returns: 所有板块涨跌幅
        adv: 上涨家数(可选)
        dec: 下跌家数(可选)
    """
    if not sector_returns:
        return {"sentiment": "未知", "fear_level": 0}

    # 1. 板块全面下跌检测
    up_count = sum(1 for r in sector_returns.values() if r > 0)
    down_count = sum(1 for r in sector_returns.values() if r < 0)
    total = up_count + down_count

    # 2. 涨跌家数比
    adv_dec_ratio = None
    if adv and dec and dec > 0:
        adv_dec_ratio = round(adv / dec, 2)

    # 3. 恐慌等级
    fear_level = 0
    conditions = []

    if total > 0 and down_count / total > 0.8:
        fear_level += 40
        conditions.append(f"{down_count}/{total}板块下跌")
    elif total > 0 and down_count / total > 0.6:
        fear_level += 20
        conditions.append(f"{down_count}/{total}板块下跌")

    if adv_dec_ratio and adv_dec_ratio < 0.5:
        fear_level += 30
        conditions.append(f"涨跌比仅{adv_dec_ratio}")
    elif adv_dec_ratio and adv_dec_ratio < 0.8:
        fear_level += 10

    if fear_level >= 60:
        sentiment = "恐慌"
    elif fear_level >= 30:
        sentiment = "谨慎"
    elif fear_level >= 10:
        sentiment = "偏弱"
    else:
        sentiment = "平稳"

    return {
        "sentiment": sentiment,
        "fear_level": fear_level,
        "up_sectors": up_count,
        "down_sectors": down_count,
        "adv_dec_ratio": adv_dec_ratio,
        "detail": " | ".join(conditions) if conditions else "市场平稳"
    }


def score_for_quad_lens(code, stock_return=0, sector_returns=None):
    """
    为quad_lens提供市场环境评分 (±5分)
    
    逻辑:
    - 独立强势 → +3~5分 (不管大盘如何个股在涨)
    - 独立弱势 → -3~5分 (大盘没事个股在跌)
    - 跟随板块 → 0分 (不是个股信号)
    """
    if sector_returns is None:
        sector_returns = {}

    ctx = compute_context(code, stock_return, sector_returns)

    score = 0
    signals = [ctx.get("detail", "")]

    signal = ctx.get("signal", "")
    conf = ctx.get("confidence", "")

    if signal == "独立强势":
        score = 5 if conf == "高" else 3
    elif signal == "独立弱势":
        score = -5 if conf == "高" else -3
    elif signal == "略强于板块":
        score = 2
    elif signal == "略弱于板块":
        score = -1
    else:  # 跟随板块
        # 板块共振率高 = 系统性运动, 不罚分
        if ctx.get("confluence_pct", 0) >= 80:
            score = 0
            signals.append(f"板块高度共振({ctx['confluence_pct']:.0f}%) → 非个股信号")

    return {
        "score": score,
        "detail": " | ".join(signals),
        "context": ctx,
    }


def summary(code, stock_return=0, sector_returns=None):
    if sector_returns is None:
        sector_returns = {}
    ctx = compute_context(code, stock_return, sector_returns)
    return ctx.get("detail", "")


if __name__ == "__main__":
    # 模拟今天昆仑的数据
    sector_data = {
        "880645": -0.97,  # AIGC
        "880948": -0.99,  # AI
        "880590": -1.41,  # 游戏
        "881376": -1.21,  # 数字媒体
        "880786": -1.17,  # 海外业务
        "399001": -1.24,  # 深证
        "000001": -0.26,  # 上证
    }

    ctx = compute_context("300418", -1.59, sector_data)
    print(f"昆仑: {ctx['detail']}")

    sentiment = market_sentiment(sector_data)
    print(f"市场情绪: {sentiment['sentiment']} (恐慌度{sentiment['fear_level']})")
    print(f"  {sentiment['detail']}")

    sc = score_for_quad_lens("300418", -1.59, sector_data)
    print(f"评分: {sc['score']:+d} | {sc['detail']}")
