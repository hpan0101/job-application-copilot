"""
resume_parser.py — Resume + project details ingestion.

Two jobs:
1. parse_resume(path)   → reads a PDF and splits it into labelled sections.
                          Experience is further split per employer for precise retrieval.
2. parse_projects(list) → validates and normalises your project detail dicts.

Both return a list of "chunks" with a 'section', 'content', and 'source' key
so the embedder can treat them uniformly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract_text


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """One unit of content that will be embedded and stored."""
    section: str        # e.g. "experience", "projects", "education"
    content: str        # the actual text
    source: str         # "resume" or "projects"
    metadata: dict = field(default_factory=dict)  # any extra info


@dataclass
class ProjectDetail:
    """
    One project entry you provide manually.
    Fill this in for every project you want the AI to know about.
    """
    name: str                          # e.g. "E-commerce Recommender"
    stack: str                         # e.g. "Python, FastAPI, PostgreSQL, Docker"
    your_role: str                     # e.g. "Solo developer / Backend lead"
    what_you_built: str                # 1-2 sentences describing what it does
    impact: str                        # measurable outcome or what you learned
    duration: Optional[str] = None     # e.g. "3 months", "Jan–Apr 2024"
    url: Optional[str] = None          # GitHub link or live URL


# ---------------------------------------------------------------------------
# Section detection helpers
# ---------------------------------------------------------------------------

# Common headings found in resumes — extend as needed
_SECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("summary",        re.compile(r"^(summary|profile|objective|about me)", re.I)),
    ("experience",     re.compile(r"^(experience|work experience|employment|work history)", re.I)),
    ("education",      re.compile(r"^(education|academic|qualifications)", re.I)),
    ("skills",         re.compile(r"^(skills|technical skills|core competencies|technologies)", re.I)),
    ("projects",       re.compile(r"^(projects|personal projects|side projects|portfolio)", re.I)),
    ("certifications", re.compile(r"^(certifications|certificates|licen[sc]es)", re.I)),
    ("awards",         re.compile(r"^(awards|honors|achievements)", re.I)),
]

# Matches a 4-digit year
_YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')
# Matches a month abbreviation + year — identifies standalone date lines
# e.g. "Feb. 2022 – Present", "Oct. 2020 – Feb. 2022"
_DATE_LINE_RE = re.compile(
    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(19|20)\d{2}'
)
# Matches common bullet styles used in resumes
_BULLET_RE = re.compile(r'^[–\-•*]\s')


def _detect_section(line: str) -> Optional[str]:
    """Return a normalised section name if the line looks like a top-level heading."""
    stripped = line.strip()
    if not stripped or len(stripped) > 60:
        return None
    for name, pattern in _SECTION_PATTERNS:
        if pattern.match(stripped):
            return name
    return None


# ---------------------------------------------------------------------------
# Experience chunking by employer
# ---------------------------------------------------------------------------

def _split_experience_by_employer(exp_lines: list[str]) -> list[Chunk]:
    """
    Split a flat list of experience lines into one Chunk per employer.

    Handles both common PDF formats:
      Format A — company + date on ONE line:  "PayPal Inc. Feb. 2022 – Present"
      Format B — company then date on NEXT line: "PayPal Inc." / "Feb. 2022 – Present"
      (pdfminer produces Format B for this resume)

    Strategy for Format B:
      1. Locate every date line (Month. YYYY pattern).
      2. Scan backward from each date line through non-bullet, capitalized lines
         to find the TOPMOST one — that is the company name line, not the role title.
      3. Slice the flat list at those company-name positions.
    """
    non_empty = [l for l in exp_lines if l.strip()]

    # --- Locate date lines ---
    date_positions = [
        i for i, l in enumerate(non_empty)
        if _DATE_LINE_RE.search(l) and not _BULLET_RE.match(l)
    ]

    # For Format A (year already on company line), add those positions too
    format_a_positions = [
        i for i, l in enumerate(non_empty)
        if _YEAR_RE.search(l) and not _BULLET_RE.match(l)
        and re.match(r'^[A-Z]', l) and not _DATE_LINE_RE.search(l)
    ]

    employer_start_set: set[int] = set()

    # Format B: scan backward from each date line to find the company name.
    # Employer headers are always within 3 lines of their date (company → role → date).
    # Limiting to 3 lines back prevents grabbing wrapped bullet continuations
    # from the previous employer as false positives.
    MAX_HEADER_LINES = 3
    for di in date_positions:
        candidate = None
        for j in range(di - 1, max(di - MAX_HEADER_LINES - 1, -1), -1):
            line = non_empty[j]
            if _BULLET_RE.match(line):
                break  # hit a bullet — stop scanning
            if re.match(r'^[A-Z]', line) and not _DATE_LINE_RE.search(line):
                candidate = j  # keep going — we want the EARLIEST capital line
        if candidate is not None:
            employer_start_set.add(candidate)

    # Format A: add direct matches
    for i in format_a_positions:
        employer_start_set.add(i)

    employer_start_indices = sorted(employer_start_set)

    if not employer_start_indices:
        return [Chunk(
            section="experience",
            content="\n".join(non_empty),
            source="resume",
        )]

    # --- Slice into per-employer blocks ---
    starts = employer_start_indices + [len(non_empty)]
    chunks: list[Chunk] = []
    for k in range(len(employer_start_indices)):
        block = non_empty[starts[k]: starts[k + 1]]
        employer_label = block[0] if block else "Unknown"
        chunks.append(Chunk(
            section="experience",
            content="\n".join(block),
            source="resume",
            metadata={"employer": employer_label},
        ))
    return chunks


# ---------------------------------------------------------------------------
# Resume parser
# ---------------------------------------------------------------------------

def parse_resume(pdf_path: str | Path) -> list[Chunk]:
    """
    Extract text from a PDF and split into section chunks.

    Special handling for the experience section: instead of one large blob,
    each employer becomes its own chunk for precise RAG retrieval.

    Returns a flat list of Chunk objects.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Resume not found: {pdf_path}")

    # --- Extract raw text via pdfminer ---
    # pdfminer handles tight-kerned / character-positioned PDFs much better than
    # pdfplumber's default extractor — it correctly reconstructs word spacing.
    raw_text = pdfminer_extract_text(str(pdf_path))
    lines = [l.strip() for l in raw_text.splitlines()]

    if not lines:
        raise ValueError("Could not extract any text from the PDF. Is it a scanned image?")

    # --- Walk lines and bucket into top-level sections ---
    raw_sections: list[tuple[str, list[str]]] = []
    current_section = "header"
    current_lines: list[str] = []

    for line in lines:
        section = _detect_section(line)
        if section:
            if current_lines:
                raw_sections.append((current_section, current_lines))
            current_section = section
            current_lines = []
        else:
            if line.strip():
                current_lines.append(line.strip())

    if current_lines:
        raw_sections.append((current_section, current_lines))

    # --- Convert raw sections into Chunks ---
    chunks: list[Chunk] = []
    for section_name, section_lines in raw_sections:
        if section_name == "experience":
            # Split experience into per-employer chunks for better retrieval
            employer_chunks = _split_experience_by_employer(section_lines)
            chunks.extend(employer_chunks)
        else:
            content = "\n".join(section_lines).strip()
            if content:
                chunks.append(Chunk(
                    section=section_name,
                    content=content,
                    source="resume",
                ))

    sections_summary = [
        f"{c.section}({c.metadata.get('employer', '')[:20]})" if c.section == "experience"
        else c.section
        for c in chunks
    ]
    print(f"[parser] Extracted {len(chunks)} chunks: {sections_summary}")
    return chunks


