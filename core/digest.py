"""
digest.py - 知识消化引擎
零外部依赖。纯 Python stdlib 实现。

功能:
- 中文分词 (Bigram + 英文提取)
- 关键词标签提取 (词频排序)
- 自动分类 (关键词匹配, 7类)
- 摘要生成 (首句截取)
- 重要性评分 (启发式 1-5)
- 文本消化主流程 (分词→标签→分类→摘要→入库)
"""
import re
import uuid
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import Optional

from core.graph import KnowledgeGraph


# ---- 停用词表 ----
STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "他", "她", "它", "们", "那", "些", "什么", "怎么", "如何",
    "可以", "这个", "那个", "还是", "因为", "所以", "但是", "如果", "虽然",
    "已经", "比较", "非常", "应该", "可能", "需要", "不过", "然后", "之后",
    "真的", "觉得", "知道", "让", "把", "被", "从", "对", "与", "或",
    "太", "更", "最", "只", "每", "才", "又", "再", "吗", "呢", "吧", "啊",
    "嗯", "哦", "哈", "呀", "嘛", "啦", "哇", "the", "a", "an", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "shall", "should", "may", "might", "must", "can",
    "could", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below", "between",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either", "neither",
    "it", "its", "they", "them", "their", "he", "she", "we", "us", "our"
}


