# Job Application Copilot — Project Plan

## What It Does

You give it:
1. Your resume (PDF)
2. Your project details (structured form — name, stack, role, impact)
3. A job description (paste or URL)

It gives you:
- A **self-introduction** in three formats: 30-second verbal, 2-minute verbal, written
- A tailored **cover letter**
- **Behavioral Q&A** — STAR-format answers (Situation → Task → Action → Result) for 15 common behavioral questions grounded in your real experience
- **Screening Q&A** — grounded answers to 10 common HR questions
- A **match score** (0–100) with strengths, skill gaps, and suggestions

---

## Requirements

### Functional
- Ingest and parse resume PDF → per-employer sections (not one blob)
- Accept structured project details as input
- Ingest job description (raw text or scraped from a URL)
- Retrieve relevant resume + project chunks per JD requirement (RAG)
- Generate self-introduction in 30s / 2-min / written variants
- Generate tailored cover letter
- Answer behavioral questions in STAR format grounded in real experience
- Answer HR/screening questions grounded in actual experience
- Score profile fit (0–100) and highlight skill gaps
- (Optional) Store past applications and compare across them

### Non-functional
- Runs locally via Streamlit UI
- Fast enough for interactive use (~5–10s per generation)
- No resume data sent to third parties (optional: use Ollama for full local privacy)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Streamlit UI                        │
│  Sidebar: resume upload + project details form           │
│  Tab 1: Self-Intro  Tab 2: Cover Letter                  │
│  Tab 3: Behavioral Q&A  Tab 4: Match Score               │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                     App Layer                            │
│                                                          │
│  1. Resume Parser (resume_parser.py)                     │
│     pdfminer.six → text; split by employer               │
│     + structured project details form                    │
│                                                          │
│  2. JD Parser (resume_parser.py)                         │
│     BeautifulSoup4 scrape or raw paste                   │
│                                                          │
│  3. RAG Retriever (retriever.py)                         │
│     Embed chunks → ChromaDB 0.3.x (DuckDB+Parquet)       │
│     Query: top-k chunks per JD requirement               │
│                                                          │
│  4. Generation Chain (generator.py)                      │
│     Self-intro prompt (3 variants)                       │
│     Cover letter prompt                                  │
│     Behavioral Q&A prompt (STAR, 15 questions)           │
│     Screening Q&A prompt (10 HR questions)               │
│     Match score + gap analysis prompt                    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   LLM Backend                            │
│      OpenAI GPT-4o-mini / GPT-4o  OR  Ollama (local)    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│               Storage (optional, Day 7)                  │
│   SQLite via sqlmodel — applications, JDs, outputs       │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.9 | 3.8 is EOL; 3.10+ also works |
| LLM | OpenAI GPT-4o-mini (dev) / GPT-4.1 (prod) | or Ollama/llama3 for local privacy |
| Embeddings | `text-embedding-3-small` | $0.02/1M tokens — effectively free |
| Vector Store | ChromaDB 0.3.29 (DuckDB+Parquet) | No SQLite 3.35 requirement |
| PDF Parsing | `pdfminer.six` | Handles tight-kerned/LaTeX fonts correctly |
| Web Scraping | `httpx` + `BeautifulSoup4` | JD URL ingestion |
| Orchestration | Raw OpenAI API calls | No LangChain overhead |
| UI | Streamlit | Simple, fast to build |
| Storage | SQLite via `sqlmodel 0.0.8` | Pydantic 1.x compatible |

### Why pdfminer over pdfplumber?
pdfplumber's `extract_text()` merges words together for PDFs that use tight character-level positioning (common in LaTeX-generated resumes). `pdfminer.six` uses layout analysis that correctly reconstructs word spacing. pdfplumber is still installed (pdfminer is its dependency) but we call pdfminer directly.

### Why ChromaDB 0.3.29?
ChromaDB 0.4+ requires SQLite 3.35+. Python 3.9 on Windows ships with SQLite 3.34, which fails the version check. ChromaDB 0.3.x uses a DuckDB+Parquet backend with no SQLite dependency. We use a custom `OpenAIEmbedFn` wrapper since chromadb 0.3.x used the old `openai.Embedding` API.

---

## Week Plan