# ---------------------------------------------------------------------------
# Project details parser
# ---------------------------------------------------------------------------

def parse_projects(projects: list[dict] | list[ProjectDetail]) -> list[Chunk]:
    """
    Convert a list of project dicts (or ProjectDetail objects) into Chunks.

    Each project becomes one chunk with a rich text representation so the
    embedder treats it exactly like a resume section.

    Example input dict:
        {
            "name": "Job Application Copilot",
            "stack": "Python, LangChain, ChromaDB, Streamlit",
            "your_role": "Solo developer",
            "what_you_built": "LLM-powered assistant that tailors job applications.",
            "impact": "Reduced application prep time from 2 hours to 10 minutes.",
            "duration": "2 weeks",
            "url": "https://github.com/..."
        }
    """
    chunks: list[Chunk] = []

    for item in projects:
        if isinstance(item, dict):
            try:
                proj = ProjectDetail(**item)
            except TypeError as e:
                raise ValueError(
                    f"Invalid project dict — missing required field. {e}\n"
                    "Required fields: name, stack, your_role, what_you_built, impact"
                ) from e
        else:
            proj = item

        # Build a rich text block the LLM can read naturally
        lines = [
            f"Project: {proj.name}",
            f"Tech Stack: {proj.stack}",
            f"My Role: {proj.your_role}",
            f"What I Built: {proj.what_you_built}",
            f"Impact / Outcome: {proj.impact}",
        ]
        if proj.duration:
            lines.append(f"Duration: {proj.duration}")
        if proj.url:
            lines.append(f"URL: {proj.url}")

        chunks.append(Chunk(
            section="projects",
            content="\n".join(lines),
            source="projects",
            metadata={"project_name": proj.name},
        ))

    print(f"[parser] Parsed {len(chunks)} project entries: "
          f"{[c.metadata.get('project_name') for c in chunks]}")
    return chunks


