# MASTER PROMPT: Build and Fix an End-to-End AI Internship Application Platform

## 1. Your Mission

You are a senior full-stack engineer, AI engineer, product designer, data engineer, and QA engineer working on an existing application.

Your task is to **inspect, debug, complete, and transform the existing codebase into a fully functional, end-to-end AI-powered internship discovery and application management platform.**

This product should help a student or early-career candidate manage the entire job-hunting lifecycle, from finding internships to creating personalized application materials, preparing for interviews, applying, and tracking outcomes.

The platform should combine:

1. Multi-platform internship and job discovery.
2. A centralized candidate profile and resume repository.
3. A structured portfolio of projects, technical skills, and achievements.
4. AI-powered job-resume matching and eligibility analysis.
5. Job-specific LaTeX resume generation.
6. Tailored cover letter generation.
7. Company and job research.
8. Personalized interview preparation.
9. Application tracking and follow-up management.
10. Analytics that improve the candidate's job-search strategy over time.

**Do not create a static prototype, throwaway demo, or frontend-only dashboard. Build a working application with real data persistence, functional backend endpoints, practical AI workflows, error handling, and a polished user experience.**

First inspect the complete existing repository, understand the current architecture and technology stack, identify broken functionality, and preserve working features. Extend and repair the existing application rather than unnecessarily rebuilding everything from scratch.

Make reasonable technical decisions independently. Do not stop at planning, listing suggestions, or creating placeholder components. Implement, test, and fix as much of the complete system as possible.

---

# 2. Product Vision

The application should act as a candidate's personal AI career operating system.

The core workflow is:

**Discover opportunities → Analyze eligibility → Match candidate → Customize resume → Generate cover letter → Research company → Prepare for interviews → Apply → Track progress → Learn from results.**

A candidate should be able to create their profile once, maintain a complete record of their skills and projects, and reuse that information to generate highly targeted application materials for different jobs.

For example, if a candidate has built a RAG application using Python, FastAPI, FAISS, and sentence-transformer embeddings, the system should identify which of those experiences are most relevant when applying for an AI engineering internship.

If another internship emphasizes backend development, APIs, databases, and cloud deployment, it should prioritize the candidate's relevant backend projects instead.

Every generated document must be personalized to the specific position without inventing experience, skills, qualifications, achievements, or metrics.

---

# 3. First Task: Audit and Repair the Existing Application

Before adding features, inspect:

- The complete project directory and existing documentation.
- Frontend framework, routing, UI architecture, and state management.
- Backend framework, API routes, and business logic.
- Database schema, migrations, and existing records.
- Authentication and authorization.
- AI provider and model integrations.
- Existing job discovery or web scraping functionality.
- Resume upload and document generation logic.
- Environment variables and configuration.
- Dependencies, build scripts, and deployment configuration.
- Existing automated tests, error logs, and runtime failures.

Identify the root causes of existing bugs and incomplete features.

Create an implementation checklist internally and work through it systematically. Fix broken existing functionality before expanding the application.

Important implementation rules:

- Retain the existing technology stack unless there is a compelling technical reason to change it.
- Do not replace working systems merely to make the architecture look cleaner.
- Do not hardcode sample jobs, fake company information, dummy match percentages, or fabricated application statuses into production screens.
- Use realistic demo data only in an explicitly labeled demo environment.
- Never expose API keys or secrets in frontend code.
- Avoid duplicating existing functionality.
- Keep dependencies maintainable and configuration documented.
- Ensure all major screens are connected to real application state and persisted data.

---

# 4. Module One: Multi-Platform Job Discovery

Build a unified job discovery engine that aggregates internships, graduate roles, research opportunities, and entry-level jobs from multiple sources.

## Target sources

Design integrations for sources including:

- Internshala.
- Y Combinator's Work at a Startup / YC Jobs.
- Glassdoor.
- LinkedIn, where authorized integration or permitted access is available.
- Wellfound.
- Greenhouse-powered company career pages.
- Lever-powered company career pages.
- Ashby-powered company career pages.
- Indeed, where authorized integration or permitted access is available.
- Official company career pages.
- University placement portals and other configurable sources.

Do not assume every website exposes a public API or permits unrestricted scraping. Build the ingestion system around the access methods actually available for each source.

Prioritize official APIs, permitted public job feeds, authorized integrations, and company career-page data. Where a source cannot be accessed reliably or permissibly, provide a source-specific adapter placeholder with clear configuration requirements, direct job links, manual URL import, and other legitimate fallback options.

Do not bypass authentication, CAPTCHAs, paywalls, access controls, or anti-bot protections. Do not describe an unsupported integration as operational.

## A. Source adapter architecture

Create a modular ingestion architecture where every source has a consistent interface.

Each adapter should support, as appropriate:

- Fetching available job listings.
- Pagination and incremental synchronization.
- Normalizing source-specific fields.
- Preserving the original job URL.
- Recording the source and fetch timestamp.
- Detecting closed or expired jobs when that information is reliably available.
- Handling rate limits, timeouts, and temporary failures.
- Logging ingestion results.
- Retrying transient failures with sensible limits.
- Respecting source-specific access rules and rate limits.