class TextDigester:
    """文本消化器 — 分词 / 标签提取 / 自动分类 / 摘要生成 / 重要性评分

    使用方式:
        digester = TextDigester(graph, data_dir)
        node = digester.digest("你的文本内容")
    """

    def __init__(self, graph: KnowledgeGraph, data_dir: Path):
        self.graph = graph
        self.data_dir = data_dir
        self.category_index = self._load_category_index()

    def _load_category_index(self) -> dict:
        """加载分类关键词配置"""
        try:
            import json
            path = self.data_dir / "category-index.json"
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"categories": {}, "default_category": "life"}

    # ========== 分词 (v2.1: jieba 主引擎 + bigram 回退) ==========
    _jieba_available = None

    @classmethod
    def _init_jieba(cls):
        """懒加载 jieba"""
        if cls._jieba_available is None:
            try:
                import jieba
                jieba.setLogLevel(20)  # 静默
                cls._jieba = jieba
                cls._jieba_available = True
            except ImportError:
                cls._jieba_available = False

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """v2.1: jieba 中文分词 + 英文提取, bigram 回退"""
        TextDigester._init_jieba()
        tokens = []

        # 提取英文单词
        for match in re.finditer(r'[a-zA-Z0-9]+', text):
            tokens.append(match.group().lower())

        if TextDigester._jieba_available:
            # jieba 精确模式中文分词
            chinese_text = "".join(
                c if '\u4e00' <= c <= '\u9fff' else ' '
                for c in text
            )
            cn_tokens = TextDigester._jieba.lcut(chinese_text)
            tokens.extend(t for t in cn_tokens if t.strip() and len(t.strip()) >= 1)
        else:
            # fallback: bigram
            chinese_chars = "".join(c for c in text if '\u4e00' <= c <= '\u9fff')
            for i in range(len(chinese_chars) - 1):
                tokens.append(chinese_chars[i:i + 2])
            tokens.extend(list(chinese_chars))

        return [t for t in tokens if t not in STOP_WORDS and len(t) >= 1]

    @staticmethod
    def tokenize_set(text: str) -> set[str]:
        """返回去重 token 集合 (用于图谱关联)"""
        return set(TextDigester.tokenize(text))

    # ========== 标签提取 ==========
    def extract_tags(self, text: str, max_tags: int = 8) -> list[str]:
        """基于词频提取关键词标签"""
        tokens = self.tokenize(text)
        freq = Counter(tokens)
        return [word for word, _ in freq.most_common(max_tags)]

    # ========== 自动分类 ==========
    def classify(self, text: str) -> str:
        """关键词匹配自动分类"""
        categories = self.category_index.get("categories", {})
        text_lower = text.lower()
        scores = {}

        for cat_id, cat_info in categories.items():
            score = 0
            for kw in cat_info.get("keywords", []):
                if kw.lower() in text_lower:
                    score += 1
            if score > 0:
                scores[cat_id] = score

        if scores:
            return max(scores, key=scores.get)
        return self.category_index.get("default_category", "life")

    def get_category_name(self, category_id: str) -> str:
        """获取分类的中文名"""
        cat = self.category_index.get("categories", {}).get(category_id, {})
        return cat.get("name", category_id)

    # ========== 摘要生成 ==========
    @staticmethod
    def generate_summary(text: str, max_len: int = 80) -> str:
        """规则摘要: 取首句或截取前 max_len 字"""
        for sep in ["。", "\n", "；"]:
            idx = text.find(sep)
            if 10 < idx < max_len:
                return text[:idx] + "。"
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + "..."

    # ========== 重要性评分 ==========
    @staticmethod
    def score_importance(text: str) -> int:
        """启发式重要性评分 1-5"""
        score = 1
        length = len(text)

        if length > 2000:
            score += 2
        elif length > 500:
            score += 1

        # 包含问号 → 可能是问题/决策
        if "?" in text or "？" in text:
            score += 1

        # 包含感叹号/强调词
        if "!" in text or "！" in text or "重要" in text or "关键" in text:
            score += 1

        return min(score, 5)

    # ========== 主流程 ==========
    def digest(self, text: str, title: str = "", source: str = "manual") -> dict:
        """消化一段文本，自动分词/分类/标签/摘要并存入知识图谱。

        返回完整的知识节点 dict。
        """
        node_id = str(uuid.uuid4())[:8]
        title = title or (text[:50].strip() + ("..." if len(text) > 50 else ""))

        node = {
            "id": node_id,
            "type": "knowledge",
            "title": title,
            "content": text,
            "summary": self.generate_summary(text),
            "source": source,
            "source_path": "",
            "tags": self.extract_tags(text),
            "category": self.classify(text),
            "importance": self.score_importance(text),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "access_count": 0,
            "feedback_score": 0.0,
            "metadata": {"word_count": len(text), "language": "zh"}
        }

        # 存入知识图谱
        self.graph.reload()
        self.graph.add_node(node)
        self.graph.auto_link(node)
        self.graph.commit()

        return node

    def digest_batch(self, items: list[dict]) -> list[dict]:
        """批量消化。items = [{"text":..., "title":..., "source":...}, ...]"""
        results = []
        for item in items:
            text = item.get("text", "").strip()
            if not text:
                continue
            node = self.digest(
                text,
                item.get("title", ""),
                item.get("source", "batch")
            )
            results.append(node)
        return results

    # ========== 分类索引管理 ==========
    def reload_category_index(self):
        """热重载分类配置"""
        self.category_index = self._load_category_index()

    def add_category_keywords(self, category_id: str, keywords: list[str]):
        """运行时追加分类关键词"""
        if category_id not in self.category_index["categories"]:
            self.category_index["categories"][category_id] = {"name": category_id, "keywords": []}
        existing = self.category_index["categories"][category_id].get("keywords", [])
        for kw in keywords:
            if kw not in existing:
                existing.append(kw)
        self.category_index["categories"][category_id]["keywords"] = existing


# ================================================================
#  FileDigester / URLDigester (v1 预定接口)
# ================================================================

