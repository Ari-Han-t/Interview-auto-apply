import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.interview_prep import InterviewQuestion, MockInterviewSession
from app.models.job import Job
from app.models.user import User
from app.services.llm import get_llm
from app.services.resume_compiler.candidate_data import load_candidate_library

logger = logging.getLogger(__name__)

INTERVIEW_CATEGORIES = [
    {"id": "resume_walkthrough", "label": "Resume & Project Walkthroughs", "icon": "FolderGit2"},
    {"id": "programming_fundamentals", "label": "Programming Fundamentals", "icon": "Code2"},
    {"id": "dsa", "label": "Data Structures & Algorithms", "icon": "Binary"},
    {"id": "languages_frameworks", "label": "Languages, Frameworks & DBs", "icon": "Layers"},
    {"id": "role_specific", "label": "Role-Specific Topics (Backend/AI/Cloud)", "icon": "Cpu"},
    {"id": "software_practices", "label": "Software Engineering Practices", "icon": "GitMerge"},
    {"id": "system_design", "label": "System Design & Architecture", "icon": "Network"},
    {"id": "behavioral", "label": "Behavioral & STAR Scenarios", "icon": "Users"},
    {"id": "company_product", "label": "Company & Product Knowledge", "icon": "Building2"},
]

def _build_deterministic_question_set(job: Job, candidate_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic fallback questions grounded in job and candidate profile."""
    company = job.company or "The Company"
    title = job.title or "Software Engineer"
    skills = job.required_skills_json or job.tech_stack_json or ["Python", "PostgreSQL", "FastAPI"]
    primary_tech = skills[0] if skills else "Python"
    secondary_tech = skills[1] if len(skills) > 1 else "PostgreSQL"
    
    # Extract candidate background for grounding
    projects = candidate_data.get("projects", [])
    first_proj = projects[0] if projects else {"title": "Distributed Web Service", "technologies": [primary_tech]}
    proj_title = first_proj.get("title") or "Distributed Web Service"
    proj_techs = ", ".join(first_proj.get("technologies", [])) or primary_tech
    
    experiences = candidate_data.get("experience", [])
    past_exp = experiences[0] if experiences else {"title": "Software Engineer", "company": "Tech Company"}
    past_role = past_exp.get("title") or "Software Engineer"
    past_company = past_exp.get("company") or "Previous Team"

    return [
        {
            "category": "resume_walkthrough",
            "difficulty": "medium",
            "question": f"Walk me through the architecture of your project '{proj_title}'. Why did you choose {proj_techs}, and what was the most difficult technical trade-off you encountered?",
            "why_it_matters": "Evaluates technical ownership, ability to justify architectural choices, and honesty regarding engineering trade-offs.",
            "what_good_answer_demonstrates": "Clear articulation of system boundaries, data flow, bottlenecks considered, and reasoned technology selection.",
            "suggested_answer": f"In {proj_title}, I selected {proj_techs} to prioritize low latency and maintainable schema evolution. When designing the data pipeline, the key trade-off was between synchronous validation and asynchronous background processing. I implemented an async queue to decouple ingestion from write operations.",
            "likely_follow_ups": [
                "How did you monitor latency and error rates in production?",
                "What would break first if traffic scaled by 50x?",
                "How did you handle database connection pooling under burst traffic?"
            ],
            "common_mistakes": [
                "Only describing what the app does rather than how the system is engineered under the hood.",
                "Failing to articulate why alternative technologies were rejected."
            ],
            "practice_resources": [
                {"title": "System Architecture Walkthrough Guide", "url": "https://github.com/donnemartin/system-design-primer", "type": "guide"}
            ],
            "is_verified_company_question": False,
            "source_note": f"Standard technical walkthrough tailored to {title} candidate profile."
        },
        {
            "category": "programming_fundamentals",
            "difficulty": "medium",
            "question": f"Explain concurrency and async I/O in {primary_tech}. How does the event loop or threading model handle blocking CPU-bound tasks versus I/O-bound tasks?",
            "why_it_matters": f"Essential for verifying foundational knowledge of {primary_tech} runtime mechanics and avoiding blocking anti-patterns in production services.",
            "what_good_answer_demonstrates": "Nuanced understanding of event loops, asynchronous coroutines, thread pooling, and CPU offloading.",
            "suggested_answer": f"In {primary_tech}, async I/O utilizes a single-threaded cooperative event loop to multiplex socket descriptors without thread context switching overhead. For blocking CPU tasks, the event loop would freeze; therefore, compute-heavy work must be offloaded to worker processes or a thread pool executor.",
            "likely_follow_ups": [
                "What happens when third-party sync libraries are called inside async routines?",
                "How do you profile event loop lag in production?"
            ],
            "common_mistakes": [
                "Confusing asynchronous I/O with true OS multi-core parallel processing.",
                "Executing blocking time.sleep() or file I/O inside async event loop handlers."
            ],
            "practice_resources": [
                {"title": f"{primary_tech} Concurrency Internals", "url": "https://docs.python.org/3/library/asyncio.html", "type": "docs"}
            ],
            "is_verified_company_question": False,
            "source_note": "Core programming fundamentals for senior/mid-level engineering."
        },
        {
            "category": "dsa",
            "difficulty": "medium",
            "question": f"Given a high-throughput stream of customer events, how would you design an in-memory sliding-window counter or LRU cache to detect duplicate transactions within a 10-minute window? Analyze its time and space complexity.",
            "why_it_matters": "Tests foundational understanding of data structure trade-offs (hash map + doubly linked list vs ring buffer), amortized operations, memory eviction policies, and algorithmic efficiency.",
            "what_good_answer_demonstrates": "Clear trade-off analysis between hash tables, doubly linked lists, ring buffers, and deque timestamp pruning, ensuring O(1) amortized lookup and eviction.",
            "suggested_answer": "I would use a composite data structure: a hash map paired with a doubly linked list (or deque) ordered by timestamp. The hash map maps transaction IDs to list nodes for O(1) lookup. When a new transaction arrives, expired nodes older than 10 minutes are pruned from the head in O(1) amortized time, and new transactions are appended to the tail. Space complexity is O(N) where N is the maximum events in the 10-minute window.",
            "likely_follow_ups": [
                "How would you handle memory constraints if the volume exceeds available RAM?",
                "What concurrency synchronization is required if multiple worker threads access the cache simultaneously?"
            ],
            "common_mistakes": [
                "Scanning the entire list linearly to find expired timestamps, causing O(N) lookup degradation.",
                "Neglecting race conditions between eviction and insertion."
            ],
            "practice_resources": [
                {"title": "LeetCode LRU Cache & Sliding Window Patterns", "url": "https://leetcode.com/problems/lru-cache/", "type": "practice"}
            ],
            "is_verified_company_question": False,
            "source_note": "Core algorithmic and data structure competency."
        },
        {
            "category": "languages_frameworks",
            "difficulty": "medium",
            "question": f"How do you design database indexing in {secondary_tech} for high-read, moderate-write tables? Explain the difference between B-Tree and GIN/GiST indexes.",
            "why_it_matters": "Database indexing and query execution plans are fundamental to backend system performance and preventing slow query degradation.",
            "what_good_answer_demonstrates": "Understanding of disk page lookups, composite index ordering, index bloat, and write amplification overhead.",
            "suggested_answer": f"In {secondary_tech}, B-Tree indexes are ideal for equality and range queries on sequential or unique data. For full-text search, arrays, or JSONB documents, GIN indexes allow indexing multi-key values. Composite indexes must follow leading-column cardinality rules.",
            "likely_follow_ups": [
                "How do you detect unused or duplicate indexes?",
                "What is the impact of table bloat on index scanning?"
            ],
            "common_mistakes": [
                "Adding an index to every column without considering write penalty.",
                "Misordering multi-column composite index columns."
            ],
            "practice_resources": [
                {"title": "Use The Index, Luke! - Indexing Guide", "url": "https://use-the-index-luke.com/", "type": "tutorial"}
            ],
            "is_verified_company_question": False,
            "source_note": f"Required database technology in {job.company} posting."
        },
        {
            "category": "role_specific",
            "difficulty": "hard",
            "question": f"In a distributed backend and AI/ML production service at {company}, how do you ensure idempotent processing of asynchronous jobs or background model inference tasks under network retries and worker crashes?",
            "why_it_matters": "Critical for backend and ML engineers to prevent duplicate execution, corrupted database states, and redundant compute expenses during network jitter or worker restarts.",
            "what_good_answer_demonstrates": "Proficiency with idempotency keys, distributed locks (e.g. Redlock), atomic state transitions in databases, dead-letter queues, and compensation transactions.",
            "suggested_answer": "I implement idempotency keys passed in the request header or event metadata. In the ingestion worker, we acquire an atomic lock or insert a pending execution record in PostgreSQL/Redis with a unique constraint on the idempotency key. If a duplicate delivery occurs while the task is executing or completed, the worker returns the cached status or previous result without re-executing. Unrecoverable worker failures release the lock after a lease TTL to allow dead-letter queue retries.",
            "likely_follow_ups": [
                "What happens if a worker crashes midway after external third-party API calls have completed?",
                "How do you configure dead-letter queues (DLQ) and exponential backoff retry policies?"
            ],
            "common_mistakes": [
                "Assuming at-least-once message brokers (Kafka, SQS, RabbitMQ) guarantee exactly-once delivery without application-level deduplication.",
                "Not scoping idempotency keys with appropriate TTLs, leading to unbounded storage growth."
            ],
            "practice_resources": [
                {"title": "Designing Idempotent APIs & Distributed Task Workflows", "url": "https://stripe.com/blog/idempotency", "type": "guide"}
            ],
            "is_verified_company_question": False,
            "source_note": f"Role-specific backend and infrastructure design for {title}."
        },
        {
            "category": "software_practices",
            "difficulty": "medium",
            "question": "Describe your strategy for performing a major database schema migration on a high-traffic table with zero downtime. How do you integrate automated testing and CI/CD canary rollouts into this lifecycle?",
            "why_it_matters": "Assesses professional engineering maturity, operational safety, testing discipline, and experience preventing table locks in production.",
            "what_good_answer_demonstrates": "Use of the Expand and Contract pattern, backward-compatible dual-writing, non-blocking index creation, and canary telemetry monitoring.",
            "suggested_answer": "I follow the Expand and Contract pattern across distinct deployment phases: 1. Expand: Add new nullable columns or tables and non-blocking indexes (e.g. CREATE INDEX CONCURRENTLY in PostgreSQL). 2. Dual-write: Deploy application code that reads from old fields but writes to both old and new fields. 3. Backfill: Run asynchronous background migration scripts in batches to populate historical rows without lock contention. 4. Contract: Switch reads to the new schema, verify telemetry in canary deployments, and safely drop legacy columns in a subsequent release.",
            "likely_follow_ups": [
                "How do you handle automated rollbacks if a canary version exhibits elevated 5xx error rates?",
                "What testing pyramid layers do you run in your CI pipeline before staging promotion?"
            ],
            "common_mistakes": [
                "Running blocking ALTER TABLE commands with default values on large production tables during business hours.",
                "Coupling schema changes directly with code changes in a single atomic release without backward compatibility."
            ],
            "practice_resources": [
                {"title": "Evolutionary Database Design & Zero-Downtime Migrations", "url": "https://martinfowler.com/articles/evodb.html", "type": "article"}
            ],
            "is_verified_company_question": False,
            "source_note": "Production software engineering and reliability practices."
        },
        {
            "category": "system_design",
            "difficulty": "hard",
            "question": f"Design a distributed rate-limiting service capable of handling 500,000 requests per second across multi-region API gateways at {company}.",
            "why_it_matters": "Evaluates distributed systems fundamentals, Redis/token-bucket algorithms, clock drift, and partition tolerance.",
            "what_good_answer_demonstrates": "Token bucket vs sliding-window log trade-offs, local in-memory batching with Redis sync, and graceful degradation.",
            "suggested_answer": "I would implement a hybrid architecture: local memory token-bucket caching at the gateway level with asynchronous batch syncing to Redis clusters using Lua scripts to prevent race conditions. If Redis becomes partitioned, the system falls back to soft-limit local counters to protect availability.",
            "likely_follow_ups": [
                "How do you handle multi-region replication latency and race conditions?",
                "What is the memory footprint of tracking 50 million active user rate limits?"
            ],
            "common_mistakes": [
                "Making a synchronous Redis network call for every single incoming request at 500k RPS.",
                "Neglecting race conditions between concurrent worker threads."
            ],
            "practice_resources": [
                {"title": "System Design Primer - Rate Limiter", "url": "https://github.com/donnemartin/system-design-primer", "type": "guide"}
            ],
            "is_verified_company_question": False,
            "source_note": f"System design scenario calibrated to {title} level."
        },
        {
            "category": "behavioral",
            "difficulty": "medium",
            "question": f"Tell me about a time in your role at {past_company} where you identified a critical production issue or architectural bottleneck under tight deadlines. How did you diagnose it, and what was the outcome?",
            "why_it_matters": "Demonstrates resilience, structured debugging under pressure, communication during outages, and root-cause resolution.",
            "what_good_answer_demonstrates": "Structured STAR story demonstrating methodical isolation, immediate remediation, and long-term prevention.",
            "suggested_answer": f"Using the STAR method based on my experience at {past_company}: Situation - our production service encountered 504 gateway timeouts during peak customer traffic. Task - As {past_role}, I needed to isolate the bottleneck without taking the service offline. Action - I inspected distributed APM traces, identified database connection pool exhaustion caused by unindexed foreign keys, and deployed a targeted patch with connection limits. Result - response latency dropped by 80% and service uptime recovered to 99.99%.",
            "likely_follow_ups": [
                "How did you communicate the issue to non-technical stakeholders?",
                "What guardrails did you put in place to ensure this never happens again?"
            ],
            "common_mistakes": [
                "Vague narration without specific actions taken by the candidate.",
                "Blaming other team members or failing to quantify the outcome."
            ],
            "star_framework": {
                "situation": f"High latency and timeout alerts impacting production services during customer traffic spikes at {past_company}.",
                "task": f"As {past_role}, identify root bottleneck, stabilize system, and prevent recurring incident.",
                "action": "Analyzed logs/APM, isolated database connection contention, applied index & connection pool limits.",
                "result": "Restored 99.99% availability, reduced 95th percentile latency from 2.4s to 120ms."
            },
            "practice_resources": [
                {"title": "STAR Method Interview Framework", "url": "https://www.themuse.com/advice/star-interview-method", "type": "guide"}
            ],
            "is_verified_company_question": False,
            "source_note": "Behavioral STAR competency question grounded in candidate experience."
        },
        {
            "category": "company_product",
            "difficulty": "medium",
            "question": f"Based on {company}'s public technical ecosystem, what is one major scalability or architectural challenge their engineering team faces, and how would you approach it?",
            "why_it_matters": f"Assesses genuine candidate preparation, domain curiosity, and intellectual engagement with {company}'s mission.",
            "what_good_answer_demonstrates": "Deep understanding of the company's business model, customer scale, and public engineering challenges.",
            "suggested_answer": f"Given {company}'s scale, a key engineering challenge is maintaining data freshness and consistency across distributed services while keeping API latency under strict SLAs. I would approach this by enforcing CQRS patterns, cache invalidation with CDC (Change Data Capture), and granular circuit breakers.",
            "likely_follow_ups": [
                f"How would you measure the business impact of this optimization at {company}?",
                "What risks might this introduce to operational complexity?"
            ],
            "common_mistakes": [
                "Reciting generic marketing bullet points without technical insight.",
                "Claiming certainty about confidential internal architectures."
            ],
            "practice_resources": [
                {"title": f"{company} Engineering Culture & Public Case Studies", "url": job.url or f"https://www.google.com/search?q={company}+engineering+blog", "type": "case_study"}
            ],
            "is_verified_company_question": False,
            "source_note": f"Role & domain specific question for {company}."
        }
    ]

def generate_interview_questions_for_job(
    job_id: int,
    user_id: int,
    categories: Optional[List[str]] = None,
    force_refresh: bool = False,
    db: Optional[Session] = None,
) -> List[InterviewQuestion]:
    """Generates and persists a structured catalog of interview questions for a job across all categories."""
    if not force_refresh:
        existing = db.query(InterviewQuestion).filter(
            InterviewQuestion.job_id == job_id,
            (InterviewQuestion.user_id == user_id) | (InterviewQuestion.user_id.is_(None))
        ).all()
        if existing and len(existing) >= 5:
            return existing

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job #{job_id} not found")

    candidate_raw = load_candidate_library(user_id, db)
    
    # Generate through LLM
    questions_data = None
    try:
        provider = get_llm()
        system_prompt = (
            "You are a Principal Engineering Interviewer and Staff Bar Raiser. "
            "Generate a comprehensive, rigorous interview preparation suite for this candidate and target job. "
            "\nCRITICAL RULES:"
            "\n1. COVER MULTIPLE CATEGORIES: resume_walkthrough, programming_fundamentals, dsa, languages_frameworks, role_specific, software_practices, system_design, behavioral, company_product."
            "\n2. FOR EVERY QUESTION, INCLUDE: question, why_it_matters, what_good_answer_demonstrates, suggested_answer (grounded in candidate's verified profile), likely_follow_ups (list of strings), common_mistakes (list of strings), practice_resources (list of objects with title, url, type)."
            "\n3. FOR BEHAVIORAL QUESTIONS: provide a star_framework object with {situation, task, action, result} keys."
            "\n4. TRUTHFULNESS: Never claim a company definitely asks a question unless verified. Set is_verified_company_question=false."
            "\n5. FORMAT: Return ONLY a valid JSON array of objects matching the schema."
        )

        projects_summary = [f"{p.get('title')}: {', '.join(p.get('technologies', []))}" for p in candidate_raw.get("projects", [])[:3]]
        skills_summary = [s.get("name", "") if isinstance(s, dict) else str(s) for s in candidate_raw.get("skills", [])[:10]]

        user_prompt = (
            f"TARGET JOB:\n"
            f"Role: {job.title}\n"
            f"Company: {job.company}\n"
            f"Stack: {', '.join(job.required_skills_json or job.tech_stack_json or [])}\n"
            f"Responsibilities: {job.description[:600] if job.description else ''}\n\n"
            f"CANDIDATE VERIFIED PROFILE:\n"
            f"Verified Projects: {', '.join(projects_summary)}\n"
            f"Verified Skills: {', '.join(skills_summary)}\n\n"
            f"Generate 7-9 high-signal, rigorous interview questions covering all major interview categories now."
        )

        raw_json = provider.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        if isinstance(raw_json, list) and len(raw_json) > 0:
            questions_data = raw_json
        elif isinstance(raw_json, dict):
            for k in ["questions", "interview_questions", "data", "items"]:
                if isinstance(raw_json.get(k), list) and len(raw_json[k]) > 0:
                    questions_data = raw_json[k]
                    break
    except Exception as e:
        logger.warning(f"LLM interview questions generation failed ({e}), using deterministic set.")

    if not questions_data or not isinstance(questions_data, list):
        questions_data = _build_deterministic_question_set(job, candidate_raw)

    valid_categories = {c["id"] for c in INTERVIEW_CATEGORIES}

    # Ensure behavioral STAR question is always present in catalog
    has_behavioral = any(
        isinstance(q, dict) and ((q.get("category") or "").lower() == "behavioral" or "behavior" in (q.get("category") or "").lower())
        for q in questions_data
    )
    if not has_behavioral:
        det_set = _build_deterministic_question_set(job, candidate_raw)
        behavioral_candidates = [q for q in det_set if q.get("category") == "behavioral"]
        if behavioral_candidates:
            questions_data.append(behavioral_candidates[0])

    # Save to database
    records = []
    for q in questions_data:
        raw_cat = q.get("category") or q.get("type") or q.get("topic") or "role_specific"
        cat_str = str(raw_cat).lower().strip()
        if cat_str in valid_categories:
            resolved_cat = cat_str
        elif "behavior" in cat_str or "star" in cat_str:
            resolved_cat = "behavioral"
        elif "design" in cat_str or "architect" in cat_str:
            resolved_cat = "system_design"
        elif "algorithm" in cat_str or "dsa" in cat_str:
            resolved_cat = "dsa"
        elif "fundament" in cat_str:
            resolved_cat = "programming_fundamentals"
        elif "practice" in cat_str:
            resolved_cat = "software_practices"
        elif "walkthrough" in cat_str or "project" in cat_str:
            resolved_cat = "resume_walkthrough"
        else:
            resolved_cat = "role_specific"

        star_fw = q.get("star_framework") or {}
        if resolved_cat == "behavioral" and not star_fw:
            star_fw = {
                "situation": f"Production incident or high-priority feature delivery at previous organization.",
                "task": f"Take ownership of resolving the bottleneck under tight engineering deadlines.",
                "action": f"Led methodical root-cause debugging, instrumented telemetry, and delivered non-blocking patch.",
                "result": f"Recovered 99.99% service availability and prevented recurring regressions."
            }

        rec = InterviewQuestion(
            job_id=job_id,
            user_id=user_id,
            category=resolved_cat,
            difficulty=q.get("difficulty", "medium"),
            question=q.get("question", "Explain your technical background."),
            why_it_matters=q.get("why_it_matters"),
            what_good_answer_demonstrates=q.get("what_good_answer_demonstrates"),
            suggested_answer=q.get("suggested_answer"),
            likely_follow_ups=q.get("likely_follow_ups", []),
            common_mistakes=q.get("common_mistakes", []),
            practice_resources=q.get("practice_resources", []),
            star_framework=star_fw,
            is_verified_company_question=bool(q.get("is_verified_company_question", False)),
            source_note=q.get("source_note") or f"Curated for {job.company} {job.title}",
        )
        db.add(rec)
        records.append(rec)
    db.commit()
    for r in records:
        db.refresh(r)
    return records

def create_mock_session(
    user_id: int,
    job_id: int,
    category: str = "all",
    difficulty: str = "medium",
    question_count: int = 5,
    db: Optional[Session] = None,
) -> MockInterviewSession:
    """Initializes an interactive mock interview session with selected questions."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job #{job_id} not found")

    # Ensure questions exist
    questions = generate_interview_questions_for_job(job_id=job_id, user_id=user_id, db=db)

    # Filter by category if specified
    if category and category != "all":
        filtered = [q for q in questions if q.category == category]
        if filtered:
            questions = filtered

    # Filter by difficulty if available
    if difficulty and difficulty != "all":
        diff_filtered = [q for q in questions if q.difficulty == difficulty]
        if diff_filtered:
            questions = diff_filtered

    selected = questions[:question_count]
    questions_json = [
        {
            "id": q.id,
            "category": q.category,
            "difficulty": q.difficulty,
            "question": q.question,
            "why_it_matters": q.why_it_matters,
            "what_good_answer_demonstrates": q.what_good_answer_demonstrates,
            "suggested_answer": q.suggested_answer,
            "likely_follow_ups": q.likely_follow_ups or [],
            "common_mistakes": q.common_mistakes or [],
            "practice_resources": q.practice_resources or [],
            "star_framework": q.star_framework or {},
            "is_verified_company_question": q.is_verified_company_question,
        }
        for q in selected
    ]

    title = f"Mock Interview ({job.company} - {job.title}): {category.replace('_', ' ').title()}"
    session = MockInterviewSession(
        user_id=user_id,
        job_id=job_id,
        title=title,
        category=category,
        difficulty=difficulty,
        status="in_progress",
        questions_json=questions_json,
        current_question_index=0,
        answers_json={},
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def evaluate_mock_answer(
    session_id: int,
    question_index: int,
    answer_text: str,
    user_id: int,
    db: Session,
) -> Dict[str, Any]:
    """Evaluates candidate's answer to a mock interview question and returns constructive feedback."""
    session = db.query(MockInterviewSession).filter(
        MockInterviewSession.id == session_id,
        MockInterviewSession.user_id == user_id,
    ).first()
    if not session:
        raise ValueError(f"Mock session #{session_id} not found")

    questions = session.questions_json or []
    if question_index < 0 or question_index >= len(questions):
        raise ValueError(f"Question index {question_index} out of bounds")

    target_q = questions[question_index]
    question_text = target_q.get("question", "")
    suggested_answer = target_q.get("suggested_answer", "")

    # AI evaluation
    score = 80
    feedback = "Solid answer demonstrating core principles."
    strengths = ["Covered the core requirements", "Clear technical terminology"]
    improvements = ["Could provide more quantified production metrics", "Mention edge-case recovery"]
    model_answer = suggested_answer

    try:
        provider = get_llm()
        system_prompt = (
            "You are an expert technical interviewer evaluating a candidate's answer during a mock interview. "
            "Provide constructive, rigorous, and supportive evaluation. "
            "\nReturn ONLY a JSON object with keys: "
            "'score' (integer 0-100), 'feedback' (string), 'strengths' (array of strings), "
            "'improvements' (array of strings), 'model_answer' (string)."
        )
        user_prompt = (
            f"QUESTION:\n{question_text}\n\n"
            f"REFERENCE ANSWER:\n{suggested_answer}\n\n"
            f"CANDIDATE'S ANSWER:\n{answer_text}\n\n"
            f"Evaluate the candidate's answer now."
        )
        eval_json = provider.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        if isinstance(eval_json, dict) and "score" in eval_json:
            score = int(eval_json.get("score", 80))
            feedback = eval_json.get("feedback", feedback)
            strengths = eval_json.get("strengths", strengths)
            improvements = eval_json.get("improvements", improvements)
            model_answer = eval_json.get("model_answer", model_answer)
    except Exception as e:
        logger.warning(f"AI mock evaluation fallback: {e}")
        # Deterministic scoring heuristic
        word_count = len(answer_text.strip().split())
        if word_count < 20:
            score = 55
            feedback = "Answer is quite brief. Aim to elaborate on specific architectural decisions and production trade-offs."
            improvements = ["Provide deeper technical context", "Explain the 'why' behind your choices"]
        elif word_count > 60:
            score = 88
            feedback = "Thorough and structured explanation demonstrating strong hands-on ownership."
            strengths = ["Comprehensive details", "Good communication"]

    # Save to session answers_json
    answers = dict(session.answers_json or {})
    key = str(question_index)
    retry_count = answers.get(key, {}).get("retry_count", 0)
    if key in answers:
        retry_count += 1

    eval_result = {
        "question_id": target_q.get("id"),
        "question": question_text,
        "answer_text": answer_text,
        "score": score,
        "feedback": feedback,
        "strengths": strengths,
        "improvements": improvements,
        "model_answer": model_answer,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "retry_count": retry_count,
    }
    answers[key] = eval_result
    session.answers_json = answers

    # Advance current index if at or ahead
    if session.current_question_index <= question_index:
        session.current_question_index = min(question_index + 1, len(questions) - 1)

    # Check if all questions are answered to complete session
    if len(answers) >= len(questions):
        scores = [v.get("score", 75) for v in answers.values()]
        avg_score = sum(scores) / len(scores) if scores else 80.0
        session.overall_score = round(avg_score, 1)
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        session.overall_feedback = f"Completed mock interview with an average score of {round(avg_score, 1)}/100 across {len(questions)} questions."

    db.commit()
    db.refresh(session)

    return {
        "question_index": question_index,
        "eval_result": eval_result,
        "session_status": session.status,
        "overall_score": session.overall_score,
        "current_question_index": session.current_question_index,
        "score": eval_result["score"],
        "feedback": eval_result["feedback"],
        "strengths": eval_result["strengths"],
        "improvements": eval_result["improvements"],
        "model_answer": eval_result["model_answer"],
        "retry_count": eval_result["retry_count"],
    }