A failure from one platform must not stop other sources from working.

Maintain source health information, including:

- Integration status.
- Last successful synchronization.
- Latest error.
- Number of jobs imported.
- Number of duplicates detected.
- Number of expired jobs updated.

If a platform requires API credentials or another authorized access method, make configuration explicit through environment variables or a secure administrative settings screen.

## B. Job search interface

Build a professional search experience with filters for:

- Job title and keywords.
- Technologies and programming languages.
- Job category.
- Company.
- Location and country.
- Remote, hybrid, or onsite.
- Paid and unpaid internships.
- Minimum stipend or compensation, where available.
- Full-time, part-time, internship, or contract.
- Experience and graduation requirements.
- Application deadline.
- Posted date.
- Source platform.
- Visa or work authorization requirements, where relevant.
- Saved and previously applied jobs.
- Minimum resume-match score.

Support searches such as:

"Find backend engineering internships in India requiring Python, FastAPI, PostgreSQL, and cloud deployment, preferably remote or in Bangalore."

Also support a natural-language search interface that translates user requests into structured job filters.

## C. Job normalization and deduplication

Different websites may list the same opening. Normalize records into a canonical job schema containing:

- Job title.
- Company.
- Description.
- Responsibilities.
- Required qualifications.
- Preferred qualifications.
- Required technologies.
- Preferred technologies.
- Location.
- Work arrangement.
- Employment type.
- Compensation or stipend.
- Experience requirements.
- Graduation and eligibility requirements.
- Visa and work authorization requirements.
- Posting date.
- Application deadline.
- Original source.
- Original URL.
- Official application URL, when available.
- Last verified timestamp.
- Source-specific job identifier.
- Current status and status confidence.

Deduplicate using source IDs, URLs, canonicalized company and job titles, and similarity-based comparisons where appropriate.

Preserve the original source records and provenance. Never merge two distinct openings simply because their titles are similar.

Expired or unverifiable jobs should be labeled accordingly rather than silently presented as active opportunities.

## D. Job details page

Every job should open into a detailed, useful page displaying:

- Complete job description.
- Responsibilities.
- Technical requirements.
- Preferred qualifications.
- Eligibility and graduation restrictions.
- Work location and arrangement.
- Compensation information, if available.
- Application deadline, if available.
- Company information.
- Original job source and link.
- Last verified date.
- Candidate's match analysis.
- Skill gaps.
- Recommended resume version.
- Suggested next steps.

Clearly distinguish verified facts from AI-generated interpretations and unavailable information.

---

# 5. Module Two: Candidate Profile and Resume Repository

Create a centralized candidate profile that acts as the single source of truth for every generated application.

The candidate should not have to repeatedly enter the same information for every job.

## A. Personal and professional information

Support fields such as:

- Full name and preferred name.
- Email and contact details.
- Phone number, if provided.
- City and country.
- LinkedIn profile.
- GitHub profile.
- Portfolio website.
- Personal website.
- Education institution.
- Degree and specialization.
- Graduation year.
- Current semester or year.
- CGPA or GPA.
- Relevant coursework.
- Certifications.
- Work experience.
- Internships.
- Leadership experience.
- Hackathons and competitions.
- Achievements and awards.
- Open-source contributions.
- Technical and business skills.
- Professional interests.
- Job preferences.
- Work authorization, where relevant.
- Availability and preferred internship duration.

Make fields optional where appropriate and allow the candidate to control what information is included in an application.

## B. Upload and parse existing resumes

Support uploading existing resumes in LaTeX source format, particularly `.tex` files.

Also support `.zip` archives of LaTeX projects when useful, including associated template files, bibliography files, and custom style files. PDF and DOCX uploads may be supported as alternative import formats.

For LaTeX resumes:

1. Read the uploaded source.
2. Parse the document structure and sections.
3. Extract contact information, education, work experience, projects, skills, certifications, and achievements.
4. Preserve the original source file.
5. Identify custom commands and section macros.
6. Flag fields or macros that cannot be parsed reliably.
7. Show the extracted information in a review screen.
8. Allow the candidate to correct mistakes before saving it as verified profile data.

Do not overwrite the original resume when generating a job-specific variant.

If a PDF accompanies the LaTeX file, use it as an additional reference for the rendered layout and extracted text.

If a file cannot be parsed correctly, communicate that clearly and offer manual editing rather than silently producing inaccurate data.

## C. Multiple resume versions

Allow candidates to maintain distinct resume versions, for example:

- General software engineering.
- Backend engineering.
- AI and machine learning.
- Data engineering.
- Full-stack development.
- Product and business technology.

Each version should have:

- Its own LaTeX source.
- Selected projects.
- Selected experience.
- Target role category.
- Formatting preferences.
- Version history.
- Creation and modification dates.
- Optional notes.

The candidate should always be able to return to the original uploaded version.

---

# 6. Module Three: Structured Project Portfolio

This is a core differentiator. Build a dedicated project-management system for the candidate's technical work.

Candidates often have far more experience than can fit on a one-page resume. The platform must retain that full information and select the most relevant parts for each job.

