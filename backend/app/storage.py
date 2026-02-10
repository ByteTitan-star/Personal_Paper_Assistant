import json
import shutil
from pathlib import Path

from fastapi import UploadFile

from .schemas import PaperMeta, ResultKind

RESULT_FILE_MAP: dict[ResultKind, str] = {
    "translation": "translated_full.md",
    "summary": "summary_tinghua.md",
    "improvement": "improvements.md",
}


class Storage:
    def __init__(self, base_dir: Path, templates_dir: Path) -> None:
        self.base_dir = base_dir
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self.meta_file = self.base_dir / "papers.json"
        self.templates_dir = templates_dir
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        if not self.meta_file.exists():
            self.meta_file.write_text("[]", encoding="utf-8")

        default_template_path = self.templates_dir / "tinghua.md"
        if not default_template_path.exists():
            default_template_path.write_text(
                (
                    "# Core Ideas (Tinghua)\n\n"
                    "## 1. Problem Statement\n"
                    "- What problem does this paper solve?\n\n"
                    "## 2. Method\n"
                    "- Main idea and technical route.\n\n"
                    "## 3. Experiments\n"
                    "- Dataset / metrics / key results.\n\n"
                    "## 4. Strengths and Limits\n"
                    "- Strong points and known limitations.\n\n"
                    "## 5. Takeaways\n"
                    "- Reusable insights and practical notes.\n"
                ),
                encoding="utf-8",
            )

    def _load_papers(self) -> list[dict]:
        return json.loads(self.meta_file.read_text(encoding="utf-8"))

    def _save_papers(self, papers: list[dict]) -> None:
        self.meta_file.write_text(
            json.dumps(papers, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_papers(self) -> list[PaperMeta]:
        papers = [PaperMeta.model_validate(item) for item in self._load_papers()]
        return sorted(papers, key=lambda p: p.created_at, reverse=True)

    def get_paper(self, paper_id: str) -> PaperMeta | None:
        for paper in self.list_papers():
            if paper.paper_id == paper_id:
                return paper
        return None

    def upsert_paper(self, payload: PaperMeta) -> None:
        papers = self._load_papers()
        serialized = payload.model_dump()
        for idx, item in enumerate(papers):
            if item["paper_id"] == payload.paper_id:
                papers[idx] = serialized
                self._save_papers(papers)
                return
        papers.append(serialized)
        self._save_papers(papers)

    def update_paper_status(self, paper_id: str, status: str, domain_tags: list[str] | None = None) -> None:
        papers = self._load_papers()
        for item in papers:
            if item["paper_id"] == paper_id:
                item["status"] = status
                if domain_tags is not None:
                    item["domain_tags"] = domain_tags
        self._save_papers(papers)

    def save_upload(self, paper_id: str, upload: UploadFile) -> Path:
        destination = self.raw_dir / f"{paper_id}.pdf"
        with destination.open("wb") as output:
            shutil.copyfileobj(upload.file, output)
        return destination

    def pdf_path(self, paper_id: str) -> Path:
        return self.raw_dir / f"{paper_id}.pdf"

    def paper_output_dir(self, paper_id: str) -> Path:
        output_dir = self.processed_dir / paper_id
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def write_result(self, paper_id: str, kind: ResultKind, content: str) -> None:
        output_file = self.paper_output_dir(paper_id) / RESULT_FILE_MAP[kind]
        output_file.write_text(content, encoding="utf-8")

    def read_result(self, paper_id: str, kind: ResultKind) -> str:
        output_file = self.paper_output_dir(paper_id) / RESULT_FILE_MAP[kind]
        if not output_file.exists():
            return ""
        return output_file.read_text(encoding="utf-8")

    def save_chunks(self, paper_id: str, chunks: list[str]) -> None:
        path = self.paper_output_dir(paper_id) / "chunks.json"
        path.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_chunks(self, paper_id: str) -> list[str]:
        path = self.paper_output_dir(paper_id) / "chunks.json"
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def list_templates(self) -> list[str]:
        templates: list[str] = []
        for path in self.templates_dir.glob("*.md"):
            templates.append(path.name)
        return sorted(templates)

    def read_template(self, template_name: str) -> str:
        path = self.templates_dir / template_name
        if not path.exists():
            path = self.templates_dir / "tinghua.md"
        return path.read_text(encoding="utf-8")
