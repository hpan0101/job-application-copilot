# Job Application Copilot

An LLM-powered assistant that helps you tailor job applications. Give it your resume and a job description — it retrieves your most relevant experience and generates a self-introduction, cover letter, STAR behavioral answers, screening Q&A, and a match score.

## Features

- **Resume parsing** — ingests your PDF resume; splits experience by employer for precise retrieval
- **Project details** — structured input for your personal projects (name, stack, role, impact)
- **JD analysis** — extracts key requirements from pasted text or a scraped URL
- **RAG retrieval** — finds the most relevant resume + project chunks per JD requirement
- **Self-introduction** — 30-second, 2-minute, and written variants tailored to the role
- **Cover letter** — formal or casual tone, grounded in your actual experience
- **Behavioral Q&A** — STAR-format answers (Situation → Task → Action → Result) from a 15-question bank
- **Screening Q&A** — grounded answers to 10 common HR questions
- **Match score** — 0–100 fit score with strengths, skill gaps, and suggestions

## Tech Stack

- **Python:** 3.9 (required — 3.8 is EOL and incompatible with dependencies)
- **LLM:** OpenAI GPT-4o / GPT-4o-mini (or Ollama for fully local use)
- **Embeddings:** `text-embedding-3-small`
- **Vector Store:** ChromaDB 0.3.x (DuckDB+Parquet backend — no SQLite version requirement)
- **PDF Parsing:** `pdfminer.six` (handles tight-kerned fonts correctly)
- **Web Scraping:** `httpx` + `BeautifulSoup4`
- **UI:** Streamlit
- **Storage:** SQLite via `sqlmodel`

## Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/hpan0101/job-application-copilot.git
cd job-application-copilot

# 2. Create and activate virtual environment (Python 3.9 required)
py -3.9 -m venv .venv
.venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your API key
copy .env.example .env
# Then open .env and paste your OpenAI API key

# 5. Add your resume
# Place your PDF at data/resume.pdf

# 6. Run the app  (available from Day 6 onward)
streamlit run src/app.py
```

## Cost

Using GPT-4o-mini for all generations costs roughly **$0.008 per job application** (~$0.40/month for 50 apps). The entire build week of testing costs under **$1**. See [`docs/project-plan.md`](docs/project-plan.md) for a full cost breakdown by model.

## Project Structure

```
job-application-copilot/
├── src/
│   ├── resume_parser.py   # PDF ingestion (pdfminer) + project details input
│   ├── embedder.py        # Chunk + embed into ChromaDB (DuckDB backend)
│   ├── retriever.py       # RAG: query ChromaDB per JD requirement
│   ├── generator.py       # Self-intro, cover letter, STAR Q&A, match score
│   └── app.py             # Streamlit UI (4 tabs)
├── data/
│   └── resume.pdf         # Your resume (git-ignored)
├── outputs/               # Saved application outputs (git-ignored)
├── chroma_db/             # Local vector store (git-ignored)
├── docs/
│   └── project-plan.md    # Architecture, week plan, cost estimate
├── .env.example           # API key template — copy to .env
└── requirements.txt       # Pinned dependencies for Python 3.9
```

## Documentation

See [`docs/project-plan.md`](docs/project-plan.md) for the full architecture, week-by-week plan, design decisions, and cost breakdown.