## A. Project creation and editing

For every project, support:

- Project name.
- Short description.
- Problem being solved.
- Motivation and objective.
- Technical architecture.
- Programming languages.
- Frameworks and libraries.
- Databases.
- Cloud platforms and deployment tools.
- APIs and external integrations.
- AI models and ML techniques.
- Data processing methods.
- Algorithms and data structures.
- Testing and security techniques.
- Key features implemented.
- Individual contribution.
- Team size and collaboration details.
- Technical challenges.
- Engineering decisions and trade-offs.
- Results and measurable impact.
- GitHub repository URL.
- Live deployment URL.
- Documentation URL.
- Screenshots or supporting files.
- Start and completion dates.
- Project status.
- Privacy and confidentiality restrictions.

Support separate structured entries for projects, internships, work experience, open-source contributions, and coursework.

## B. Technology extraction

When a candidate provides a project description, repository URL, README, documentation, or supported repository files, identify potential technologies and propose structured metadata.

Only analyze repositories the candidate is authorized to access.

Never assume that a dependency appearing in a package file necessarily means the candidate implemented or mastered that technology.

Show extracted claims for review before treating them as verified profile information.

## C. Achievements and evidence

Where available, allow candidates to attach evidence such as:

- Test results.
- Benchmark results.
- Deployment metrics.
- Performance improvements.
- User counts.
- Commits or contributions.
- Hackathon awards.
- Screenshots.
- Public documentation.
- Published work.

Never fabricate numerical impact. If measurable results are unavailable, write strong, specific descriptions of the engineering work without invented metrics.

## D. Project evidence bank

For each project, maintain a collection of verified facts and resume-ready statements.

For example:

Project: AI-powered document search platform.

Technologies: Python, FastAPI, FAISS, sentence-transformers, PostgreSQL.

Verified experience:
- Implemented document ingestion and preprocessing.
- Created vector embeddings for semantic retrieval.
- Integrated similarity-based search.
- Developed REST endpoints for querying stored documents.
- Persisted document and application data.

Store these as factual claims with links to their supporting project details.

This allows the AI to select accurate, relevant statements without repeatedly inventing new descriptions.

---

# 7. Module Four: AI Job-Matching Engine

Develop a real job-to-candidate matching engine.

It should evaluate not only keyword overlap but also the actual relationship between a candidate's verified experience and the job requirements.

## A. Matching pipeline

For each job:

1. Parse the job description.
2. Extract required and preferred skills.
3. Identify the responsibilities and expected deliverables.
4. Extract explicit eligibility requirements.
5. Retrieve relevant candidate experiences and projects.
6. Compare requirements against verified candidate evidence.
7. Evaluate transferable skills.
8. Identify missing or uncertain information.
9. Generate an explainable match report.
10. Suggest application materials and preparation steps.

Use a combination of structured matching, semantic search, and an LLM for interpretation. Do not rely exclusively on an LLM to produce an unexplained arbitrary percentage.

## B. Match score

Create a configurable matching system with a transparent scoring model.

An initial example:

- Required technical skills: 30%.
- Relevant projects and hands-on experience: 25%.
- Responsibilities and role alignment: 15%.
- Preferred skills: 10%.
- Education and explicit eligibility: 10%.
- Relevant achievements or domain knowledge: 10%.

These are starting weights, not universal truths. Make them configurable and validate the calculation.

Show the underlying category scores and the supporting evidence.

Do not let a strong overall score conceal a critical eligibility failure. Eligibility should be evaluated separately, and mandatory requirements should be identified clearly.

Distinguish among:

- Meets requirement.
- Partially meets requirement.
- Does not meet requirement.
- Unknown or insufficient evidence.

A missing field must not automatically be treated as proof that the candidate is ineligible.

## C. Matching interface

Display:

- Overall match score.
- Eligibility status.
- Matched skills.
- Missing required skills.
- Missing preferred skills.
- Most relevant projects.
- Most relevant experience.
- Relevant achievements.
- Important job responsibilities.
- Potential recruiter concerns.
- Recommended improvements.
- Confidence and data completeness.

For each requirement, show the candidate evidence that supports the assessment.

Example:

Requirement: REST API development.

Candidate evidence: Developed FastAPI endpoints in a document retrieval project.

Assessment: Strong match.

Requirement: Production Kubernetes experience.

Candidate evidence: No verified Kubernetes experience in the candidate profile.

Assessment: Unknown or missing evidence; do not claim proficiency.

## D. Personalized recommendations

Classify roles into configurable groups such as:

- Strong match.
- Worth applying.
- Stretch opportunity.
- Low priority.
- Potential eligibility issue.

Explain why every classification was assigned.

Allow candidates to prioritize learning, career direction, compensation, location, and likelihood of meeting requirements instead of optimizing solely for match score.

---

# 8. Module Five: AI LaTeX Resume Generator

Build a full resume-generation workflow that produces editable, job-specific LaTeX resumes.

This must be a real document-generation system, not just an AI response rendered inside a text box.

## A. Workflow

When the candidate opens a job and clicks "Generate Tailored Resume":

