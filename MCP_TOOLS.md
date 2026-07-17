# MCP工具速查 — 通达信&第二大脑
版本: 2026-07-04 | v1.0

> **用途**: AI工具快速查询MCP工具用法
> **维护**: 所有AI共享

---

## 一、通达信MCP (tdx_live_bridge.py)

### 1.1 启动命令

```bash
# 独立启动（MCP stdio模式）
C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe -u F:/aidanao/mcp/tdx_live_bridge.py
```

### 1.2 工具列表

| 工具名 | 参数 | 返回 | 说明 |
|--------|------|------|------|
| `tdx_realtime` | `{code}` | 实时行情 | 股票实时价格/成交量/涨跌 |
| `tdx_kline` | `{code, period, count}` | K线数据 | 日/周/月/5分钟K线 |
| `tdx_lookup` | `{query}` | 搜索结果 | 模糊搜索股票 |
| `tdx_news` | `{keyword, limit}` | 新闻列表 | 资讯/公告 |
| `tdx_notice` | `{code, limit}` | 公告列表 | 个股公告 |
| `tdx_screener` | `{query, limit}` | 选股结果 | 条件选股 |

### 1.3 工具详细用法

#### tdx_realtime — 实时行情

```json
// 输入
{"code": "300418"}

// 返回示例
{
  "code": "300418",
  "name": "昆仑万维",
  "price": 46.50,
  "change_pct": 2.15,
  "volume": 1234567,
  "amount": 56789012,
  "high": 47.20,
  "low": 45.80,
  "open": 45.50,
  "prev_close": 45.50,
  "bid1": 46.48,
  "ask1": 46.50,
  "timestamp": "2026-07-04 10:30:00"
}
```

#### tdx_kline — K线数据

```json
// 输入
{
  "code": "300418",
  "period": "5m",   // 5m/日/周/月
  "count": 100
}

// 返回示例
{
  "code": "300418",
  "period": "5m",
  "bars": [
    {
      "datetime": "2026-07-04 10:30:00",
      "open": 46.00,
      "high": 46.50,
      "low": 45.90,
      "close": 46.30,
      "volume": 12345,
      "amount": 567890
    }
  ]
}
```

#### tdx_lookup — 股票搜索

```json
// 输入
{"query": "昆仑"}

// 返回示例
{
  "results": [
    {"code": "300418", "name": "昆仑万维", "market": "创业板"},
    {"code": "600436", "name": "片仔癀", "market": "主板"}
  ]
}
```

#### tdx_news — 新闻资讯

```json
// 输入
{"keyword": "AI", "limit": 5}

// 返回示例
{
  "news": [
    {
      "title": "AI板块持续火热",
      "datetime": "2026-07-04 10:00:00",
      "source": "东方财富"
    }
  ]
}
```

#### tdx_notice — 个股公告

```json
// 输入
{"code": "300418", "limit": 3}

// 返回示例
{
  "notices": [
    {
      "title": "关于2026年半年报的公告",
      "datetime": "2026-07-01 18:00:00"
    }
  ]
}
```

#### tdx_screener — 条件选股

```json
// 输入
{"query": "AI概念", "limit": 10}

// 返回示例
{
  "stocks": [
    {"code": "300418", "name": "昆仑万维"},
    {"code": "300058", "name": "蓝色光标"}
  ]
}
```

---

## 二、第二大脑API (server.py)

### 2.1 启动命令

```bash
# 启动HTTP服务
python F:/aidanao/server.py

# 服务地址: http://localhost:8766
```

### 2.2 API列表

#### 知识检索

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/retrieve/search` | 搜索知识库 |
| POST | `/api/retrieve/ask` | 智能问答 |
| GET | `/api/retrieve/categories` | 获取分类列表 |
| GET | `/api/knowledge-graph` | 获取完整图谱 |

#### 知识添加

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/digest/text` | 添加文本知识 |
| POST | `/api/digest/file` | 添加文件知识 |
| POST | `/api/digest/batch-text` | 批量添加 |

#### 进化机制

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/evolve/evaluate` | 执行进化评估 |
| GET | `/api/evolve/report` | 获取进化报告 |
| GET | `/api/evolve/insights` | 获取洞察 |
| POST | `/api/evolve/apply-rules` | 应用优化规则 |

#### 系统状态

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/stats` | 系统统计 |
| GET | `/api/health/status` | 健康状态 |
| GET | `/api/evolve/trend` | 进化趋势 |

### 2.3 API详细用法

#### POST /api/retrieve/search — 搜索知识库

```bash
curl -X POST http://localhost:8766/api/retrieve/search \
  -H "Content-Type: application/json" \
  -d '{"query": "昆仑万维 交易", "top_k": 5}'
```

```json
// 请求
{
  "query": "昆仑万维 交易",
  "top_k": 5,
  "category": null  // 可选：过滤分类
}

// 响应
{
  "results": [
    {
      "id": "abc123",
      "title": "昆仑万维交易规则",
      "summary": "昆仑万维优先于蓝标...",
      "category": "rules",
      "score": 0.95
    }
  ],
  "total": 1
}
```

