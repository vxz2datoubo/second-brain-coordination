"""
brain_sync.py — 全领域知识批量摄入

将 aidanao 所有知识领域分门别类喂入 8767 智慧大脑。
类别: knowledge | decision | workflow | trading | evolution | causal
"""

import json, urllib.request, sys, os

BRAIN = "http://localhost:8767"

def post(endpoint, data):
    url = f"{BRAIN}{endpoint}"
    req = urllib.request.Request(url, data=json.dumps(data, ensure_ascii=False).encode(),
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def ingest(category, key, content, tags):
    """写入神经记忆，按分类标签"""
    r = post("/api/deep/memory/write", {
        "key": f"{category}/{key}",
        "content": content,
        "tags": [category] + list(tags)
    })
    return r

def batch():
    total, ok = 0, 0
    
    # ============================================================
    # 类别1: knowledge — AI视频、MaiBot、系统设计
    # ============================================================
    knowledge_items = [
        ("film-wong-kar-wai", "王家卫都市文艺体系:51条提示词,10维度创作框架(材质质感/镜头术语/构图/演员调度/场景调度/叙事诡计/灯光色彩/剪辑手法/剧情张力/导演),8种运镜(推拉摇移跟甩升降),3层音效设计,6大场景色调,遮挡变装技法。用户偏好:真人实拍质感,非CG非游戏非插画,IMAX+PanavisionC变形宽荧幕,自然光照,真实皮肤纹理毛孔瑕疵,轻微手持动态模糊,浅景深,色彩通透不过度HDR。", ["film","prompt","wong-kar-wai"]),
        
        ("film-dark-tokusatsu", "暗黑特摄变身体系:18个QA加多模板,BLACKSUN美学风格,肉身撕裂至生长至战损完成的完整流程,反物理细节设计。", ["film","tokusatsu","henshin"]),
        
        ("film-atom-punk", "原子朋克丧尸体系:辐射游戏风格,荒诞反差美学,机器人加丧尸双体系设计。", ["film","atom-punk","zombie"]),
        
        ("film-aesthetics-engine", "美学偏好学习系统:通过LLMVision全维度分析用户发图,5大维度(人物特征/服装风格/场景氛围/构图细节/互动元素)自动统计偏好,挖掘用户自己都没意识到的隐藏模式。导演方案覆盖10个维度,核心洞察:真正机会在将方法论转化为可执行工作流资产。", ["film","aesthetics","AI"]),
        
        ("maibot-architecture", "MaiBot洛雪:拟人化LLM智能体,可持续对话学习。Maisaka推理引擎负责上下文理解+回复判定+生成+协调记忆工具人格。AMemorix长期情景记忆系统依赖Embedding做语义检索,与第二大脑语义记忆互补。MCP桥接(brainbridge.py)暴露4个工具:brainsearch+brainconsult+braindigest+brainread。消息管线通过适配器接入QQ/Telegram/Discord。插件系统通过Manifest注册Command/Tool/Hook/Event。", ["maibot","llm","agent","live2d"]),
        
        ("second-brain-architecture", "第二大脑(8787/8767):6层认知架构(感知/记忆/情感/决策/社交/元认知)。Bigram分词+纯JSON图谱+BF遍历+TFIDF标签加权检索。MaiBotPlanner是LLM functioncalling决策链,MCP工具增强而非替代。每3小时自动会话同步+每日8点进化评估。上下文策略:第二大脑存全部(171KB)+上下文仅注入记忆摘要(8KB)+渐进索引L1至L4。", ["system","knowledge-base","architecture"]),
    ]
    
    for key, content, tags in knowledge_items:
        r = ingest("knowledge", key, content, tags)
        total += 1
        if not r.get("error"): ok += 1
        print(f"  📚 knowledge/{key}: {'✅' if not r.get('error') else '❌ '+str(r.get('error',''))}")
    
    # ============================================================
    # 类别2: decision — 硬规则、闭环教训
    # ============================================================
    decision_items = [
        ("news-surge-rule", "新闻突袭处理硬规则:盘中涨幅超5%或振幅超8%自动查新闻。流程:搜索(公众号/新浪7x24/同花顺)→分级(里程碑/重要/一般)→查旧闻→调卖点(上移百分之50/30/10+标注原值)→底仓不动。反例:7月2日昆仑万维ARR8亿美元新闻,股价42飙46,未主动查新闻导致T仓40.63过早卖出。", ["hard-rule","news","trading","critical"]),
        
        ("next-day-trend-rule", "追涨次日判定硬规则:昨日涨超百分之8且放量超2倍→标记需验证日。次日竞价低开超百分之1.5→立即降T仓一半,三十分钟不回-1%则全清。三十分钟不翻红→全天禁用抄底,只卖不买。根因:天量买盘一天消耗完毕,次日无接力资金,非上升趋势回踩而是利好一次性定价加接力失败。反例:7月3日昆仑竞价-2.7%冲46.69后三十分钟崩盘全天-6%。", ["hard-rule","trend","trading","critical"]),
        
        ("sell-wait-rule", "卖出等待硬规则:卖出后最少等三十分钟再接回,让股价走完路径再判断。禁止一分钟内接回。反例:7月3日46.45卖→45.81接只隔一分钟,错过了后续十块钱的跌幅抄底机会,全天利润被这一个操作毁掉。", ["hard-rule","trade","critical"]),
        
        ("position-iron-law", "仓位铁律:底仓百分之97长线不动,T仓百分之3每日最多2到3笔操作。单笔上限5000元。单日亏损超百分之2熔断全天停止。连续亏损2笔降为1槽。T仓盈亏对总资产影响微乎其微,不值得为T仓焦虑。", ["hard-rule","position","risk","critical"]),
        
        ("batch-build-rule", "分批建仓规则:不要一笔梭哈,分3次在不同支撑位建仓。第一次在浅回调,第二次在中支撑,第三次在深支撑。每次三分之一仓位。", ["hard-rule","entry","trading"]),
        
        ("fake-break-rule", "假跌破判断规则:跌破关键价位后3分钟不收回→真跌破,立刻止损。3分钟内收回且放量→假跌破,不止损甚至可加仓。假跌破通常伴随放量快速抽回,真跌破是阴线下去横着不回头。", ["hard-rule","support","stop-loss"]),
        
        ("info-advantage-rule", "信息劣势认知规则:昨天利好涨超12%今日若不强=主力在借利好出货。大盘资金今天流入其他板块,追涨次日必须等验证。不能用上升趋势中的回踩来解释追涨次日的弱势。", ["hard-rule","info","trading"]),
        
        ("closed-loop-principle", "闭环学习原则:每次被纠正事实后,扫描所有受影响产物并修复。将被纠正的事实提炼为可迁移流程规则,写入MEMORY.md和知识图谱。不给同一个错误犯第二次的机会。", ["hard-rule","learning","process"]),
    ]
    
    for key, content, tags in decision_items:
        r = ingest("decision", key, content, tags)
        total += 1
        if not r.get("error"): ok += 1
        print(f"  ⚖️  decision/{key}: {'✅' if not r.get('error') else '❌ '+str(r.get('error',''))}")

    # ============================================================
    # 类别3: workflow — 沙箱、Agent协作、工具链
    # ============================================================
    workflow_items = [
        ("sandbox-policy", "三层沙箱策略:readonly只读用于代码审查和文件分析。workspace-write默认模式,CWD内可读写用于改文件和重构。danger-full-access必须显式声明用于整个文件系统操作。", ["sandbox","security","policy"]),
        
        ("codex-collab", "Codex协作模式:WorkBuddy迪迪作为协调中枢,调度QClaw纯算力引擎和Codex智能体。QClaw产出到qclaw-output,Codex产出到codex-runs,两者产出均自动摄入第二大脑(POST /api/digest/text)。Codex调用方式:codex_run()从WorkBuddy调或codex exec从CLI直接调。", ["agent","collaboration","workflow"]),
        
        ("super-jarvis", "SuperJarvis共享协议:跨Agent任务调度(inbox→tasks/pending→running→done/failed),多Agent产出归档到outputs/workbuddy+outputs/qclaw+outputs/codex,协议schema定义在protocols/task+memory+decision。", ["agent","orchestration","protocol"]),
        
        ("data-infra", "数据基础设施:三层次数据源。第一优先neodata通过HTTPAPI覆盖A港美股实时历史行情资金板块宏观。第二优先tdx-connector通过MCP协议提供通达信本地K线实时行情选股资讯。第三降级直接读通达信本地二进制.day .lc5 .lc1文件免API依赖。", ["data","infrastructure","trading"]),
    ]
    
    for key, content, tags in workflow_items:
        r = ingest("workflow", key, content, tags)
        total += 1
        if not r.get("error"): ok += 1
        print(f"  🔧 workflow/{key}: {'✅' if not r.get('error') else '❌ '+str(r.get('error',''))}")
    
    # ============================================================
    # 类别4: trading — 已喂入的交易知识（补充）
    # ============================================================
    # 前面已有4条,这里补价量方法论的详细版
    trading_items = [
        ("time-window-psychology", "日内时间窗口心理学:0930-0950开盘博弈期优先接回跨日仓位不做新交易。0950-1030黄金窗口确认方向后首笔倒T最有效。1030-1100上午延续期继续看机会尤其方向选择。1100-1130垃圾时间除非强信号否则等待。1300-1330下午重启观察新方向第二反转窗口。1330-1400下午黄金窗口容易出倒T机会。1400-1430尾盘决策判断是否还有机会。1430-1500强制收尾所有未接回全部强平。统计结论:0930-1030上午持续走低后,1015-1045是第一反转窗口。", ["time","window","psychology","trading"]),
        
        ("dual-stock-strategy", "双股策略:昆仑万维趋势跟随型(trend)主力二次建仓区30-42可大胆做T。蓝色光标逆势抄底型(counter)主力成本远在6-8元做T需谨慎。双股资金比60/40,每日合计最多3笔卖出。同涨时优先强股做倒T,分化时弱买强卖。7个月量价剖面对比:昆仑有骨架(40.5-41铁底2.5%量)蓝标是薄壳(各层0.3-1.2%无实质结构)。", ["dual-stock","kunlun","blue","strategy"]),
    ]
    
    for key, content, tags in trading_items:
        r = ingest("trading", key, content, tags)
        total += 1
        if not r.get("error"): ok += 1
        print(f"  📊 trading/{key}: {'✅' if not r.get('error') else '❌ '+str(r.get('error',''))}")
    
    # ============================================================
    # 类别5: evolution — 自动进化、因果推理、认知引擎
    # ============================================================
    evolution_items = [
        ("auto-evo-system", "自动进化三层体系:日级收盘后记录日志→分析教训→更新图谱→决策前自检。周级汇总周报→识别重复犯错→因子评估→规则迭代。月级胜率验证→参数更新→策略迭代→年度回顾。自动触发:日亏2%熔断,连亏3笔停,Regime=EXTREME全平,某因子胜率低于40%自动降权,胜率高于70%自动提权。", ["evolution","auto","system"]),
        
        ("causal-wisdom", "因果智慧大脑:从知识检索→匹配规则→执行升级为理解因果→博弈推演→预见→行动。四大核心引擎:因果链构建器追溯直接深层原因+多路径推演。博弈网络分析器多方力量动态网络识别主导力量破局点。反事实推演器多分支概率期望差异。跨领域类比库心理学↔物理学↔行为金融学↔博弈论映射。", ["causal","wisdom","reasoning"]),
        
        ("cognitive-engine", "认知决策引擎:深思模式+快思模式双通道思维信号。四因素置信度评估:知识覆盖0-40+交叉验证0-30+风险识别0-10+元认知0-20。A++可直接执行→A建议执行→B谨慎→C备选→D不建议。闭环学习:决策前查历史教训→决策中多方案→决策后记录自动学习。", ["cognitive","reasoning","confidence"]),
    ]
    
    for key, content, tags in evolution_items:
        r = ingest("evolution", key, content, tags)
        total += 1
        if not r.get("error"): ok += 1
        print(f"  🧬 evolution/{key}: {'✅' if not r.get('error') else '❌ '+str(r.get('error',''))}")
    
    print(f"\n{'='*50}")
    print(f"总计: {ok}/{total} 条成功喂入 8767 智慧大脑")
    
    # 检查大脑状态
    stats = post("/api/deep/memory/stats", {})
    if isinstance(stats, dict) and "total_memories" in stats:
        print(f"当前记忆总量: {stats['total_memories']} 条")
    print(f"{'='*50}")

if __name__ == "__main__":
    batch()