### Day 1 — Resume + Project Details ✅
- Parse PDF resume → text with `pdfminer.six`
- Split experience by employer (not one blob) for precise per-employer retrieval
- Build `ProjectDetail` dataclass for structured project input
- Embed all chunks into ChromaDB (DuckDB backend)
- **Files:** `resume_parser.py`, `embedder.py`, `requirements.txt`, `.env.example`

### Day 2 — JD Ingestion + Retrieval
- Accept JD as pasted text or scraped URL (`httpx` + `BeautifulSoup4`)
- Extract key requirements from JD using LLM
- Retrieve top-2 resume + project chunks per JD requirement
- **File:** `retriever.py`

### Day 3 — Self-Introduction + Cover Letter
- Self-intro prompt: 30-sec / 2-min / written variants + tone selector
- Ground intro in: background, top projects, target role fit
- Cover letter prompt: `[JD summary] + [retrieved chunks] → letter`
- **File:** `generator.py` (intro + cover letter)

### Day 4 — Behavioral Q&A (STAR Method)
- 15-question behavioral bank: leadership, conflict, failure, growth, collaboration
- STAR-format prompt: Situation → Task → Action → Result
- Ground every answer in real resume + project experience chunks
- Screening Q&A: 10 common HR questions with grounded answers
- **File:** `generator.py` (behavioral + screening)

### Day 5 — Match Score + Gap Analysis
- Score profile fit (0–100) with detailed reasoning
- Highlight JD skills missing from resume + projects
- Suggest which experiences to emphasize per role
- Output: JSON with score, strengths, gaps, suggestions
- **File:** `generator.py` (match score)

### Day 6 — Streamlit UI
- Sidebar: upload resume + project details form (name, stack, role, impact)
- Tab 1 — Self-Intro: format selector (30s / 2-min / written) + generate
- Tab 2 — Cover Letter: JD input + generate
- Tab 3 — Behavioral Q&A: question picker + STAR answer display
- Tab 4 — Match Score: fit score + skill gap list
- **File:** `app.py`

### Day 7 — Polish + Export
- Save applications to SQLite (JD, all outputs, date, match score)
- Export all outputs to `.md` or `.txt`
- Prompt tuning: test on 3+ real job postings
- Edge cases: missing resume sections, very long JDs, Ollama local fallback

---

## Project Structure

```
job-application-copilot/
├── src/
│   ├── resume_parser.py   # PDF ingestion (pdfminer) + project details + JD parsing
│   ├── embedder.py        # Chunk + embed into ChromaDB (DuckDB backend)
│   ├── retriever.py       # RAG: top-k chunks per JD requirement
│   ├── generator.py       # Self-intro, cover letter, STAR Q&A, match score
│   └── app.py             # Streamlit UI (4 tabs)
├── data/
│   └── resume.pdf         # Your resume (git-ignored)
├── outputs/               # Saved application outputs (git-ignored)
├── chroma_db/             # Local vector store (git-ignored)
├── docs/
│   └── project-plan.md    # This file
├── .env.example           # API key template
└── requirements.txt       # Pinned dependencies for Python 3.9
```

---

## Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/hpan0101/job-application-copilot.git
cd job-application-copilot

# 2. Create venv with Python 3.9 (py launcher required on Windows)
py -3.9 -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Open .env and set OPENAI_API_KEY=sk-...
# Change OPENAI_MODEL to gpt-4o-mini for dev (cheaper), gpt-4.1 for real use

# 5. Add your resume
# Place your PDF at data/resume.pdf

# 6. Run the app (available from Day 6 onward)
streamlit run src/app.py
```

---

## Cost Estimate

> Based on one full run: JD analysis + self-intro (3 variants) + cover letter + 5 behavioral Q&A + 10 screening Q&A + match score ≈ 25,000 input tokens + 7,000 output tokens, 21 LLM calls.

| Model | Cost / Application | 50 Apps / Month |
|---|---|---|
| GPT-4o ($2.50/$10 per 1M) | ~$0.13 | ~$6.50 |
| GPT-4.1 ($2.00/$8 per 1M) | ~$0.11 | ~$5.50 |
| GPT-4o-mini ($0.15/$0.60 per 1M) | ~$0.008 | ~$0.40 |
| Ollama (local) | $0 | $0 |

**Recommendation:** use `gpt-4o-mini` during development (entire build week under $1), switch to `gpt-4.1` for real applications.

Embeddings (`text-embedding-3-small` at $0.02/1M tokens) cost less than $0.01/month regardless of usage.
