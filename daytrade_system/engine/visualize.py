"""
可视化引擎 — 生成交互式HTML走势图
叠加: K线、VWAP+标准差带、布林带、支撑压力位、RSI副图、做T信号标记
"""

import json
from typing import Dict, List
from engine.indicators import KBar, calc_vwap_bands, calc_rsi, calc_bollinger, calc_ma, calc_cumulative_delta


def generate_chart_html(daily_bars: List[KBar], min5_bars: List[KBar],
                         stock_name: str, stock_code: str,
                         backtest_trades: List[Dict] = None,
                         support_resistance: Dict = None) -> str:
    """
    生成交互式ECharts HTML走势图
    """
    # 准备数据
    dates = []
    ohlc = []       # [open, close, low, high]
    volumes = []

    for bar in min5_bars:
        time_str = _format_time(bar.date, bar.time_sec)
        dates.append(time_str)
        ohlc.append([bar.open, bar.close, bar.low, bar.high])
        volumes.append(bar.volume)

    # 计算叠加指标
    closes = [b.close for b in min5_bars]
    vwap_bands = []  # 逐点VWAP
    for i in range(1, len(min5_bars) + 1):
        vb = calc_vwap_bands(min5_bars[:i])
        vwap_bands.append(vb)

    vwap_line = [v["vwap"] for v in vwap_bands]
    sigma1_up = [v["sigma1_upper"] for v in vwap_bands]
    sigma1_lo = [v["sigma1_lower"] for v in vwap_bands]
    sigma2_up = [v.get("sigma2_upper", 0) for v in vwap_bands]
    sigma2_lo = [v.get("sigma2_lower", 0) for v in vwap_bands]

    # RSI
    rsi_vals = calc_rsi(closes, 6)

    # CDV (累计成交量delta)
    cdv_vals = calc_cumulative_delta(min5_bars)

    # 支撑压力位（水平线）
    sr_lines = []
    if support_resistance:
        for level_name in ["s2", "s1", "pivot", "r1", "r2"]:
            val = support_resistance.get(level_name)
            if val and val > 0:
                sr_lines.append({"name": level_name.upper(), "value": val,
                                 "color": "#00ff00" if "s" in level_name else "#ff6b6b" if "r" in level_name else "#888"})

    # 交易信号标记
    trade_markers_buy = []
    trade_markers_sell = []
    if backtest_trades:
        for t in backtest_trades:
            if t.get("entry_time"):
                entry_ts = t["entry_time"]
                marker = {
                    "coord": [entry_ts, t.get("entry_px", 0)],
                    "value": f"{t['dir']} {t['profit']:+.1f}%",
                }
                if t["dir"] == "正T":
                    trade_markers_buy.append(marker)
                else:
                    trade_markers_sell.append(marker)

    # 构建JSON数据
    chart_data = {
        "stock": f"{stock_name}({stock_code})",
        "dates": dates,
        "ohlc": ohlc,
        "volumes": volumes,
        "vwap": vwap_line,
        "vwap_s1u": sigma1_up, "vwap_s1l": sigma1_lo,
        "vwap_s2u": sigma2_up, "vwap_s2l": sigma2_lo,
        "rsi": rsi_vals,
        "cdv": cdv_vals,
        "sr_lines": sr_lines,
        "buy_markers": trade_markers_buy,
        "sell_markers": trade_markers_sell,
    }

    chart_json = json.dumps(chart_data, ensure_ascii=False, default=str)

    # 构建支撑压力线ECharts series配置（预先构建避免f-string与JS语法冲突）
    sr_js_parts = []
    for sl in sr_lines:
        js = (
            '{ name:"' + sl['name'] + '", type:"line", xAxisIndex:0, yAxisIndex:0, '
            'markLine: { silent:true, symbol:"none", '
            'lineStyle:{color:"' + sl['color'] + '",width:1,type:"dashed"}, '
            'label:{show:true,position:"end",color:"' + sl['color'] + '",'
            'fontSize:11,formatter:"' + sl['name'] + ' " + ' + str(sl['value']) + '.toFixed(2)}, '
            'data:[{yAxis:' + str(sl['value']) + '}] } }'
        )
        sr_js_parts.append(js)
    sr_js_block = ",\n    ".join(sr_js_parts)
    if sr_js_block:
        sr_js_block = ",\n    " + sr_js_block

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{stock_name}({stock_code}) 做T走势图</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
  body {{ margin:0; padding:20px; background:#1a1a2e; font-family: 'Microsoft YaHei', sans-serif; }}
  #header {{ text-align:center; color:#e0e0e0; margin-bottom:16px; }}
  #header h2 {{ margin:0; font-size:20px; }}
  #header span {{ font-size:13px; color:#888; }}
  #chart {{ width:100%; height:700px; }}
  .legend {{ display:flex; justify-content:center; gap:20px; flex-wrap:wrap; margin-top:10px; }}
  .legend-item {{ display:flex; align-items:center; gap:6px; font-size:12px; color:#aaa; }}
  .legend-color {{ width:14px; height:3px; border-radius:2px; }}
</style>
</head>
<body>
<div id="header">
  <h2>{stock_name} ({stock_code}) — 做T走势图</h2>
  <span>VWAP + 标准差带 + RSI + 累计Delta | 支撑/压力位 | 交易信号</span>
</div>
<div id="chart"></div>
<div class="legend">
  <div class="legend-item"><div class="legend-color" style="background:#ffd700"></div>VWAP</div>
  <div class="legend-item"><div class="legend-color" style="background:rgba(255,215,0,0.15)"></div>VWAP ±1σ</div>
  <div class="legend-item"><div class="legend-color" style="background:rgba(255,215,0,0.05)"></div>VWAP ±2σ</div>
  <div class="legend-item"><div class="legend-color" style="background:#00ff00"></div>支撑位</div>
  <div class="legend-item"><div class="legend-color" style="background:#ff6b6b"></div>压力位</div>
</div>
<script>
const data = {chart_json};
const upColor = '#ef5350';
const downColor = '#26de81';
const option = {{
  backgroundColor: '#1a1a2e',
  tooltip: {{
    trigger: 'axis',
    axisPointer: {{ type: 'cross' }},
    backgroundColor: 'rgba(30,30,50,0.95)',
    borderColor: '#444',
    textStyle: {{ color: '#ddd', fontSize: 12 }}
  }},
  axisPointer: {{ link: [{{ xAxisIndex: 'all' }}] }},
  grid: [
    {{ left:'8%', right:'3%', top:60, height:'55%' }},
    {{ left:'8%', right:'3%', top:'78%', height:'10%' }},
    {{ left:'8%', right:'3%', top:'90%', height:'8%' }}
  ],
  xAxis: [
    {{ type:'category', data:data.dates, gridIndex:0, axisLabel:{{color:'#999',fontSize:10,interval:Math.floor(data.dates.length/15)}} }},
    {{ type:'category', data:data.dates, gridIndex:1, axisLabel:{{show:false}} }},
    {{ type:'category', data:data.dates, gridIndex:2, axisLabel:{{show:false}} }}
  ],
  yAxis: [
    {{ gridIndex:0, scale:true, axisLabel:{{color:'#aaa'}}, splitLine:{{lineStyle:{{color:'#2a2a3e'}}}} }},
    {{ gridIndex:1, axisLabel:{{color:'#aaa',fontSize:10}}, splitLine:{{show:false}}, min:0, max:100 }},
    {{ gridIndex:2, axisLabel:{{color:'#aaa',fontSize:10,formatter:v=>(v/1e6).toFixed(1)+'M'}}, splitLine:{{show:false}} }}
  ],
  series: [
    {{
      name:'K线', type:'candlestick', xAxisIndex:0, yAxisIndex:0,
      data: data.ohlc.map(d => [d[0], d[3], d[2], d[1]]),
      itemStyle: {{ color:upColor, color0:downColor, borderColor:upColor, borderColor0:downColor }}
    }},
    {{ name:'VWAP', type:'line', xAxisIndex:0, yAxisIndex:0, data:data.vwap, lineStyle:{{color:'#ffd700',width:1.5}}, symbol:'none', smooth:true }},
    {{ name:'VWAP+1σ', type:'line', xAxisIndex:0, yAxisIndex:0, data:data.vwap_s1u, lineStyle:{{color:'rgba(255,215,0,0.4)',width:1,type:'dashed'}}, symbol:'none' }},
    {{ name:'VWAP-1σ', type:'line', xAxisIndex:0, yAxisIndex:0, data:data.vwap_s1l, lineStyle:{{color:'rgba(255,215,0,0.4)',width:1,type:'dashed'}}, symbol:'none', areaStyle:{{color:{{x:0,y:0,x2:0,y2:1,colorStops:[{{offset:0,color:'rgba(255,215,0,0.08)'}},{{offset:1,color:'rgba(255,215,0,0.02)'}}]}}}} }},
    {{ name:'VWAP+2σ', type:'line', xAxisIndex:0, yAxisIndex:0, data:data.vwap_s2u, lineStyle:{{color:'rgba(255,215,0,0.2)',width:1,type:'dotted'}}, symbol:'none' }},
    {{ name:'VWAP-2σ', type:'line', xAxisIndex:0, yAxisIndex:0, data:data.vwap_s2l, lineStyle:{{color:'rgba(255,215,0,0.2)',width:1,type:'dotted'}}, symbol:'none' }}{sr_js_block},
    {{ name:'RSI(6)', type:'line', xAxisIndex:1, yAxisIndex:1, data:data.rsi, lineStyle:{{color:'#a29bfe',width:1.5}}, symbol:'none', smooth:true, markLine:{{ silent:true, symbol:'none', lineStyle:{{color:'#666',type:'dashed'}}, data:[{{yAxis:70,label:{{formatter:'70',color:'#fc5c65'}}}},{{yAxis:30,label:{{formatter:'30',color:'#26de81'}}}}] }}, areaStyle:{{color:{{x:0,y:0,x2:0,y2:1,colorStops:[{{offset:0,color:'rgba(162,155,254,0.15)'}},{{offset:1,color:'rgba(162,155,254,0.02)'}}]}} }} }},
    {{ name:'CumDelta', type:'line', xAxisIndex:2, yAxisIndex:2, data:data.cdv, lineStyle:{{color:'#00d2ff',width:1.2}}, symbol:'none', smooth:true, areaStyle:{{color:{{x:0,y:0,x2:0,y2:1,colorStops:[{{offset:0,color:'rgba(0,210,255,0.2)'}},{{offset:1,color:'rgba(0,210,255,0.02)'}}]}} }} }}
  ]
}};
const chart = echarts.init(document.getElementById('chart'));
chart.setOption(option);
window.addEventListener('resize', () => chart.resize());
</script>
</body>
</html>'''
    return html


def _format_time(date: str, sec: int) -> str:
    """格式化时间标签"""
    h = sec // 3600
    m = (sec % 3600) // 60
    # 只显示月日+时分
    if len(date) >= 8:
        md = date[4:6] + '/' + date[6:8]
    else:
        md = date
    return f"{md} {h:02d}:{m:02d}"


def generate_daily_chart(daily_bars: List[KBar], min5_bars: List[KBar],
                          stock_name: str, stock_code: str,
                          backtest_trades: List[Dict] = None,
                          support_resistance: Dict = None) -> str:
    """生成单日详细走势图（当日5分钟K线）"""
    # 只取当日数据
    if min5_bars:
        day_date = min5_bars[0].date
        day_bars = [b for b in min5_bars if b.date == day_date]
    else:
        day_bars = min5_bars

    return generate_chart_html(daily_bars, day_bars or min5_bars,
                               stock_name, stock_code,
                               backtest_trades, support_resistance)