class FileDigester:
    """文件消化器 — v1 阶段实现 markitdown/OCR 路由"""

    def __init__(self, text_digester: TextDigester):
        self.text_digester = text_digester
        self.DIRECT_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".log"}
        self.MARKITDOWN_EXTENSIONS = {".docx", ".pdf", ".pptx", ".xlsx"}
        self.OCR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
        self.VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

    def digest_file(self, file_path: str) -> Optional[dict]:
        """根据扩展名路由到对应转换方法"""
        p = Path(file_path)
        if not p.exists():
            return None

        ext = p.suffix.lower()
        if ext in self.DIRECT_EXTENSIONS:
            return self._digest_direct(p)
        elif ext in self.MARKITDOWN_EXTENSIONS:
            return self._digest_markitdown(p)
        elif ext in self.OCR_EXTENSIONS:
            return self._digest_ocr(p)
        elif ext in self.VIDEO_EXTENSIONS:
            return self._digest_video(p)
        return None

    def _digest_direct(self, p: Path) -> dict:
        text = self._read_text_file(p)
        return self.text_digester.digest(text, title=p.stem, source=f"file:{p.name}")

    def _digest_markitdown(self, p: Path) -> dict:
        text = self._read_sidecar_text(p)
        if not text:
            text = self._metadata_text(p, "document")
            text += "\n\n内容提取状态: 未安装 markitdown/pandoc，已先摄入文件元数据。"
        return self.text_digester.digest(text, title=p.stem, source=f"document:{p.name}")

    def _digest_ocr(self, p: Path) -> dict:
        parts = [self._metadata_text(p, "image")]

        sidecar = self._read_sidecar_text(p)
        if sidecar:
            parts.append("人工/外部OCR文本:\n" + sidecar)

        tesseract = shutil.which("tesseract")
        if tesseract:
            ocr = self._run_command([tesseract, str(p), "stdout", "-l", "chi_sim+eng"], timeout=60)
            if ocr.strip():
                parts.append("OCR识别文本:\n" + ocr.strip())
        else:
            parts.append("OCR状态: 未检测到 tesseract；已摄入图片元数据。可放置同名 .txt sidecar 或安装 OCR 后重新摄入。")

        return self.text_digester.digest("\n\n".join(parts), title=p.stem, source=f"image:{p.name}")

    def _digest_video(self, p: Path) -> dict:
        parts = [self._metadata_text(p, "video")]

        sidecar = self._read_sidecar_text(p)
        if sidecar:
            parts.append("字幕/转写文本:\n" + sidecar)

        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            meta = self._run_command([
                ffprobe, "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", str(p)
            ], timeout=30)
            if meta.strip():
                parts.append("ffprobe媒体信息:\n" + meta.strip()[:4000])
        else:
            parts.append("视频分析状态: 未检测到 ffprobe/ffmpeg；已摄入视频元数据。可放置同名 .txt/.srt sidecar 或安装 ffmpeg 后重新摄入。")

        return self.text_digester.digest("\n\n".join(parts), title=p.stem, source=f"video:{p.name}")

    def _read_text_file(self, p: Path) -> str:
        for enc in ("utf-8", "utf-8-sig", "gb18030"):
            try:
                return p.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        return p.read_text(encoding="utf-8", errors="replace")

    def _read_sidecar_text(self, p: Path) -> str:
        candidates = [
            p.with_suffix(p.suffix + ".txt"),
            p.with_suffix(".txt"),
            p.with_suffix(".md"),
            p.with_suffix(".srt"),
            p.with_suffix(".vtt"),
        ]
        texts = []
        for c in candidates:
            if c.exists() and c.is_file():
                try:
                    texts.append(f"[{c.name}]\n{self._read_text_file(c)}")
                except OSError:
                    pass
        return "\n\n".join(texts)

    def _metadata_text(self, p: Path, media_type: str) -> str:
        stat = p.stat()
        payload = {
            "media_type": media_type,
            "file_name": p.name,
            "path": str(p),
            "extension": p.suffix.lower(),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
        return "多模态文件元数据:\n" + json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _run_command(args: list[str], timeout: int) -> str:
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            return result.stdout if result.stdout else result.stderr
        except Exception as e:
            return f"外部工具执行失败: {e}"


class URLDigester:
    """URL 消化器 — v1 阶段实现网页抓取"""

    def __init__(self, text_digester: TextDigester):
        self.text_digester = text_digester

    def digest_url(self, url: str) -> dict:
        from urllib.request import Request, urlopen
        req = Request(url, headers={"User-Agent": "SecondBrain/0.1"})
        with urlopen(req, timeout=20) as resp:
            raw = resp.read(1024 * 1024)
            charset = resp.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return self.text_digester.digest(text, title=url[:80], source=f"url:{url}")
