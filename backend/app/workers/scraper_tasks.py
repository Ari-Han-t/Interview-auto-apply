from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.job import Job
from app.services.scraper.yc import scrape_yc_jobs
from app.services.scraper.linkedin import scrape_linkedin_jobs
from app.services.scraper.internshala import scrape_internshala_jobs
from app.services.scraper.greenhouse import scrape_greenhouse_jobs
from app.services.scraper.lever import scrape_lever_jobs
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def run_job_discovery(
    source: str = "yc",
    keywords: str = None,
    location: str = None,
    job_type: str = "both",
    only_suited: bool = True,
    user_id: int = None
):
    logger.info(f"Starting job discovery: source={source}, keywords={keywords}, location={location}, job_type={job_type}, user_id={user_id}")
    jobs = []
    effective_kw = keywords or "software engineer"
    effective_loc = location or "Remote"

    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        sources_to_run = [source] if source != "all" else ["linkedin", "internshala", "yc", "greenhouse", "lever"]
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_src = {}
            for src in sources_to_run:
                if src == "yc":
                    future_to_src[executor.submit(scrape_yc_jobs, effective_kw, job_type)] = "yc"
                elif src == "linkedin":
                    future_to_src[executor.submit(scrape_linkedin_jobs, effective_kw, effective_loc, job_type)] = "linkedin"
                elif src == "internshala":
                    future_to_src[executor.submit(scrape_internshala_jobs, effective_kw, effective_loc)] = "internshala"
                elif src == "greenhouse":
                    for board in ["stripe", "cloudflare", "figma"]:
                        future_to_src[executor.submit(scrape_greenhouse_jobs, board, effective_kw)] = f"greenhouse:{board}"
                elif src == "lever":
                    for company in ["spotify", "cloudflare", "postman"]:
                        future_to_src[executor.submit(scrape_lever_jobs, company, effective_kw)] = f"lever:{company}"
                else:
                    logger.warning(f"Unknown source: {src}")

            for future in as_completed(future_to_src):
                src_label = future_to_src[future]
                try:
                    res_jobs = future.result()
                    if res_jobs:
                        jobs.extend(res_jobs)
                except Exception as ex:
                    logger.warning(f"Scraper task for {src_label} failed: {ex}")

        db = SessionLocal()
        saved_count = 0
        try:
            from app.services.ai.eligibility import evaluate_eligibility
            
            for job_data in jobs:
                # Basic pre-filtering for job_type if specified
                title_desc = f"{job_data['title']} {job_data['description']}".lower()
                if job_type == "internship" and "intern" not in title_desc and job_data.get("source") != "internshala":
                    continue
                if job_type == "fulltime" and "intern" in title_desc:
                    continue

                existing = db.query(Job).filter(Job.url == job_data["url"]).first()
                target_job = None
                if not existing:
                    new_job = Job(
                        title=job_data["title"],
                        company=job_data["company"],
                        url=job_data["url"],
                        description=job_data["description"],
                        location=job_data.get("location", ""),
                        is_remote=job_data.get("is_remote", False),
                        salary_range=job_data.get("salary_range"),
                        source=job_data.get("source", source),
                        posted_at=job_data.get("posted_at")
                    )
                    db.add(new_job)
                    db.flush()
                    target_job = new_job
                else:
                    target_job = existing

                # Extract and cache requirements if missing
                if target_job and not target_job.requirements:
                    try:
                        title_lower = target_job.title.lower()
                        desc_lower = (target_job.description or "").lower()
                        is_intern = "intern" in title_lower or "internship" in title_lower or target_job.source == "internshala"
                        
                        # Fast heuristic extraction for instant scraping performance
                        common_techs = ["python", "javascript", "typescript", "react", "node", "java", "c++", "docker", "aws", "sql", "postgresql", "fastapi"]
                        extracted_techs = [t for t in common_techs if t in title_lower or t in desc_lower]
                        
                        from app.models.candidate import JobRequirement
                        job_req = JobRequirement(
                            job_id=target_job.id,
                            minimum_experience=0 if is_intern else (1 if "junior" in title_lower else 2),
                            maximum_experience=1 if is_intern else None,
                            minimum_degree="Bachelors",
                            required_skills=extracted_techs,
                            preferred_skills=[],
                            visa_required=False,
                            location=target_job.location or "Remote",
                            remote=target_job.is_remote or False,
                            salary=120000,
                            employment_type="Internship" if is_intern else "Full-time",
                            internship=is_intern,
                            fulltime=not is_intern,
                            contract=False,
                            technologies=extracted_techs,
                            keywords=extracted_techs,
                            company_size="Medium"
                        )
                        db.add(job_req)
                        db.flush()
                    except Exception as ex:
                        logger.error(f"Failed to extract requirements for job {target_job.id}: {ex}")

                # If user_id provided, evaluate resume suitability
                if target_job and user_id:
                    eval_res = evaluate_eligibility(user_id, target_job.id, db)
                    if only_suited and not eval_res.get("eligible", True):
                        # If strict suitability filtering is requested and not eligible, delete/rollback non-suited job
                        if not existing:
                            db.delete(target_job)
                        continue

                saved_count += 1

            db.commit()
            logger.info(f"Successfully processed and saved {saved_count} suited jobs for user {user_id}.")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
