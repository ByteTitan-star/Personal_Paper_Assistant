# Personal Scholar Agent

Vue3 + Python implementation of a private paper reading assistant.

## Features

- PDF upload with task progress (SSE)
- 3-page frontend:
  - Upload page
  - Dashboard page
  - Reading workspace (PDF + translation/summary/improvement tabs + chat)
- Python backend pipeline:
  - Parse PDF
  - Generate translation draft
  - Generate structured summary (template-based)
  - Generate improvement suggestions
- Local paper metadata and artifacts:
  - `backend/data/raw`
  - `backend/data/processed/{paper_id}`

## Project Structure

```text
.
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ pipeline.py
│  │  ├─ schemas.py
│  │  └─ storage.py
│  ├─ data/
│  ├─ templates/
│  ├─ requirements.txt
│  └─ main.py
└─ frontend/
   ├─ src/
   │  ├─ api/
   │  ├─ router/
   │  ├─ stores/
   │  └─ views/
   ├─ package.json
   └─ vite.config.js
```

## Backend Run

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

Backend default URL: `http://127.0.0.1:8000`

## Frontend Run

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend default URL: `http://127.0.0.1:5173`

## API Summary

- `POST /api/upload` upload PDF
- `GET /api/tasks/{task_id}/events` SSE progress stream
- `GET /api/papers` list papers
- `GET /api/papers/{paper_id}` paper detail
- `GET /api/papers/{paper_id}/content/{kind}` result markdown (`translation|summary|improvement`)
- `GET /api/papers/{paper_id}/pdf` original PDF
- `POST /api/papers/{paper_id}/chat` retrieval QA

## Notes

- Current pipeline uses deterministic local logic, so it is runnable without external LLM keys.
- If you want real LLM generation, replace functions in `backend/app/pipeline.py`.
