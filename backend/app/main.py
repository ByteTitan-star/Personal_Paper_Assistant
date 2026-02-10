import asyncio
import datetime as dt
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from .config import get_settings
from .pipeline import TaskBroker, run_pipeline
from .schemas import (
    ChatRequest,
    ChatResponse,
    ContentResponse,
    PaperMeta,
    SystemInfoResponse,
    TemplateInfo,
    UploadResponse,
)
from .storage import Storage

settings = get_settings()
backend_root = Path(__file__).resolve().parents[1]
storage = Storage(
    base_dir=backend_root / settings.data_dir,
    templates_dir=backend_root / settings.templates_dir,
)
broker = TaskBroker()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def utc_now_year() -> int:
    return dt.datetime.now(dt.timezone.utc).year


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def retrieve_contexts(question: str, chunks: list[str], top_k: int) -> list[str]:
    if not chunks:
        return []
    q_tokens = tokenize(question)
    scored: list[tuple[float, str]] = []
    for chunk in chunks:
        c_tokens = tokenize(chunk)
        if not c_tokens:
            continue
        overlap = len(q_tokens.intersection(c_tokens))
        score = overlap / (len(q_tokens) + 1)
        scored.append((score, chunk))
    ranked = sorted(scored, key=lambda item: item[0], reverse=True)
    selected = [item[1] for item in ranked[:top_k] if item[0] > 0]
    if not selected:
        return chunks[:top_k]
    return selected


async def execute_pipeline(task_id: str, paper_id: str, title: str, target_language: str, template_name: str) -> None:
    try:
        tags = await run_pipeline(
            task_id=task_id,
            paper_id=paper_id,
            title=title,
            target_language=target_language,
            template_name=template_name,
            storage=storage,
            broker=broker,
            settings=settings,
        )
        storage.update_paper_status(paper_id, "completed", domain_tags=tags)
    except Exception as exc:
        storage.update_paper_status(paper_id, "failed")
        await broker.update(task_id, "failed", 100, f"任务失败：{exc}")


@app.get(f"{settings.api_prefix}/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get(f"{settings.api_prefix}/system/info", response_model=SystemInfoResponse)
async def get_system_info() -> SystemInfoResponse:
    return SystemInfoResponse(
        app_name=settings.app_name,
        model_provider=settings.model_provider,
        llm_model_name=settings.llm_model_name,
        embedding_model_name=settings.embedding_model_name,
        pipeline_mode=settings.pipeline_mode,
    )


@app.get(f"{settings.api_prefix}/templates", response_model=list[TemplateInfo])
async def list_templates() -> list[TemplateInfo]:
    return [TemplateInfo(name=name) for name in storage.list_templates()]


@app.post(f"{settings.api_prefix}/upload", response_model=UploadResponse)
async def upload_paper(
    file: UploadFile = File(...),
    target_language: str = Form(default="Chinese"),
    summary_template: str = Form(default="tinghua.md"),
) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持上传 PDF 文件。")

    paper_id = uuid.uuid4().hex[:12]
    task_id = uuid.uuid4().hex
    storage.save_upload(paper_id, file)
    await file.close()

    paper_meta = PaperMeta(
        paper_id=paper_id,
        title=Path(file.filename).stem,
        source_filename=file.filename,
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        target_language=target_language,
        status="processing",
        year=utc_now_year(),
        authors=[],
        domain_tags=[],
    )
    storage.upsert_paper(paper_meta)
    await broker.create(task_id, paper_id)
    asyncio.create_task(
        execute_pipeline(
            task_id=task_id,
            paper_id=paper_id,
            title=paper_meta.title,
            target_language=target_language,
            template_name=summary_template,
        )
    )
    return UploadResponse(task_id=task_id, paper_id=paper_id)


@app.get(f"{settings.api_prefix}/tasks/{{task_id}}")
async def get_task(task_id: str) -> dict:
    state = await broker.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="任务不存在。")
    return state.model_dump()


@app.get(f"{settings.api_prefix}/tasks/{{task_id}}/events")
async def task_events(task_id: str):
    state = await broker.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="任务不存在。")
    return StreamingResponse(
        broker.subscribe(task_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get(f"{settings.api_prefix}/papers", response_model=list[PaperMeta])
async def list_papers() -> list[PaperMeta]:
    return storage.list_papers()


@app.get(f"{settings.api_prefix}/papers/{{paper_id}}", response_model=PaperMeta)
async def get_paper(paper_id: str) -> PaperMeta:
    paper = storage.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在。")
    return paper


@app.get(f"{settings.api_prefix}/papers/{{paper_id}}/content/{{kind}}", response_model=ContentResponse)
async def get_content(paper_id: str, kind: str) -> ContentResponse:
    if kind not in {"translation", "summary", "improvement"}:
        raise HTTPException(status_code=400, detail="不支持的内容类型。")
    if not storage.get_paper(paper_id):
        raise HTTPException(status_code=404, detail="论文不存在。")
    content = storage.read_result(paper_id, kind)  # type: ignore[arg-type]
    return ContentResponse(paper_id=paper_id, kind=kind, content=content)  # type: ignore[arg-type]


@app.get(f"{settings.api_prefix}/papers/{{paper_id}}/pdf")
async def get_pdf(paper_id: str):
    pdf_path = storage.pdf_path(paper_id)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF 文件不存在。")
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{paper_id}.pdf")


@app.post(f"{settings.api_prefix}/papers/{{paper_id}}/chat", response_model=ChatResponse)
async def chat(paper_id: str, payload: ChatRequest) -> ChatResponse:
    if not storage.get_paper(paper_id):
        raise HTTPException(status_code=404, detail="论文不存在。")

    chunks = storage.load_chunks(paper_id)
    contexts = retrieve_contexts(payload.question, chunks, payload.top_k)
    if not contexts:
        contexts = [storage.read_result(paper_id, "summary")[:500] or "暂无可用上下文。"]

    answer_lines = [
        "以下回答基于当前论文上下文生成：",
        "",
        f"问题：{payload.question}",
        "",
        "关键依据：",
    ]
    for idx, context in enumerate(contexts, start=1):
        answer_lines.append(f"{idx}. {context[:220]}")
    answer_lines.extend(
        [
            "",
            "结论：当前为基线检索回答，接入真实大模型后可获得更强推理能力。",
        ]
    )
    return ChatResponse(answer="\n".join(answer_lines), contexts=contexts)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