1. Load the complete candidate profile.
2. Load verified experience and project evidence.
3. Load the job description and matching report.
4. Select the most relevant verified projects and achievements.
5. Prioritize skills requested by the employer.
6. Rewrite bullet points for clarity, specificity, and relevance.
7. Improve action verbs and remove unnecessary wording.
8. Optimize section order and available space.
9. Preserve truthful education, experience, dates, technologies, and achievements.
10. Generate or update the LaTeX source.
11. Compile the source when a compatible LaTeX compiler is available.
12. Validate the generated document.
13. Display a PDF preview and editable source.
14. Allow the candidate to revise and approve the result.
15. Save the generated version against the corresponding job.

## B. LaTeX preservation and compilation

Provide a controlled resume template system rather than allowing the model to generate arbitrary LaTeX structures every time.

Support:

- Uploaded custom templates.
- A clean default ATS-friendly template.
- Single-column and compact layouts.
- Consistent typography and spacing.
- Configurable margins and font sizes.
- Section visibility and ordering.
- Bullet-point density.
- One-page and multi-page layouts.
- Unicode and special-character handling where supported.
- Consistent clickable links.

Preserve custom commands and uploaded template conventions where feasible.

Use a sandboxed compiler or isolated document-generation service if compilation is implemented.

Do not execute arbitrary uploaded shell commands or custom build scripts. Disable shell escape and apply sensible time, memory, file-access, and output-size limits.

If compilation fails, show a useful error message and preserve the editable source.

Do not claim a PDF was successfully produced until the file actually exists and has passed basic validation.

## C. ATS-oriented quality checks

Check for:

- Missing contact information.
- Unreadable or excessively complex layouts.
- Important skills absent from the resume despite being supported by verified evidence.
- Inconsistent date formatting.
- Spelling and grammar errors.
- Broken links.
- Excessive repetition.
- Unsupported claims.
- Poorly structured headings.
- Potential PDF text-extraction problems.
- Unnecessary graphics or formatting that can reduce machine readability.
- Unnecessary filler content.
- Lack of role-relevant evidence.

Do not claim to know an employer's proprietary ATS score. Provide explainable, practical resume-quality checks.

## D. Resume comparison

Show a before-and-after comparison.

For every significant change, explain:

- What changed.
- Why it changed.
- Which job requirement motivated the change.
- Which verified candidate fact supports it.

Let users accept or reject changes.

Support undo, version history, duplicate generation, and restoration of earlier versions.

## E. Export formats

Support, where available:

- Downloadable PDF.
- Editable `.tex` source.
- Downloadable LaTeX project archive containing required local assets.

Optionally export DOCX from the same structured resume data, but never silently replace LaTeX when the candidate specifically wants to maintain it.

---

# 9. Module Six: Personalized Cover Letter Generator

Create a separate AI workflow for cover letters.

Generate a tailored cover letter using:

- The actual job description.
- The company's available information.
- The candidate's verified experience.
- The most relevant projects.
- The specific reasons the candidate fits the role.
- The job's important requirements.
- Any candidate-provided motivation for applying.

The cover letter should be professional, specific, concise, natural, and free from generic AI filler.

It should answer:

1. Why this position?
2. Why this company, based on verified information or candidate-provided motivation?
3. Why this candidate?
4. What evidence demonstrates relevant ability?
5. What would the candidate contribute?

Never invent personal connections, knowledge of the company's culture, company achievements, or motivations.

Support multiple editing styles:

- Concise and direct.
- Technical and project-focused.
- Startup-oriented.
- Formal and traditional.

The candidate must be able to edit, regenerate, save, compare versions, and download the letter.

Provide a copy-to-clipboard function for application portals.

---

# 10. Module Seven: Company and Job Research

Build an AI-generated job research brief for each opportunity.

Collect company information from permitted public sources, official websites, the job listing, and relevant verified public documents.

Where source access is available, provide:

- Company overview.
- Products and services.
- Industry and business model.
- Target customers.
- Major business lines.
- Available company announcements.
- Publicly reported recent developments.
- Technical products or engineering challenges relevant to the role.
- Company size and location, when verifiable.
- Relevant company career-page information.
- The relationship between the company's work and the internship.

Also explain the position itself:

- What the intern is likely to work on.
- What skills matter most.
- What an ordinary working day might involve, where inferable.
- Which requirements appear essential.
- What the candidate should demonstrate in an interview.
- What information remains unknown.

Cite the source URL and retrieved date for external factual claims where possible.

Clearly label inferred responsibilities as interpretations rather than verified facts. Never invent funding rounds, revenue, headcount, customers, salary, or recent company developments.

Create a concise briefing that the candidate can understand in a few minutes before applying or interviewing.

---

# 11. Module Eight: Interview Preparation

After analyzing a job, generate a personalized interview preparation workspace.

## A. Suggested interview questions

Generate questions by category:

- Resume and project-based questions.
- Core programming concepts.
- Data structures and algorithms.
- Role-specific technical fundamentals.
- Framework and technology questions.
- Database and systems questions.
- Software engineering practices.
- System design, appropriate to the seniority.
- Behavioral questions.
- Situational questions.
- Company and product questions.
- Questions about the candidate's motivation.
- Questions about weaknesses or gaps in the resume.

