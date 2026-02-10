import asyncio
import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader

from .config import Settings
from .schemas import TaskState
from .storage import Storage


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        pages: list[str] = []
        for idx, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            pages.append(f"[Page {idx + 1}]\n{text}")
        combined = "\n\n".join(pages).strip()
        if combined:
            return combined
    except Exception:
        pass
    return "未提取到可读文本，上传的 PDF 可能是扫描件或受保护文件。"


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def infer_domain_tags(text: str) -> list[str]:
    low = text.lower()
    vocab = {
        "Backdoor Attacks": ["backdoor", "trigger", "clean-label", "trojan"],
        "Time Series": ["time series", "forecast", "temporal", "sequence"],
        "LLM": ["llm", "large language model", "transformer"],
        "Computer Vision": ["image", "vision", "cnn", "object detection"],
        "NLP": ["language", "text", "token", "bert", "translation"],
    }
    tags: list[str] = []
    for tag, keywords in vocab.items():
        if any(keyword in low for keyword in keywords):
            tags.append(tag)
    return tags or ["General"]


def make_translation_markdown(title: str, target_language: str, chunks: list[str]) -> str:
    lines = [
        f"# 全文翻译：{title}",
        "",
        f"目标语言：{target_language}",
        "",
        "说明：当前为可运行基线版本，保留公式与引用格式，输出草稿级翻译内容。",
        "",
    ]
    sample_chunks = chunks[:8] if chunks else ["未生成有效文本分块。"]
    for idx, chunk in enumerate(sample_chunks, start=1):
        lines.append(f"## 段落 {idx}")
        lines.append("")
        lines.append(f"原文片段：{chunk[:350]}")
        lines.append("")
        lines.append(
            f"翻译（{target_language}）：[基线演示] {chunk[:250]}"
        )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def make_summary_markdown(title: str, template: str, chunks: list[str]) -> str:
    key_points = chunks[:5] if chunks else ["无可用文本，暂无法生成有效总结。"]
    lines = [template.strip(), "", "---", "", f"## 针对《{title}》的自动总结", ""]
    for idx, point in enumerate(key_points, start=1):
        lines.append(f"- 关键点 {idx}：{point[:220]}")
    lines.extend(
        [
            "",
            "## 方法概览",
            "- 构建了解析 -> 翻译 -> 总结 -> 改进建议 的流水线。",
            "- 输出统一沉淀到结构化 Markdown 文件中。",
            "",
            "## 实验与证据",
            "- 依据上传论文切块内容自动生成。",
            "",
            "## 局限性",
            "- OCR 与深度领域适配目前仍是占位实现，可继续接入真实模型增强。",
            "",
        ]
    )
    return "\n".join(lines)


def make_improvement_markdown(title: str, tags: list[str], chunks: list[str]) -> str:
    evidence = chunks[0][:260] if chunks else "暂无可引用证据片段。"
    lines = [
        f"# 《{title}》改进建议",
        "",
        f"关联领域：{', '.join(tags)}",
        "",
        "## 1. 数据与评估",
        "- 扩展数据集覆盖范围，并加入分布外测试。",
        "- 为关键模块补充消融实验。",
        "",
        "## 2. 模型设计",
        "- 与更强的近期基线做对比，并明确性能与算力权衡。",
        "- 固定随机种子和实验环境，强化可复现性。",
        "",
        "## 3. 潜在创新方向",
        "- 尝试融合检索增强推理与鲁棒训练信号。",
        "- 为失败模式设计可解释诊断机制。",
        "",
        "## 证据片段",
        evidence,
        "",
    ]
    return "\n".join(lines)


def sse_event(payload: dict, event: str = "progress") -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class TaskBroker:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskState] = {}
        self._subscribers: defaultdict[str, set[asyncio.Queue[dict]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def create(self, task_id: str, paper_id: str) -> None:
        state = TaskState(
            task_id=task_id,
            paper_id=paper_id,
            status="queued",
            progress=0,
            message="任务已排队，等待执行。",
            updated_at=utc_now_iso(),
        )
        async with self._lock:
            self._tasks[task_id] = state
        await self._notify(task_id, state.model_dump())

    async def update(self, task_id: str, status: str, progress: int, message: str) -> None:
        async with self._lock:
            if task_id not in self._tasks:
                return
            current = self._tasks[task_id]
            state = TaskState(
                task_id=current.task_id,
                paper_id=current.paper_id,
                status=status,  # type: ignore[arg-type]
                progress=progress,
                message=message,
                updated_at=utc_now_iso(),
            )
            self._tasks[task_id] = state
        await self._notify(task_id, state.model_dump())

    async def get(self, task_id: str) -> TaskState | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def _notify(self, task_id: str, payload: dict) -> None:
        for queue in list(self._subscribers[task_id]):
            await queue.put(payload)

    async def subscribe(self, task_id: str):
        queue: asyncio.Queue[dict] = asyncio.Queue()
        self._subscribers[task_id].add(queue)

        current = await self.get(task_id)
        if current:
            await queue.put(current.model_dump())

        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    yield sse_event(payload)
                    if payload.get("status") in {"done", "failed"}:
                        break
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            self._subscribers[task_id].discard(queue)


async def run_pipeline(
    task_id: str,
    paper_id: str,
    title: str,
    target_language: str,
    template_name: str,
    storage: Storage,
    broker: TaskBroker,
    settings: Settings,
) -> list[str]:
    await broker.update(task_id, "parsing", 15, "正在解析 PDF 文本。")
    text = await asyncio.to_thread(extract_text_from_pdf, storage.pdf_path(paper_id))
    chunks = await asyncio.to_thread(
        chunk_text,
        text,
        settings.max_chunk_chars,
        settings.chunk_overlap,
    )
    await asyncio.to_thread(storage.save_chunks, paper_id, chunks)
    await asyncio.sleep(0.2)

    await broker.update(task_id, "translating", 45, "正在生成全文翻译草稿。")
    translation_md = await asyncio.to_thread(
        make_translation_markdown,
        title,
        target_language,
        chunks,
    )
    await asyncio.to_thread(storage.write_result, paper_id, "translation", translation_md)
    await asyncio.sleep(0.2)

    await broker.update(task_id, "summarizing", 70, "正在提取核心思路。")
    template = await asyncio.to_thread(storage.read_template, template_name)
    summary_md = await asyncio.to_thread(make_summary_markdown, title, template, chunks)
    await asyncio.to_thread(storage.write_result, paper_id, "summary", summary_md)
    await asyncio.sleep(0.2)

    tags = infer_domain_tags(text)
    await broker.update(task_id, "critiquing", 90, "正在生成改进建议。")
    improvement_md = await asyncio.to_thread(
        make_improvement_markdown,
        title,
        tags,
        chunks,
    )
    await asyncio.to_thread(storage.write_result, paper_id, "improvement", improvement_md)
    await asyncio.sleep(0.2)

    await broker.update(task_id, "done", 100, "任务已完成。")
    return tags
