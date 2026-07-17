# Aesthetics Brain v2 - 进阶版美学智慧大脑

## 功能特性

| 能力 | 状态 | 说明 |
|------|------|------|
| 图片理解 | ✅ | 语义向量分析 |
| 批量处理 | ✅ | 多图批量分析 |
| 偏好发现 | ✅ | 频率统计 + 隐藏模式 |
| 向量检索 | ✅ | 语义相似度匹配 |
| 可视化 | ✅ | 雷达图仪表盘 |

## 核心模块

```
wisdom-brain/
├── core/
│   ├── aesthetics_brain.py    # 核心大脑
│   ├── image_vectorizer.py   # 向量化引擎
│   ├── preference_engine.py   # 偏好分析
│   ├── similarity_search.py   # 相似召回
│   ├── batch_processor.py     # 批量处理
│   └── radar_chart.py         # 雷达图
├── server_aesthetics.py       # HTTP服务
└── demo_aesthetics.py         # 演示脚本
```

## 快速开始

```bash
# 运行演示
cd F:/aidanao/wisdom-brain
python demo_aesthetics.py

# 启动HTTP服务
python server_aesthetics.py --port 8768
```

## API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| /stats | GET | 系统统计 |
| /summary | GET | 偏好总结 |
| /radar | GET | 生成雷达图 |
| /patterns | GET | 隐藏模式 |
| /evolution | GET | 时序演变 |
| /analyze | POST | 分析单张图片 |
| /batch | POST | 批量分析 |
| /similar | POST | 查找相似 |

## 示例用法

```python
from core.aesthetics_brain import AestheticsBrain

brain = AestheticsBrain()

# 分析单张图片
analysis = {
    "person": {"face_shape": "oval", "eyes": "large", "hair": "long"},
    "clothing": {"style": "casual", "color": ["black", "white"]},
    "scene": {"location": "cafe", "mood": "warm"}
}
result = brain.analyze_image("photo.jpg", analysis)

# 查找相似
similar = brain.find_similar(["person.face_shape.oval", "person.hair.long"])

# 获取偏好雷达图
radar = brain.generate_radar_chart()
```

## 数据存储

- `knowledge/aesthetics/images/` - 图片记录
- `knowledge/aesthetics/vectors/` - 向量数据
- `knowledge/aesthetics/preferences/` - 偏好统计
- `knowledge/aesthetics/radar_chart.html` - 可视化雷达图

## 版本

- v2.0 (2026-07-06) - 进阶版完成