Questions must reflect the actual requirements of the position and the candidate's stated experience.

Do not claim that the company will definitely ask a question unless an authoritative source supports that statement.

## B. Personalized answers

For each question, provide:

- Why the interviewer may ask it.
- What a strong answer should demonstrate.
- A suggested answer grounded in verified candidate experience.
- Relevant project evidence.
- Likely follow-up questions.
- Common mistakes to avoid.
- Further resources where useful.

For behavioral questions, use the STAR framework when appropriate.

Never fabricate work experience or claim the candidate personally implemented something they did not do.

Use interview answers as editable drafts, not scripts the candidate must memorize.

## C. Technical assessment preparation

Suggest practice topics based on the position, such as:

- Relevant LeetCode problem patterns.
- SQL exercises.
- API implementation tasks.
- Debugging exercises.
- Language-specific fundamentals.
- Framework questions.
- Project walkthroughs.
- Relevant take-home assignments or coding exercises.

Provide working problem-solving guidance, not just a generic list of interview topics.

Where external practice resources are included, use real links.

## D. Mock interview mode

Build an interactive mock interview experience.

The candidate should be able to choose:

- Technical or behavioral interview.
- Difficulty.
- Interview duration.
- Question category.
- Interviewer style.

Present one question at a time, accept the candidate's response, and provide constructive feedback on:

- Technical correctness.
- Completeness.
- Clarity.
- Specificity.
- Structure.
- Evidence from experience.
- Areas needing improvement.

Allow the candidate to retry answers and review past sessions.

---

# 12. Module Nine: Application Management CRM

Every opportunity should be manageable through a centralized application tracker.

## A. Application statuses

Support statuses such as:

- Discovered.
- Saved.
- To Review.
- Shortlisted.
- Preparing Application.
- Ready to Apply.
- Applied.
- Assessment Received.
- Interview Scheduled.
- Interview Completed.
- Offer Received.
- Rejected.
- Withdrawn.
- Position Closed.

Let candidates configure their own workflow.

Do not automatically mark a job as applied merely because a resume was generated, a website was opened, or an application link was clicked.

Only record an application as submitted when the candidate confirms submission or a trustworthy integration verifies it.

## B. Application records

Each application should retain:

- Associated job.
- Company.
- Position.
- Source.
- Application URL.
- Match report.
- Submitted resume version.
- Submitted cover letter.
- Application submission date.
- Current status.
- Recruiter or contact information, where provided.
- Interview dates.
- Assessment deadlines.
- Follow-up dates.
- Personal notes.
- Interview preparation materials.
- Feedback and outcome.
- Compensation and offer details, if applicable.

Preserve the exact materials associated with a submitted application even if the candidate subsequently edits their profile.

## C. Follow-ups and deadlines

Support manual follow-up reminders, calendar export, interview reminders, and deadline notifications where the necessary integration is configured.

Provide a dashboard showing:

- Applications due soon.
- Upcoming assessments.
- Upcoming interviews.
- Follow-ups due.
- Recently applied positions.
- Applications awaiting a response.
- Offers and rejections.

Build notification preferences rather than sending excessive reminders.

## D. Application submission

Make external application links easy to access.

If browser automation is implemented and permitted, use it only for supported workflows. Require explicit user approval before submitting an application or disclosing personal information.

Never bypass platform access controls, solve CAPTCHAs through evasion, or submit applications without the user's authorization.

Where reliable form automation is unavailable, provide a convenient assisted-application workflow with the prepared materials and original application link.

The platform should remain valuable even without fully automated submissions.

---

# 13. Module Ten: Candidate Dashboard and Analytics

Build a dashboard that helps the candidate understand their pipeline and make better decisions.

Include real, database-backed metrics:

- Total opportunities discovered.
- New jobs since the last visit.
- Saved jobs.
- Jobs matching the candidate's preferences.
- Applications submitted.
- Applications under review.
- Interviews scheduled.
- Offers received.
- Rejections.
- Application response rate.
- Interview conversion rate.
- Offer conversion rate.
- Average time between application and response, when sufficient data exists.

Include visualizations for:

- Application status distribution.
- Weekly application activity.
- Application outcomes over time.
- Top job categories.
- Most common required technologies.
- Match-score distribution.
- Performance by source platform.

Do not generate impressive-looking statistics from mock data or infer reliable conversion rates from an insufficient sample.

Explain the denominator used by each percentage.

Add an insights section that identifies actionable patterns, such as:

- Strong technical fit but recurring education eligibility issues.
- Roles with the highest match scores.
- Technologies frequently missing from shortlisted roles.
- Application sources associated with more interviews, when sufficient comparable data exists.
- Resume versions associated with different outcomes, when enough observations are available.

Be careful not to present correlation as causation.

---

# 14. Module Eleven: User Experience and Interface

Create a polished, professional, desktop-first application that works well on mobile.

The interface should feel like a sophisticated career productivity tool, not a generic AI chatbot or a cluttered job portal.

