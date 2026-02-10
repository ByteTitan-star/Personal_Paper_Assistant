from typing import Literal

from pydantic import BaseModel, Field


ResultKind = Literal["translation", "summary", "improvement"]
TaskStatus = Literal["queued", "parsing", "translating", "summarizing", "critiquing", "done", "failed"]


class UploadResponse(BaseModel):
    task_id: str
    paper_id: str


class TemplateInfo(BaseModel):
    name: str


class PaperMeta(BaseModel):
    paper_id: str
    title: str
    source_filename: str
    created_at: str
    target_language: str
    status: str
    year: int | None = None
    authors: list[str] = Field(default_factory=list)
    domain_tags: list[str] = Field(default_factory=list)


class TaskState(BaseModel):
    task_id: str
    paper_id: str
    status: TaskStatus
    progress: int
    message: str
    updated_at: str


class ContentResponse(BaseModel):
    paper_id: str
    kind: ResultKind
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10)


class ChatResponse(BaseModel):
    answer: str
    contexts: list[str]


class SystemInfoResponse(BaseModel):
    app_name: str
    model_provider: str
    llm_model_name: str
    embedding_model_name: str
    pipeline_mode: str