#### POST /api/digest/text — 添加知识

```bash
curl -X POST http://localhost:8766/api/digest/text \
  -H "Content-Type: application/json" \
  -d '{
    "title": "新教训：追高买入风险大",
    "content": "2026-07-02 昆仑高开后追买，当日反转被套...",
    "category": "decision-lessons",
    "tags": ["昆仑", "追高", "教训"]
  }'
```

```json
// 响应
{
  "success": true,
  "node_id": "def456"
}
```

#### POST /api/evolve/evaluate — 执行进化评估

```bash
curl -X POST http://localhost:8766/api/evolve/evaluate
```

```json
// 响应
{
  "id": "eval001",
  "date": "2026-07-04",
  "period": "daily",
  "score": 85.5,
  "stats": {
    "total_nodes": 120,
    "total_edges": 85,
    "total_feedback": 25,
    "good_rate": 0.88
  },
  "insights": [
    "知识库已积累120个节点，建议启用定期巩固",
    "好评率88%，系统表现优秀"
  ],
  "improvements_applied": [
    "自动降低F4因子权重5%"
  ]
}
```

#### GET /api/stats — 系统统计

```json
// 响应
{
  "knowledge_graph": {
    "total_nodes": 120,
    "total_edges": 85
  },
  "memory": {
    "total_interactions": 350,
    "total_feedback": 25
  },
  "search": {
    "indexed_docs": 120,
    "vocab_size": 2500
  }
}
```

---

## 三、Python SDK用法

### 3.1 通达信MCP客户端

```python
import json
import subprocess

def call_tdx_mcp(tool: str, params: dict) -> dict:
    """调用通达信MCP桥"""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": params
        }
    }
    
    proc = subprocess.Popen(
        [
            "C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe",
            "-u", "F:/aidanao/mcp/tdx_live_bridge.py"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, _ = proc.communicate(
        input=json.dumps(request).encode(),
        timeout=30
    )
    
    return json.loads(stdout)

# 使用示例
result = call_tdx_mcp("tdx_realtime", {"code": "300418"})
print(result["price"])
```

### 3.2 第二大脑客户端

```python
import urllib.request
import json

class SecondBrainClient:
    def __init__(self, base_url: str = "http://localhost:8766"):
        self.base_url = base_url.rstrip("/")
    
    def search(self, query: str, top_k: int = 5) -> list:
        """搜索知识库"""
        data = json.dumps({"query": query, "top_k": top_k}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/retrieve/search",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["results"]
    
    def add_knowledge(self, title: str, content: str, 
                      category: str = "general", tags: list = None) -> str:
        """添加知识"""
        data = json.dumps({
            "title": title,
            "content": content,
            "category": category,
            "tags": tags or []
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/digest/text",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["node_id"]
    
    def get_stats(self) -> dict:
        """获取系统统计"""
        with urllib.request.urlopen(f"{self.base_url}/api/stats", timeout=10) as resp:
            return json.loads(resp.read())

# 使用示例
brain = SecondBrainClient()
results = brain.search("昆仑万维 教训")
print(results)

brain.add_knowledge(
    title="新教训",
    content="...",
    category="decision-lessons",
    tags=["教训"]
)
```

### 3.3 决策前自检

```python
from core.decision_consult import DecisionConsult

dc = DecisionConsult()
result = dc.consult("想在开盘追高买入", context={"大盘": "下跌"})

if result.has_warnings:
    print(result.format_warnings())
```

---

## 四、MCP Hub (mcp/hub/mcp_hub.py)

统一管理多个MCP服务器：

```python
from mcp.hub.mcp_hub import MCPHub

hub = MCPHub()

# 注册MCP服务器
hub.register("tdx", tdx_mcp_config)
hub.register("brain", brain_mcp_config)

# 调用工具
result = hub.call("tdx", "tdx_realtime", {"code": "300418"})

# 搜索
results = hub.search("brain", "昆仑 交易")
```

---

## 五、错误处理

### 5.1 通达信MCP错误

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| -1 | 连接失败 | 检查通达信是否运行 |
| -2 | 超时 | 重试 |
| -3 | 股票代码不存在 | 检查代码 |
| -4 | 数据不存在 | 等待数据更新 |

### 5.2 第二大脑错误

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| 400 | 参数错误 | 检查请求格式 |
| 404 | 节点不存在 | 新增知识 |
| 500 | 服务器错误 | 查看日志 |
| 503 | 服务未启动 | 启动server.py |

---

## 六、最佳实践

1. **启动顺序**: 先启动server.py，再启动tdx_live_bridge.py
2. **错误重试**: MCP调用建议重试3次，每次间隔1秒
3. **缓存结果**: 实时行情缓存5秒，K线缓存1分钟
4. **并发限制**: 同一工具同时只能有1个请求
5. **超时设置**: 实时行情5秒，K线30秒，搜索10秒
