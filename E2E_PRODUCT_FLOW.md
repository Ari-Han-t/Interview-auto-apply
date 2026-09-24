# Interview AutoApply — End-to-End Product Flow

This file explains what the project does from signup to application tracking, so you can feed it into a design tool for UI generation.

## 1) Product Goal

Interview AutoApply helps a candidate:
- set up profile/resume once,
- discover suitable jobs,
- generate tailored application material,
- optionally auto-submit applications,
- and track complete lifecycle status.

## 2) User Journey (End-to-End)

### Stage A — Login
1. User registers/signs in on `/login`.
2. Backend validates credentials and sets JWT cookie.
3. User lands on dashboard.

### Stage B — Candidate Setup
1. User uploads master resume in `/profile` (`.tex/.pdf/.docx/.txt/.md`).
2. Backend stores resume version and updates profile text fields.
3. Background parser extracts structured resume details.
4. User fills profile/preferences/capabilities in `/settings`.

### Stage C — GitHub Sync
1. User enters GitHub username in `/profile`.
2. Backend fetches repos, upserts projects, infers skills/achievements.
3. Normalized project metadata becomes AI input for matching.

### Stage D — Job Discovery
1. User opens `/jobs` and starts discovery with filters.
2. Backend enqueues Celery job discovery task.
3. Workers scrape sources (LinkedIn, Internshala, YC, Greenhouse, Lever).
4. Jobs are normalized, deduped, analyzed, and optionally suitability-filtered.
5. UI shows eligible/ineligible jobs with reasons.

### Stage E — Analyze + Generate
1. User clicks **Analyze & Apply** on a job.
2. Backend initializes `Application` and progress map.
3. Concurrent pipeline runs:
   - parse job requirements,
   - resume/job match analysis,
   - tailored resume generation,
   - cover letter generation,
   - company research,
   - interview Q&A prep.
4. `/jobs/[id]` polls progress endpoint and renders live checklist.
5. Final output: generated resume (PDF), cover letter, and insights.

### Stage F — Optional Auto-Apply
1. User triggers auto-apply from `/applications`.
2. Backend sets status to `applying` and runs automation worker.
3. Outcomes:
   - success -> `applied`,
   - manual interruption (e.g., CAPTCHA) -> `intervention_required`,
   - failure -> error history + notification.

### Stage G — Tracking
1. User tracks timeline/history in `/applications`.
2. User can manually update statuses (`interview`, `offer`, `rejected`, etc.).
3. User manages generated content in `/cover-letters`.
4. Dashboard `/` shows funnel metrics.

## 3) Main Screens for UI Design

- `/login` — auth entry
- `/` — KPI dashboard + conversion summary
- `/jobs` — discovery controls + feed
- `/jobs/[id]` — tailoring room with live pipeline checklist
- `/applications` — status board + timeline + automation controls
- `/cover-letters` — letter library + edit/download
- `/profile` — resume manager + GitHub sync + achievements/courses
- `/settings` — profile graph + preferences + capabilities + security

## 4) Core Backend Pipelines

### Discovery Pipeline
1. Scrape jobs from selected source(s).
2. Normalize and dedupe by URL.
3. Extract requirements/tech stack from job text.
4. Evaluate candidate eligibility.
5. Persist jobs and suitability metadata.

### Generation Pipeline (Concurrent)
1. Extract job requirements.
2. Run match/gap analysis between candidate and role.
3. Generate tailored resume and export PDF.
4. Generate cover letter and export PDF/MD.
5. Generate company-research notes.
6. Generate interview preparation Q&A.

### Auto-Apply Pipeline
1. Move application into `applying`.
2. Run browser automation task.
3. Update to `applied` or `intervention_required`.
4. Write timeline history + notifications.

## 5) Application Status State Machine

Primary flow:
`generating -> generated -> applying -> applied`

Other terminal/branch states:
`interview`, `oa`, `offer`, `rejected`, `intervention_required`

## 6) API Surface Groups (Frontend Contract View)

- Auth: register/login/logout/change-password
- Profile: full profile graph CRUD
- Resume: upload/list/download/delete
- GitHub: sync/analyze
- Jobs: list/get/discover/analyze
- Applications: initialize/progress/generate/submit/resume/status/history
- Cover Letters: list/get/update/delete/download
- Analytics: overview metrics
- Notifications: list/read/delete

## 7) UX States to Model in Design

1. Loading/skeleton states for each major page.
2. Long-running async states (discovery, generation, submission).
3. Intervention-required flow (captcha/manual action).
4. Empty states (no jobs, no resumes, no applications, no letters).
5. Error states (auth expired, invalid file type, generation failure).

## 8) Suggested Linear Prototype Flow

1. Login/Register
2. Upload resume
3. Sync GitHub
4. Complete settings/preferences
5. Discover jobs
6. Analyze & generate application package
7. Review/download resume + cover letter
8. Trigger auto-apply
9. Handle success or intervention branch
10. Track lifecycle in applications timeline
