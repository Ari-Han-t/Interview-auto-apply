# Interview AutoApply System

Welcome to the Interview AutoApply system. This project is an automated AI-driven pipeline designed to streamline the software engineering job application process. It automatically tailors your master LaTeX resume to specific job descriptions, injects relevant real-world GitHub projects to match the required tech stack, and generates highly targeted cover letters.

## 🏗️ System Architecture

The system is composed of a **FastAPI (Python)** backend and a **Next.js (React)** frontend.

### 1. Database & State (Backend)
- **SQLAlchemy & SQLite:** We use a relational database to store Users, User Profiles (resumes, extracted JSON data, GitHub usernames), Jobs, and Applications.
- **Alembic:** Used for database migrations (e.g., adding `github_username` to the Profile).
- **Authentication:** JWT cookie-based authentication.

### 2. The Core AI Pipeline (Backend)
The true power of this system lies in its multi-step AI pipeline:

1. **Resume Ingestion (`app/api/resume.py`):** 
   - A user uploads their master `.tex` (LaTeX) resume template.
2. **GitHub Scraping (`app/services/scraper/github.py`):**
   - The system scrapes the user's public GitHub profile to extract a list of original repositories (ignoring forks), grabbing descriptions, homepage links, and tech stacks.
3. **AI Relevance Filtering (`app/services/ai/github_analyzer.py`):**
   - We pass the scraped repositories and a target Job Description to **OpenRouter (LLaMA 3)**.
   - The LLM acts as an expert tech recruiter, filtering out irrelevant repos and keeping only the "demoable" ones that directly align with the job's technical requirements. 
   - This structured JSON metadata is saved directly to the user's profile (`projects_json`).
4. **LaTeX Injection & Tailoring (`app/services/ai/generator.py`):**
   - When a user applies for a job, the LLM takes their master LaTeX resume and the target job description.
   - It is explicitly instructed to locate the `\section{Projects}` within the LaTeX document.
   - It perfectly injects the highly relevant GitHub projects (including descriptions and demo links) into the LaTeX structure without breaking compilation.
   - Finally, it saves the new tailored resume as `{user_prefix}_{company}_resume.tex`.

### 3. Frontend Automation (Next.js)
- **Tailoring Room:** Located at `frontend/src/app/jobs/[id]/page.tsx`, this is the command center where users input a GitHub username and fire off the pipeline. It orchestrates the API calls to first extract/analyze GitHub data and then generate the tailored LaTeX artifacts.

## 🚀 Getting Started

### Backend Setup
1. Navigate to the `backend/` directory.
2. Ensure you have a virtual environment active (e.g., `.venv\Scripts\activate`).
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy `backend/.env.example` to `backend/.env` and add at least one provider API key (OpenRouter, OpenAI, Groq, Gemini, Anthropic/Claude, or Azure OpenAI). See [LLM providers](#-llm-providers) below.
5. Run the database migrations (if not already done): `alembic upgrade head`.
6. Start the server: `uvicorn app.main:app --reload` (Runs on `http://localhost:8000`).

### Frontend Setup
1. Navigate to the `frontend/` directory.
2. Install dependencies: `npm install`.
3. Start the dev server: `npm run dev` (Runs on `http://localhost:3000`).

## 🤖 LLM Providers

The backend supports multiple LLM providers simultaneously. All AI services call `get_llm()` from `app/services/llm/`, which returns your primary provider or a fallback chain.

| Provider   | Env var(s)                              | Default model            |
|------------|-----------------------------------------|--------------------------|
| OpenRouter | `OPENROUTER_API_KEY`                    | `openai/gpt-oss-120b`    |
| OpenAI     | `OPENAI_API_KEY`                        | `gpt-4o-mini`            |
| Groq       | `GROQ_API_KEY`                          | `llama-3.3-70b-versatile`|
| Gemini     | `GEMINI_API_KEY` / `GOOGLE_API_KEY`     | `gemini-3.8-flash`       |
| Claude     | `ANTHROPIC_API_KEY` / `CLAUDE_API_KEY`  | `claude-sonnet-4-5`      |
| Azure      | `AZURE_OPENAI_API_KEY` + endpoint + deployment | (deployment name)  |

**Configuration (`backend/.env`):**

```bash
LLM_PROVIDER=openrouter                 # primary provider
LLM_FALLBACK_PROVIDERS=groq,openai,gemini  # tried in order on failure

OPENROUTER_API_KEY=sk-or-...
GROQ_API_KEY=gsk_...,gsk_...            # comma-separate keys to rotate on 429
```

- Set **multiple keys per provider** (comma-separated) — the client rotates on rate-limit (429) or auth errors.
- If the primary fails, the chain tries each configured fallback automatically.
- Configure as many providers as you like; only one key is strictly required.

## 🧩 Resume Tailoring Context

Every tailored resume and cover letter is built from three context layers:

1. **Master knowledge base** — experiences, skills, achievements, courses, and GitHub projects from your profile.
2. **Original resume** — the latest uploaded resume text (`raw_resume_text`) is always injected so facts stay grounded (never invented).
3. **Instructions** — free-form guidance with two scopes:
   - **Global** (Settings → Default Resume Instructions): applies to every generation.
   - **Per-job** (job tailoring room): overrides/complements global for that role only; sent as a labeled `[GLOBAL]` / `[THIS JOB — higher priority]` block when both exist.

GitHub projects are auto-refreshed before tailoring when the username is set and data is stale (>24h or no projects). The job page also accepts a GitHub username override and per-job instructions; instruction drafts are saved in the browser between visits.

## 🛠️ Testing the Pipeline
If you want to manually test the core scraping and AI components without the frontend, you can run the root Python scripts:
- `test_github.py`: Tests the GitHub extraction and AI relevance filtering.
- `test_ai.py`: Tests the LaTeX resume generation and project injection logic.

*Note: The frontend uses Next.js app router and connects to the backend via standard HTTP fetch requests with 'include' credentials for secure JWT cookie passing.*