Use the existing design system where available. Otherwise, establish a coherent design system with:

- Clear typography.
- Consistent spacing.
- Restrained use of color.
- Accessible contrast.
- Subtle borders and shadows.
- Reusable components.
- Useful empty states.
- Responsive layouts.
- Consistent loading, error, and success states.
- Keyboard navigation and accessible form controls.

Avoid excessive gradients, unnecessary animations, decorative cards that do not add meaning, and oversized dashboard elements.

## Suggested primary navigation

**1. Dashboard**
A personalized overview of the job search.

**2. Discover Jobs**
Unified search, filters, source information, job recommendations, and match scores.

**3. Applications**
A table or kanban board covering the complete application pipeline.

**4. My Career Profile**
Personal details, education, work experience, skills, and preferences.

**5. Projects & Experience**
Full project portfolio, technical achievements, and evidence library.

**6. Resume Studio**
LaTeX upload, template selection, resume versions, job-specific generation, editing, compilation, preview, and export.

**7. Interview Prep**
Technical preparation, behavioral questions, mock interviews, and study plans.

**8. Company Research**
Saved companies, job briefs, and company-specific insights.

**9. Analytics**
Application funnel and outcome reporting.

**10. Settings**
AI configuration, integrations, notifications, data exports, privacy, and account preferences.

## Essential user journeys

The following flows must work from start to finish.

### Journey A: First-time setup

1. User creates an account or enters the supported local demo environment.
2. User uploads an existing LaTeX resume.
3. System parses available information.
4. User reviews and corrects extracted facts.
5. User imports or adds projects and their technologies.
6. User configures job preferences.
7. System saves the profile.
8. User reaches a personalized dashboard.

### Journey B: Discover and assess a job

1. User opens Discover Jobs.
2. User searches across configured sources.
3. Results are normalized and deduplicated.
4. User opens a job.
5. The platform loads or retrieves the match report.
6. User reviews required skills, eligibility, and gaps.
7. User saves the role or proceeds to preparation.

### Journey C: Prepare an application

1. User opens a job.
2. User generates a tailored resume.
3. User reviews the proposed changes.
4. User compiles and previews the LaTeX resume.
5. User downloads the PDF and source.
6. User generates and edits a cover letter.
7. User generates a company brief and interview questions.
8. User marks the application as ready.
9. User opens the original application link.
10. User confirms submission.
11. The system stores the exact resume and cover letter versions in the application record.

### Journey D: Prepare for an interview

1. User opens an application with an interview scheduled.
2. The platform loads the job description and submitted resume.
3. It generates relevant technical and behavioral questions.
4. User completes a mock interview.
5. The system saves feedback and practice history.
6. The user can review the preparation material before the interview.

---

# 15. Technical Architecture

Adapt this architecture to the repository rather than blindly replacing the existing stack.

If the current implementation already uses React, TypeScript, Tailwind CSS, FastAPI, Node.js, Prisma, SQLite, PostgreSQL, Supabase, or other compatible technologies, preserve and extend those components where appropriate.

A practical default for new components is:

### Frontend
- React with TypeScript.
- Existing routing and state management, or suitable established equivalents.
- Tailwind CSS and reusable accessible UI components.
- Server-state caching and explicit loading/error states.
- Markdown rendering for research and AI-generated explanations.
- PDF preview and downloadable generated artifacts.

### Backend
Use the existing backend framework wherever possible. If there is no suitable backend, choose an established framework such as FastAPI or Node.js with TypeScript.

Separate responsibilities into clear services:

- Authentication and user profiles.
- Resume parsing and generation.
- Project portfolio management.
- Job discovery.
- Source ingestion adapters.
- Job normalization and deduplication.
- Matching and ranking.
- AI document generation.
- Company research.
- Interview preparation.
- Application tracking.
- Analytics.
- Scheduled synchronization and notifications.

### Database
Use the current database or a reliable relational database appropriate to the deployment.

Core entities should include, at minimum:

- User.
- CandidateProfile.
- Education.
- Experience.
- Skill.
- CandidateProject.
- ProjectTechnology.
- EvidenceClaim.
- Resume.
- ResumeVersion.
- ResumeArtifact.
- JobSource.
- JobListing.
- JobRequirement.
- JobMatch.
- GeneratedDocument.
- Company.
- Application.
- ApplicationEvent.
- InterviewSession.
- InterviewQuestion.
- Reminder.
- IntegrationConfig.
- SyncRun.

Add proper primary keys, foreign keys, indexes, ownership checks, timestamps, and deletion behavior.

Use transactions for related updates and migrations for schema changes.

Avoid storing all business entities in a single unstructured JSON column. Use structured relational data where querying, integrity, and reporting benefit from it.

### File storage

Store resume sources, generated PDFs, source archives, and supporting files in appropriate file storage.

Use private storage for personal documents, ownership checks for every access, and expiring authorized download links if supported.

Do not place sensitive resumes or personal information in public directories.

### Background processing

Use a task queue or another established background execution method for operations such as:

- Job ingestion.
- Job deduplication.
- Batch matching.
- Resume compilation.
- Long-running AI generation.
- Document parsing.
- Notification delivery.