# ---------------------------------------------------------------------------
# JD parser
# ---------------------------------------------------------------------------

def parse_jd_text(jd_text: str) -> str:
    """
    Clean and normalise pasted job description text.
    Strips excessive whitespace and returns the cleaned string.
    """
    lines = [line.strip() for line in jd_text.splitlines()]
    # Remove completely blank runs (keep single blank lines as paragraph breaks)
    cleaned: list[str] = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False
    return "\n".join(cleaned).strip()


async def parse_jd_url(url: str) -> str:
    """
    Scrape a job description from a URL.
    Returns the cleaned visible text of the page.
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("Install httpx and beautifulsoup4: pip install httpx beautifulsoup4")

    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove nav, header, footer, scripts, styles
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    return parse_jd_text(text)


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # ---- Test 1: project parsing (no PDF needed) ----
    sample_projects = [
        {
            "name": "Job Application Copilot",
            "stack": "Python, OpenAI API, ChromaDB, Streamlit",
            "your_role": "Solo developer",
            "what_you_built": "An LLM-powered assistant that generates tailored cover letters, "
                              "self-introductions, and STAR behavioral answers from a resume + JD.",
            "impact": "Cut application prep time from ~2 hours to under 10 minutes.",
            "duration": "1 week",
            "url": "https://github.com/hpan0101/job-application-copilot",
        },
    ]

    project_chunks = parse_projects(sample_projects)
    print("\n=== Project chunks ===")
    for chunk in project_chunks:
        print(f"[{chunk.section}] {chunk.content[:120]}...")

    # ---- Test 2: PDF resume parsing ----
    # Try the desktop path first, then data/resume.pdf
    candidate_paths = [
        Path(r"C:\Users\Doris\Desktop\huijie_pan_resume_2026_7.pdf"),
        Path(__file__).parent.parent / "data" / "resume.pdf",
    ]
    pdf_path = next((p for p in candidate_paths if p.exists()), None)

    if pdf_path:
        print(f"\n=== Resume chunks from {pdf_path.name} ===")
        resume_chunks = parse_resume(pdf_path)
        for chunk in resume_chunks:
            employer = chunk.metadata.get("employer", "")
            label = f"{chunk.section} | {employer}" if employer else chunk.section
            print(f"\n--- {label} ---")
            print(chunk.content[:300] + ("..." if len(chunk.content) > 300 else ""))
    else:
        print("\n[parser] No PDF found. Place your resume at data/resume.pdf to test parsing.")

    print("\n[parser] Smoke test done.")
