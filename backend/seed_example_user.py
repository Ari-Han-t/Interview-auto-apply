"""
Seed script to create a rich, realistic example user in the database.
User: Maya Patel (Senior Full-Stack & AI Systems Engineer)
Email: maya.patel@autoapply.dev
Password: AutoApply@2026!
"""
import os
import sys
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.profile import Profile
from app.models.candidate import (
    UserProfile,
    CandidateEducation,
    CandidateExperience,
    Project,
    Skill,
    UserSkill,
    UserPreference,
    CandidateCapability,
    Achievement,
    CourseCertification,
)
from app.models.resume import ResumeVersion
from app.models.job import Job, UserSavedJob
from app.models.application import Application
from app.models.cover_letter import CoverLetter
from app.models.company_research import CompanyResearch
from app.models.interview_prep import InterviewQuestion, MockInterviewSession


def seed_example_user():
    db = SessionLocal()
    try:
        email = "maya.patel@autoapply.dev"
        existing_user = db.query(User).filter(User.email == email).first()

        if existing_user:
            print(f"User {email} already exists (ID: {existing_user.id}). Updating profile and seeding associations...")
            user = existing_user
            user.hashed_password = get_password_hash("AutoApply@2026!")
            user.is_active = 1
        else:
            user = User(
                email=email,
                hashed_password=get_password_hash("AutoApply@2026!"),
                is_active=1,
            )
            db.add(user)
            db.flush()
            print(f"Created new user {email} (ID: {user.id})")

        now = datetime.now(timezone.utc)

        # 1. UserProfile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if not profile:
            profile = UserProfile(user_id=user.id)
            db.add(profile)

        profile.full_name = "Maya Patel"
        profile.preferred_name = "Maya"
        profile.email = email
        profile.phone = "+1 (415) 890-4321"
        profile.github = "https://github.com/mayapatel-dev"
        profile.linkedin = "https://linkedin.com/in/mayapatel-ai"
        profile.portfolio = "https://mayapatel.dev"
        profile.website = "https://mayapatel.dev"
        profile.current_location = "San Francisco, CA"
        profile.preferred_locations = ["San Francisco, CA", "New York, NY", "Remote"]
        profile.work_authorization = "US Citizen (No visa sponsorship required)"
        profile.visa_required = False
        profile.willing_to_relocate = True
        profile.remote_preference = "remote"
        profile.graduation_year = 2022
        profile.degree = "Bachelors"
        profile.specialization = "Computer Science & Artificial Intelligence"
        profile.cgpa = 3.88
        profile.university = "University of California, Berkeley"
        profile.coursework = [
            "Distributed Systems",
            "Database Systems",
            "Artificial Intelligence",
            "Algorithms & Complexity",
            "Operating Systems & Networking"
        ]
        profile.current_semester_or_year = "Alumni / 4+ Yrs Industry"
        profile.bio = (
            "Senior Full-Stack & AI Systems Engineer with 4+ years of experience architecting distributed backend "
            "services in Python and FastAPI, highly responsive web interfaces in TypeScript & Next.js, and autonomous "
            "LLM evaluation pipelines."
        )
        profile.availability = "Available (2 weeks notice period)"

        # 2. Legacy / Text Profile
        text_profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if not text_profile:
            text_profile = Profile(user_id=user.id)
            db.add(text_profile)

        text_profile.github_username = "mayapatel-dev"
        text_profile.raw_resume_text = (
            "MAYA PATEL\n"
            "San Francisco, CA | (415) 890-4321 | maya.patel@autoapply.dev\n"
            "GitHub: github.com/mayapatel-dev | LinkedIn: linkedin.com/in/mayapatel-ai | Portfolio: mayapatel.dev\n\n"
            "SUMMARY\n"
            "Senior Full-Stack & AI Systems Engineer specializing in FastAPI, Next.js, Redis, and multi-agent AI systems.\n\n"
            "EXPERIENCE\n"
            "NexaCloud AI — Senior Full-Stack Engineer (2023 - Present)\n"
            "Datablox Systems — Software Engineer (2022 - 2023)\n\n"
            "EDUCATION\n"
            "B.S. in Computer Science, UC Berkeley (2018 - 2022), GPA: 3.88\n"
        )
        text_profile.skills_json = {
            "languages": ["Python", "TypeScript", "JavaScript", "SQL", "Rust"],
            "frameworks": ["FastAPI", "Next.js", "React", "Node.js", "PyTorch"],
            "databases": ["PostgreSQL", "Redis", "SQLite"],
            "devops": ["Docker", "Kubernetes", "AWS", "GitHub Actions"]
        }

        # 3. CandidateEducation
        db.query(CandidateEducation).filter(CandidateEducation.user_id == user.id).delete()
        edu = CandidateEducation(
            user_id=user.id,
            institution="University of California, Berkeley",
            degree="Bachelor of Science",
            specialization="Computer Science",
            start_year=2018,
            graduation_year=2022,
            cgpa=3.88,
            gpa_scale="4.0",
            honors="Magna Cum Laude, Dean's Honors List",
            coursework=["Distributed Systems", "Cloud Computing", "AI Systems", "Operating Systems"],
            location="Berkeley, CA",
            bullets=[
                "Top 5% of engineering graduating class.",
                "Undergraduate research assistant in Scalable Systems Lab."
            ],
            is_visible=True,
            verification_status="verified",
        )
        db.add(edu)

        # 4. CandidateExperience
        db.query(CandidateExperience).filter(CandidateExperience.user_id == user.id).delete()
        exp1 = CandidateExperience(
            user_id=user.id,
            company="NexaCloud AI",
            title="Senior Full-Stack Engineer",
            start_date="2023-03",
            end_date="Present",
            currently_working=True,
            location="San Francisco, CA (Hybrid)",
            description=(
                "Architected distributed microservices and LLM-assisted workflow engines. "
                "Cut P99 API latency by 45% using FastAPI, Redis caching, and async queues. "
                "Led frontend migration to Next.js 15 App Router with TanStack Query and WebSocket telemetry."
            ),
            technologies=["Python", "FastAPI", "TypeScript", "Next.js", "PostgreSQL", "Redis", "Docker"],
            bullets=[
                "Architected distributed microservices and LLM-assisted workflow engines serving 500k+ active sessions.",
                "Cut P99 API latency by 45% using FastAPI, Redis caching, and background async queues.",
                "Led frontend migration to Next.js App Router with TanStack Query, cutting bundle size by 35%.",
                "Built resilient retry and token rate limiting middleware for OpenAI and Anthropic API endpoints."
            ],
            is_visible=True,
            verification_status="verified"
        )
        exp2 = CandidateExperience(
            user_id=user.id,
            company="Datablox Systems",
            title="Software Engineer",
            start_date="2022-06",
            end_date="2023-02",
            currently_working=False,
            location="San Jose, CA",
            description=(
                "Built scalable telemetry ingest pipelines processing over 3.5M daily event records with Kafka and PostgreSQL. "
                "Designed real-time monitoring dashboards with React and TailwindCSS."
            ),
            technologies=["Python", "React", "TypeScript", "Kafka", "PostgreSQL", "Docker", "TailwindCSS"],
            bullets=[
                "Engineered high-throughput event ingestion processing 3.5M+ events per day with zero data loss.",
                "Designed role-based access control and JWT session management across 12 distributed services.",
                "Authored 100+ unit and integration test suites achieving 94% code coverage."
            ],
            is_visible=True,
            verification_status="verified"
        )
        db.add_all([exp1, exp2])

        # 5. Projects
        db.query(Project).filter(Project.user_id == user.id).delete()
        proj1 = Project(
            user_id=user.id,
            name="OmniFlow Agent Engine",
            role="Creator & Lead Architect",
            description=(
                "Autonomous multi-agent framework orchestrating asynchronous tool execution, factual grounding "
                "verification, and token rate limiting with Azure OpenAI and Claude 3.5 Sonnet."
            ),
            technologies=["Python", "FastAPI", "LangChain", "Redis", "Docker", "Next.js"],
            github="https://github.com/mayapatel-dev/omniflow-agent",
            live_link="https://omniflow.dev",
            highlights=["Starred by 1,200+ developers on GitHub", "Sub-200ms agent step dispatching"],
            bullets=[
                "Designed DAG-based agent scheduler supporting dynamic tool calling and structured output parsing.",
                "Implemented automatic factual consistency verification against user candidate profiles."
            ],
            is_visible=True,
            verification_status="verified"
        )
        proj2 = Project(
            user_id=user.id,
            name="Distributed Vector Cache",
            role="Core Developer",
            description=(
                "High-throughput memory-mapped vector cache with cosine similarity clustering and sub-5ms "
                "retrieval for high-dimensional embeddings."
            ),
            technologies=["Python", "Rust", "C++", "PyTorch", "Docker"],
            github="https://github.com/mayapatel-dev/vector-cache",
            live_link="https://vectorcache.io",
            highlights=["Benchmarked against FAISS with 2.4x higher concurrency"],
            bullets=[
                "Implemented lock-free concurrent ring buffer for high-throughput embedding lookups.",
                "Integrated Python bindings via PyO3."
            ],
            is_visible=True,
            verification_status="verified"
        )
        db.add_all([proj1, proj2])

        # 6. Skills
        key_skills = [
            ("Python", "Programming Languages", "Expert", 5.0),
            ("TypeScript", "Programming Languages", "Advanced", 4.0),
            ("FastAPI", "Backend Frameworks", "Expert", 4.0),
            ("Next.js", "Frontend Frameworks", "Advanced", 4.0),
            ("React", "Frontend Frameworks", "Advanced", 4.0),
            ("PostgreSQL", "Databases & Storage", "Advanced", 4.0),
            ("Redis", "Databases & Storage", "Advanced", 3.5),
            ("Docker", "DevOps & Cloud", "Advanced", 4.0),
            ("LangChain & LLM APIs", "AI & Machine Learning", "Advanced", 2.5),
            ("TailwindCSS", "Frontend Frameworks", "Advanced", 4.0),
            ("Distributed Systems", "Architecture", "Advanced", 4.0),
            ("GraphQL & REST", "API Design", "Expert", 4.0),
        ]

        db.query(UserSkill).filter(UserSkill.user_id == user.id).delete()
        for s_name, cat, prof, yrs in key_skills:
            skill_record = db.query(Skill).filter(Skill.name == s_name).first()
            if not skill_record:
                skill_record = Skill(name=s_name)
                db.add(skill_record)
                db.flush()
            
            db.add(UserSkill(
                user_id=user.id,
                skill_id=skill_record.id,
                category=cat,
                confidence=5 if prof == "Expert" else 4,
                years_used=yrs,
                proficiency_level=prof,
                verification_status="verified",
                is_visible=True
            ))

        # 7. UserPreference
        pref = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
        if not pref:
            pref = UserPreference(user_id=user.id)
            db.add(pref)

        pref.minimum_salary = 155000
        pref.maximum_salary = 220000
        pref.preferred_roles = [
            "Senior Full-Stack Engineer",
            "Staff Software Engineer",
            "AI Systems Engineer",
            "Senior Backend Engineer"
        ]
        pref.preferred_locations = ["San Francisco, CA", "New York, NY", "Remote"]
        pref.remote_only = False
        pref.hybrid_allowed = True
        pref.onsite_allowed = True
        pref.preferred_job_type = "fulltime"
        pref.preferred_fulltime = True
        pref.preferred_internship = False
        pref.maximum_daily_applications = 10
        pref.notice_period = 14

        # 8. CandidateCapability
        cap = db.query(CandidateCapability).filter(CandidateCapability.user_id == user.id).first()
        if not cap:
            cap = CandidateCapability(user_id=user.id)
            db.add(cap)
        cap.can_relocate = True
        cap.can_work_remote = True
        cap.can_do_fulltime = True
        cap.can_do_internship = False
        cap.has_work_authorization = True
        cap.needs_sponsorship = False
        cap.open_to_startup = True
        cap.open_to_enterprise = True

        # 9. Achievements & Certifications
        db.query(Achievement).filter(Achievement.user_id == user.id).delete()
        ach1 = Achievement(
            user_id=user.id,
            title="UC Berkeley Hackathon 1st Place",
            category="hackathon",
            issuer_or_event="Cal Hacks",
            year_or_date="2021-11",
            description="Developed an automated accessibility audio reader for web documentation.",
            is_visible=True
        )
        ach2 = Achievement(
            user_id=user.id,
            title="Open Source Contributor of the Year",
            category="award",
            issuer_or_event="OpenWeb Foundation",
            year_or_date="2024-08",
            description="Recognized for core contributions to high-speed ASGI middleware.",
            is_visible=True
        )
        db.add_all([ach1, ach2])

        # 10. Master Resume Version
        db.query(ResumeVersion).filter(ResumeVersion.user_id == user.id).delete()
        resume_ver = ResumeVersion(
            user_id=user.id,
            name="Maya Patel — Full-Stack & AI Systems Master",
            storage_path="storage/resumes/maya_patel_master.pdf",
            file_type="pdf",
            version_number=1,
            is_master=True,
            target_role="Senior Full-Stack Engineer",
            template_name="clean_ats",
            notes="Tailored for senior full-stack and distributed backend positions.",
            parsed_json={
                "candidate": "Maya Patel",
                "title": "Senior Full-Stack & AI Systems Engineer",
                "phone": "+1 (415) 890-4321",
                "email": email,
                "skills": ["Python", "TypeScript", "FastAPI", "Next.js", "PostgreSQL", "Redis", "Docker"]
            }
        )
        db.add(resume_ver)
        db.flush()

        # 11. Applications linked to real database jobs
        jobs_in_db = db.query(Job).order_by(Job.id.asc()).limit(5).all()
        db.query(Application).filter(Application.user_id == user.id).delete()

        if len(jobs_in_db) >= 4:
            # App 1: Interview Scheduled
            app1 = Application(
                user_id=user.id,
                job_id=jobs_in_db[0].id,
                status="Interview Scheduled",
                source=jobs_in_db[0].source or "Greenhouse",
                applied_at=now - timedelta(days=6),
                submission_confirmed=True,
                resume_version_id=resume_ver.id,
                interview_date=now + timedelta(days=3, hours=2),
                interview_round="System Architecture & API Design Round",
                interview_notes="Prepare discussion on distributed caching and database read replicas.",
                assessment_deadline=now + timedelta(days=2),
                assessment_notes="Pre-interview design questionnaire due 24h prior.",
                follow_ups=[{
                    "id": "fu-101",
                    "title": "Review Google Cloud API Architecture and Kafka partitioning notes",
                    "due_date": (now + timedelta(days=1)).isoformat(),
                    "completed": False
                }],
                notes="Recruiter confirmed 45-minute technical screen."
            )

            # App 2: Assessment Received
            app2 = Application(
                user_id=user.id,
                job_id=jobs_in_db[1].id,
                status="Assessment Received",
                source=jobs_in_db[1].source or "Lever",
                applied_at=now - timedelta(days=4),
                submission_confirmed=True,
                resume_version_id=resume_ver.id,
                assessment_deadline=now + timedelta(days=4),
                assessment_notes="90-minute algorithmic and data pipeline challenge via Codesignal.",
                follow_ups=[{
                    "id": "fu-102",
                    "title": "Complete take-home coding challenge",
                    "due_date": (now + timedelta(days=3)).isoformat(),
                    "completed": False
                }],
                notes="Timed assessment link sent to email."
            )

            # App 3: Applied
            app3 = Application(
                user_id=user.id,
                job_id=jobs_in_db[2].id,
                status="Applied",
                source=jobs_in_db[2].source or "Ashby",
                applied_at=now - timedelta(days=2),
                submission_confirmed=True,
                resume_version_id=resume_ver.id,
                notes="Auto-applied with customized cover letter and tailored skills."
            )

            # App 4: Offer Received
            app4 = Application(
                user_id=user.id,
                job_id=jobs_in_db[3].id,
                status="Offer Received",
                source="Company Portal",
                applied_at=now - timedelta(days=14),
                submission_confirmed=True,
                resume_version_id=resume_ver.id,
                offer_compensation="$185,000 Base + $35,000 Equity + Bonus",
                notes="Offer letter received! Reviewing equity vesting schedule and benefits package."
            )

            db.add_all([app1, app2, app3, app4])
            db.flush()

            # 12. Cover Letter for App 1
            db.query(CoverLetter).filter(CoverLetter.user_id == user.id).delete()
            cl = CoverLetter(
                user_id=user.id,
                job_id=jobs_in_db[0].id,
                application_id=app1.id,
                style="technical",
                format="md",
                candidate_motivation="Deep passion for architecting resilient distributed systems and low-latency cloud infrastructure.",
                content=(
                    f"Dear Hiring Team at {jobs_in_db[0].company},\n\n"
                    f"I am writing to express my strong enthusiasm for the {jobs_in_db[0].title} opportunity. "
                    "With 4+ years of hands-on experience designing distributed backend architectures with FastAPI, "
                    "Python, and PostgreSQL, along with high-performance Next.js frontends, I have consistently delivered "
                    "reliable, scalable software that accelerates team velocity.\n\n"
                    "At NexaCloud AI, I led our core microservices redesign, reducing P99 latency by 45% while handling "
                    "over 500k active sessions. My open-source projects including OmniFlow Agent Engine demonstrate my "
                    "commitment to rigorous software practices, end-to-end type safety, and maintainable systems.\n\n"
                    f"I would welcome the opportunity to discuss how my background can drive impact at {jobs_in_db[0].company}.\n\n"
                    "Sincerely,\nMaya Patel"
                ),
                is_approved=True,
                version_number=1
            )
            db.add(cl)

            # 13. Company Research for Job 1
            db.query(CompanyResearch).filter(CompanyResearch.user_id == user.id).delete()
            cr = CompanyResearch(
                job_id=jobs_in_db[0].id,
                user_id=user.id,
                company_name=jobs_in_db[0].company,
                company_overview=f"{jobs_in_db[0].company} is a leading global technology company building high-scale developer platforms, distributed cloud services, and AI solutions.",
                products_and_services=["Developer APIs", "Cloud Infrastructure", "Enterprise Applications"],
                industry_and_business_model="Enterprise Cloud SaaS & Developer Platforms",
                target_customers_or_markets="Global enterprises, developers, and tech organizations",
                engineering_challenges=[
                    "High-throughput sub-millisecond API processing",
                    "Multi-region data consistency and disaster recovery",
                    "Resilient horizontal auto-scaling under traffic spikes"
                ],
                key_skills_in_position=["Python", "FastAPI", "Distributed Systems", "PostgreSQL", "Docker"],
                candidate_relevant_experience=[
                    "Led distributed backend optimization cutting P99 latency by 45% at NexaCloud AI",
                    "Engineered OmniFlow multi-agent framework handling concurrent asynchronous tasks"
                ],
                interview_topics_to_prep=[
                    "Designing a rate-limited distributed API gateway",
                    "Cache invalidation and database read replica synchronization",
                    "Handling partial network partitions and idempotent retry strategies"
                ],
                verified_facts=[
                    {"claim": f"{jobs_in_db[0].company} actively expands cloud infrastructure engineering teams.", "source": "Engineering Blog", "date": "2026-10"}
                ],
                inferred_insights=[
                    {"insight": "High emphasis on system reliability, type safety, and observability in production systems.", "rationale": "Extracted from job requirements"}
                ]
            )
            db.add(cr)

            # 14. Interview Prep & Mock Session
            db.query(InterviewQuestion).filter(InterviewQuestion.user_id == user.id).delete()
            iq = InterviewQuestion(
                job_id=jobs_in_db[0].id,
                user_id=user.id,
                category="system_design",
                difficulty="hard",
                question="How would you design a distributed job application queue that guarantees at-least-once delivery with idempotency?",
                why_it_matters="Tests candidate's deep understanding of distributed transactions, worker failures, and deduplication keys.",
                what_good_answer_demonstrates="Clear understanding of Redis streams, transactional outbox pattern, and idempotent database constraints.",
                suggested_answer="Use an Outbox table within the primary SQL transaction, coupled with an asynchronous CDC or Redis worker that consumes messages and uses a unique application hash to prevent duplicate submissions.",
                likely_follow_ups=[
                    "How do you handle worker crashes mid-submission?",
                    "What happens if downstream third-party job board responds with HTTP 429?"
                ],
                star_framework={
                    "situation": "High-volume application submissions with occasional network timeouts.",
                    "task": "Ensure zero lost submissions without creating duplicate job records.",
                    "action": "Implemented idempotency keys via SHA256 hashes stored in Redis with 24h TTL.",
                    "result": "Zero duplicate submissions across 500,000+ simulated application dispatches."
                },
                is_verified_company_question=True
            )
            db.add(iq)

            db.query(MockInterviewSession).filter(MockInterviewSession.user_id == user.id).delete()
            mock_session = MockInterviewSession(
                user_id=user.id,
                job_id=jobs_in_db[0].id,
                title="System Design & Distributed Scalability Mock",
                category="system_design",
                difficulty="hard",
                status="completed",
                overall_score=92.0,
                overall_feedback="Excellent structured approach to partitioning, failure modes, and database consistency trade-offs.",
                questions_json=[{
                    "question": "How do you handle rate-limiting across 10 distributed workers?",
                    "answer": "Used Redis token bucket with Lua scripts for atomic increments.",
                    "score": 95
                }]
            )
            db.add(mock_session)

            # 15. Saved Jobs
            db.query(UserSavedJob).filter(UserSavedJob.user_id == user.id).delete()
            db.add(UserSavedJob(user_id=user.id, job_id=jobs_in_db[0].id))
            db.add(UserSavedJob(user_id=user.id, job_id=jobs_in_db[1].id))

        db.commit()
        print(f"Successfully seeded complete profile and CRM data for {email} (User ID: {user.id})!")
        return user.id

    except Exception as e:
        db.rollback()
        print(f"Error seeding user: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_example_user()