Provide job status, error reporting, and retry behavior.

Do not block interactive requests while scraping multiple sources or compiling large batches of documents.

### AI provider abstraction

Implement a provider layer instead of tightly coupling the application to one model vendor.

Support configurable API providers through environment variables and secure settings.

Centralize:

- Model selection.
- Prompt templates.
- Output schema validation.
- Token and cost limits.
- Timeouts.
- Retry logic.
- Error handling.
- Structured logging.
- Redaction of sensitive information where appropriate.

Use structured outputs for resume facts, job requirements, matching reports, and interview question sets whenever supported.

Validate all model-generated data before saving it.

### Semantic retrieval

Use embeddings or another appropriate semantic search method to retrieve relevant candidate projects and evidence for a particular job.

Start with a simple, reliable implementation. Add a vector database only when it improves retrieval enough to justify the operational complexity.

Do not require paid infrastructure for basic application functionality.

---

# 16. Database Security, Privacy, and Reliability

Treat resumes, personal details, application histories, and interview preparation as private information.

Implement:

- Authentication and session security.
- Server-side authorization.
- Per-user record ownership enforcement.
- Input validation.
- Safe file upload validation.
- Upload size limits.
- Rate limiting for expensive or abuse-prone endpoints.
- Secure secret handling.
- Protection against SQL injection and cross-site scripting.
- Secure document download routes.
- Appropriate logging without leaking private content.
- Account data export.
- Account deletion and associated data cleanup.
- Explicit settings for AI processing and external integrations.

Treat imported job descriptions, public websites, resumes, and repository content as untrusted data. They must never override system rules or cause the AI to disclose secrets, run untrusted instructions, or take unintended actions.

Use least-privilege access for integrations and background workers.

Keep external integration failure isolated from core profile, document, and application-management functionality.

---

# 17. Data Provenance and AI Grounding

This requirement applies across the entire platform.

All AI-generated materials must be grounded in the candidate's verified facts and the available job information.

Maintain traceability between:

- Original candidate information.
- Extracted profile facts.
- Verified project claims.
- Job requirements.
- Matching decisions.
- Resume changes.
- Generated cover letters.
- Suggested interview answers.

Do not invent:

- Technologies the candidate has never used.
- Employment or internship history.
- Metrics or project outcomes.
- Degrees, grades, certifications, or achievements.
- Job requirements.
- Company facts.
- Application deadlines.
- Compensation details.
- Claims about a company's interview process.

When information is unavailable, ask the candidate to supply it or mark it as unknown.

Distinguish clearly between facts, inferences, recommendations, and generated draft content.

Provide useful explanations for significant AI recommendations.

---

# 18. Performance and Cost Controls

Make the application efficient enough to support ongoing job discovery and repeated AI generation.

Implement:

- Pagination for large job lists.
- Indexed database queries.
- Appropriate caching.
- Incremental job synchronization.
- Reuse of unchanged job-analysis results.
- Reuse of candidate embeddings when profile data has not changed.
- Background execution for batch processing.
- Bounded retries.
- Request timeouts.
- Model cost tracking where supported.
- Reasonable per-user generation limits.
- Graceful handling of provider quotas.
- Clear feedback for long-running tasks.

Do not repeatedly re-run expensive matching or AI generation when the underlying candidate profile and job requirements have not changed.

Invalidate cached analysis when relevant source data or profile information changes.

---

# 19. API and Service Quality

Build clearly defined API contracts for each major feature.

Provide endpoints or equivalent backend operations for:

- Candidate profile management.
- Resume upload and parsing.
- Resume version management.
- Project portfolio management.
- Job source configuration.
- Job synchronization.
- Job search and filtering.
- Job details.
- Job matching.
- Resume generation and compilation.
- Cover letter generation.
- Company research.
- Interview questions and mock interviews.
- Application creation and status updates.
- Analytics.
- Notifications and reminders.

Use consistent response schemas, validation errors, authorization checks, and pagination.

Make long-running tasks return trackable job identifiers or an equivalent reliable task-status mechanism.

Document configuration, database migrations, development commands, testing commands, and deployment instructions.

Never return fake success responses from endpoints whose operations were not actually completed.

---

# 20. Testing Requirements

Do not consider the project complete simply because the frontend builds.

Create automated tests for important business logic and end-to-end workflows.

## Unit tests

Test:

- Job normalization.
- Duplicate detection.
- Requirement extraction.
- Match-score calculations.
- Eligibility handling.
- Project relevance ranking.
- Resume source transformations.
- LaTeX special-character escaping.
- Application status transitions.
- Analytics calculations.
- Input validation and ownership enforcement.

## Integration tests

Test:

- Database persistence.
- Resume upload and parsing.
- AI provider failures.
- Source adapter failures.
- Job ingestion and deduplication.
- Document generation.
- PDF compilation where available.
- Download permissions.
- Application creation and status changes.
- Background task failures and retries.

Use mocks for external services in deterministic tests, but also verify real integrations in environments where appropriate credentials and permitted access are available.

## End-to-end tests

Verify the complete journeys:

