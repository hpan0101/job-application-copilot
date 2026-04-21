# Job Application Copilot — Project Plan

## What It Does

You give it:
1. Your resume (PDF or text)
2. A job description (paste or URL)

It gives you:
- A tailored cover letter
- Bullet points highlighting your most relevant experience
- Answers to common screening questions ("Why do you want this role?", "Describe a time you...")
- A match score — how well your profile fits the JD

---

## Requirements

### Functional
- Ingest and parse resume (PDF → text)
- Ingest job description (raw text or scraped from a URL)
- Retrieve relevant resume chunks per JD requirement
- Generate tailored cover letter
- Answer HR/screening questions grounded in your actual experience
- (Optional) Store past applications and compare across them

### Non-functional
- Runs locally or via a simple web UI
- Fast enough for interactive use (~5-10s per generation)
- No resume data sent to third parties (optional: use Ollama for full local privacy)

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    Frontend                      │
│         Streamlit / Gradio / FastAPI UI          │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│                  App Layer                       │
│                                                  │
│  1. Resume Parser        2. JD Parser            │
│     (pdfplumber)            (BeautifulSoup       │
│                              or raw paste)       │
│                                                  │
│  3. RAG Retriever                                │
│     - Embed resume chunks (OpenAI / local)       │
│     - ChromaDB vector store                      │
│     - Query: retrieve top-k chunks per JD req    │
│                                                  │
│  4. Generation Chain                             │
│     - Cover letter prompt                        │
│     - Screening Q&A prompt                       │
│     - Match score prompt                         │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│               LLM Backend                       │
│     OpenAI GPT-4o  OR  Ollama (local)           │
└─────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│              Storage (optional)                  │
│   SQLite — save applications, JDs, outputs       │
└─────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| LLM | OpenAI GPT-4o (easy) or Ollama/llama3 (private) |
| Embeddings | `text-embedding-3-small` or `nomic-embed-text` (local) |
| Vector Store | ChromaDB (simple, file-based, no server needed) |
| PDF Parsing | `pdfplumber` |
| Web scraping | `httpx` + `BeautifulSoup4` |
| Orchestration | LangChain or raw API calls |
| UI | Streamlit |
| Storage | SQLite via `sqlite3` or `SQLModel` |

---

## Week Plan (1–2h/day)

### Day 1 — Resume Ingestion
- Parse PDF → plain text with `pdfplumber`
- Chunk by section (Education, Experience, Skills, Projects)
- Embed chunks and store in ChromaDB

### Day 2 — JD Ingestion + Retrieval
- Accept JD as pasted text or scraped URL
- Extract key requirements from JD using LLM
- For each requirement, retrieve top-2 resume chunks from vector store

### Day 3 — Cover Letter Generation
- Build a prompt: `[JD summary] + [retrieved resume chunks] → cover letter`
- Tune tone (formal / casual) via a simple parameter
- Test with 2–3 real job postings

### Day 4 — Screening Q&A
- Hardcode 10 common HR questions
- For each, retrieve relevant resume chunks and generate grounded answers
- Output as a structured list

### Day 5 — Match Score + Gap Analysis
- Prompt the LLM to score fit (0–100) with reasoning
- Highlight skills in the JD that are missing from your resume

### Day 6 — Streamlit UI
- File uploader for resume
- Text area for JD
- Tabs: Cover Letter / Q&A / Match Score

### Day 7 — Polish
- Save applications to SQLite
- Export output to `.txt` or `.md`
- Prompt tuning, edge case fixes

---

## Project Structure

```
job-application-copilot/
├── src/
│   ├── parser.py        # PDF + JD ingestion
│   ├── embedder.py      # Chunk + embed resume
│   ├── retriever.py     # Query ChromaDB
│   ├── generator.py     # Cover letter, Q&A, score
│   └── app.py           # Streamlit UI
├── data/
│   └── resume.pdf
├── outputs/             # Saved cover letters
├── chroma_db/           # Local vector store
├── docs/
│   └── project-plan.md
└── requirements.txt
```

---

## Getting Started

```bash
# 1. Clone and set up environment
git clone https://github.com/hpan0101/job-application-copilot.git
cd job-application-copilot
python -m venv .venv
.venv\Scripts\activate   # Windows

# 2. Install dependencies
pip install openai langchain chromadb pdfplumber \
            streamlit httpx beautifulsoup4 sqlmodel

# 3. Set your API key
$env:OPENAI_API_KEY = "sk-..."

# 4. Run the app
streamlit run src/app.py
```
