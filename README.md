# Job Application Copilot

An LLM-powered assistant that helps you tailor job applications. Give it your resume and a job description — it retrieves your most relevant experience and generates a cover letter, screening Q&A answers, and a match score.

## Features

- **Resume parsing** — ingests your PDF resume and chunks it by section
- **JD analysis** — extracts key requirements from any job description
- **RAG retrieval** — finds the most relevant parts of your resume per requirement
- **Cover letter generation** — tailored to the specific role and company
- **Screening Q&A** — grounded answers to common HR questions based on your real experience
- **Match score** — rates your profile fit and highlights skill gaps

## Tech Stack

- **LLM:** OpenAI GPT-4o (or Ollama for local/private use)
- **Embeddings:** `text-embedding-3-small`
- **Vector Store:** ChromaDB
- **PDF Parsing:** `pdfplumber`
- **UI:** Streamlit
- **Storage:** SQLite

## Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/hpan0101/job-application-copilot.git
cd job-application-copilot

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your OpenAI API key
$env:OPENAI_API_KEY = "sk-..."

# 5. Run the app
streamlit run src/app.py
```

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
│   └── project-plan.md  # Full project plan and week schedule
└── requirements.txt
```

## Documentation

See [`docs/project-plan.md`](docs/project-plan.md) for the full architecture, week-by-week plan, and design decisions.