1. A candidate registers and creates a profile.
2. The candidate uploads a LaTeX resume.
3. The candidate adds several projects.
4. A real or explicitly labeled test job is imported.
5. The candidate receives an explainable match report.
6. A job-specific resume is generated.
7. The candidate can inspect the source and preview or download the PDF when compilation is configured.
8. A cover letter is generated.
9. Interview questions are produced.
10. The job is added to the application tracker.
11. Status changes persist after page refresh.
12. The dashboard reflects the actual database state.

Test empty states, network failures, invalid input, unauthorized access, duplicate jobs, expired listings, and missing configuration.

Run the tests available in the repository and fix failures caused by your changes.

---

# 21. Development and Delivery Strategy

Implement the product in the following priority order.

### Phase 1: Repair the foundation

Audit the existing codebase, fix runtime and build failures, establish stable navigation, verify persistence, and repair existing functionality.

### Phase 2: Candidate profile and project bank

Implement the candidate profile, resume ingestion, editable structured facts, project portfolio, and factual evidence storage.

### Phase 3: Job ingestion and discovery

Implement the canonical job schema, source adapters, permitted data ingestion, deduplication, search, filters, and detailed job pages.

Prioritize a small number of genuinely operational sources before expanding coverage. Clearly identify which integrations are operational and which need credentials or implementation.

### Phase 4: AI matching

Implement job analysis, explicit eligibility checks, evidence-grounded matching, and transparent match reports.

### Phase 5: Resume and cover letter studio

Implement job-specific LaTeX generation, document preview, compilation where configured, version management, comparison, editing, and export.

### Phase 6: Interview and company research

Implement company briefs, role-specific questions, suggested answers, mock interview sessions, and technical preparation.

### Phase 7: Application management and analytics

Implement the full pipeline, reminders, status history, dashboard metrics, and meaningful analytics.

### Phase 8: Hardening and deployment

Finish automated tests, security checks, responsive design, observability, documentation, and deployment configuration.

You may adjust this sequence to repair important dependencies or to make the existing application's architecture more reliable. Maintain working functionality at every stage.

---

# 22. Definition of Done

The following are mandatory acceptance criteria.

- The existing application builds and starts successfully.
- Core pages are functional and connected to backend services.
- Candidate information persists correctly across sessions.
- LaTeX resumes can be uploaded, parsed where supported, reviewed, and saved.
- Users can manage multiple projects and verified technologies.
- The job discovery system can import jobs from configured working sources.
- Unsupported sources are clearly identified rather than presented as functioning scrapers.
- Duplicate jobs are handled sensibly.
- Job matching includes explainable evidence and explicit eligibility analysis.
- Tailored resumes use real candidate information and actual job requirements.
- Generated LaTeX is editable and preserved independently from the original.
- PDF previews and downloads work when compilation is configured.
- Cover letters are editable and personalized.
- Company briefs distinguish source-backed facts from inference.
- Interview questions reflect the job and candidate's experience.
- Applications and their associated documents persist correctly.
- Application statuses and analytics reflect actual database records.
- Access to private files and user records is properly restricted.
- Errors are handled visibly and do not silently corrupt data.
- Critical workflows have automated tests.
- Environment configuration and setup instructions are documented.

Do not mark any requirement as complete merely because a button or screen exists.

---

# 23. How You Should Work

Operate directly on the existing repository using the tools available in the development environment.

Before modifying code:

1. Inspect the project structure.
2. Identify the entry points and current functionality.
3. Run the existing application and available tests.
4. Find and prioritize genuine defects.
5. Determine the minimal architectural changes required.

During implementation:

- Make actual code changes.
- Keep the UI and backend contracts consistent.
- Implement database migrations where needed.
- Test each major workflow.
- Resolve TypeScript, linting, build, runtime, and test errors caused by your changes.
- Use existing environment variables when possible.
- Add clear placeholders for missing secrets or unavailable external integrations.
- Do not hardcode credentials or personal information.
- Do not replace real logic with fabricated sample output.
- Do not leave primary actions wired to empty handlers.
- Do not suppress errors merely to make tests pass.
- Do not delete working functionality without justification.

If an external dependency is unavailable, implement the internal interface, provide a clear configuration path, and keep the rest of the application operational.

When you reach an external access limitation, state exactly what is blocked and what configuration or authorized access is required.

When a requirement cannot be completed in this environment, document the blocker and finish the independent parts rather than abandoning the entire application.

## Final deliverables

At the end of the implementation, provide:

1. A summary of what was repaired.
2. A list of features actually implemented.
3. The job sources that are genuinely operational.
4. The integrations that still require credentials or additional access.
5. Database and architecture changes.
6. The tests executed and their results.
7. Any known limitations or unresolved bugs.
8. Exact commands for running the application locally.
9. Required environment variables with example values that contain no real secrets.
10. Deployment instructions.

**The goal is a genuinely useful, persistent, and extensible AI internship application platform—not a visually impressive mockup. Prioritize correctness, working workflows, candidate privacy, and honest AI-generated content over superficial feature count. Start by inspecting the existing codebase, then implement the highest-priority repairs and continue through the full workflow.**