# 🚀 Cloud Deployment & CI/CD Guide

This repository is configured for automated CI/CD and multi-container Docker deployment on **Render**, **Railway**, and **GitHub Actions**.

---

## 🏗️ Architecture Overview

The system consists of two independently containerized services:
1. **Backend Service (`backend/`)**:
   - FastAPI REST API on Python 3.11 with Uvicorn.
   - Built-in TeXLive pdflatex compiler & ReportLab ATS fallback engine.
   - Dynamic port binding (`PORT`), health check route (`/health`), and dynamic CORS configuration.
2. **Frontend Service (`frontend/`)**:
   - Next.js 16 (App Router) on Node 20.
   - Multi-stage standalone Docker build (`output: "standalone"`).
   - Non-root runtime (`nextjs:nodejs`), consuming `NEXT_PUBLIC_API_URL`.

---

## 🔄 CI/CD Pipelines (GitHub Actions)

### 1. Continuous Integration (`.github/workflows/ci.yml`)
Triggers on every `push` and `pull_request` to `main`:
- **`test-backend`**: Sets up Python 3.11, installs TeXLive & requirements, executes modular resume compiler tests (`test_modular_resume.py`) and autofill tests (`test_resume_autofill.py`).
- **`build-frontend`**: Sets up Node 20, verifies TypeScript types, and compiles an optimized production build.
- **`docker-build`**: Builds and caches Docker images for both backend and frontend to verify build reproducibility.

### 2. Continuous Deployment (`.github/workflows/deploy.yml`)
Triggers on push to `main` (after tests pass) or manual dispatch:
- **`publish-images`**: Builds and pushes versioned images to **GitHub Container Registry (GHCR)**:
  - `ghcr.io/<owner>/interview-autoapply/backend:latest`
  - `ghcr.io/<owner>/interview-autoapply/frontend:latest`
- **`trigger-cloud-deploy`**: Invokes deploy webhooks (e.g. Render / Railway) when secrets are configured.

---

## ☁️ Option 1: Render All-in-One Blueprint (Recommended)

Render automatically provisions and connects both services using [`render.yaml`](file:///c:/Users/Arihant%20Gupta/Desktop/Interview_AutoApply/render.yaml).

### Steps to Deploy:
1. Push your repository to GitHub:
   ```bash
   git add .
   git commit -m "feat: setup full-stack Docker and CI/CD pipelines"
   git push origin main
   ```
2. Navigate to [Render Dashboard](https://dashboard.render.com/) and click **New +** -> **Blueprint**.
3. Select your `Interview-auto-apply` repository.
4. Render will parse `render.yaml` and create:
   - `interview-autoapply-backend` (Docker web service)
   - `interview-autoapply-frontend` (Docker web service)
5. Fill in the prompted secret environment variables:
   - `OPENROUTER_API_KEY` (or `GROQ_API_KEY` / `OPENAI_API_KEY`)
6. Click **Apply**. Both services will build and deploy automatically!

---

## ☁️ Option 2: Railway Deployment

Railway supports monorepo Docker builds natively using [`railway.json`](file:///c:/Users/Arihant%20Gupta/Desktop/Interview_AutoApply/railway.json).

### Steps to Deploy:
1. Open [Railway.app](https://railway.app/) and create a **New Project**.
2. Select **Deploy from GitHub repo** -> select `Interview-auto-apply`.
3. Add two services from the repository:
   - **Service 1 (Backend)**:
     - Root Directory: `backend`
     - Dockerfile: `Dockerfile`
     - Add environment variable `PORT=8000`
   - **Service 2 (Frontend)**:
     - Root Directory: `frontend`
     - Dockerfile: `Dockerfile`
     - Add environment variable `NEXT_PUBLIC_API_URL` set to the backend public URL.
4. Deploy!

---

## 🐳 Option 3: Local Full-Stack Docker Compose

To test the entire containerized stack locally:
```bash
docker-compose up --build
```
- Frontend UI: `http://localhost:3000`
- Backend API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

---

## 🔑 Environment Variables Reference

| Variable | Service | Description | Required? |
| :--- | :--- | :--- | :--- |
| `PORT` | Backend / Frontend | HTTP port for server process (provided by cloud host) | Auto |
| `DATABASE_URL` | Backend | PostgreSQL connection string or SQLite path | Optional (defaults to SQLite) |
| `REDIS_URL` | Backend | Redis URL for background workers / queue | Optional |
| `SECRET_KEY` | Backend | JWT secret key for session signatures | Recommended |
| `AUTH_DISABLED` | Backend | Set to `false` for production auth | Yes |
| `OPENROUTER_API_KEY` | Backend | Primary LLM API key | Yes (or GROQ/OPENAI) |
| `GROQ_API_KEY` | Backend | High-speed LLM fallback API key | Optional |
| `OPENAI_API_KEY` | Backend | OpenAI fallback API key | Optional |
| `NEXT_PUBLIC_API_URL` | Frontend | Public URL of the backend API service | Yes |
| `RENDER_DEPLOY_HOOK_BACKEND` | GitHub Secrets | Webhook URL to trigger Render backend deploy | Optional |
| `RENDER_DEPLOY_HOOK_FRONTEND` | GitHub Secrets | Webhook URL to trigger Render frontend deploy | Optional |
