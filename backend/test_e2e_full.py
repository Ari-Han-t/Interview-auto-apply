import os
import sys
import json
import time

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, engine
from app.models.base import Base

def run_full_e2e_test():
    print("=====================================================================")
    print("      INTERVIEW AUTO-APPLY END-TO-END VERIFICATION SUITE")
    print("=====================================================================\n")

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    # 1. Register / Login test user
    test_email = f"e2e_user_{int(time.time())}@example.com"
    test_password = "SecurePassword123!"
    
    print(f"---> 1. Registering test user: {test_email}")
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": test_password,
        "name": "Alex Mercer"
    })
    print(f"Registration status: {reg_resp.status_code}")
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"

    print("---> 2. Logging in...")
    login_resp = client.post("/api/v1/auth/login", data={
        "username": test_email,
        "password": test_password
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    auth_cookies = login_resp.cookies
    print("Logged in successfully with session cookie.")

    # 3. Verify /auth/me
    me_resp = client.get("/api/v1/auth/me", cookies=auth_cookies)
    assert me_resp.status_code == 200, f"/auth/me failed: {me_resp.text}"
    user_data = me_resp.json()
    user_id = user_data["id"]
    print(f"User identity verified: ID={user_id}, Email={user_data['email']}")

    # 4. Upload Master LaTeX Resume
    print("\n---> 3. Uploading Master LaTeX Resume...")
    resume_path = os.path.join(os.path.dirname(__file__), "resume.tex")
    with open(resume_path, "rb") as f:
        upload_resp = client.post(
            "/api/v1/resume/upload",
            files={"file": ("resume.tex", f, "application/x-tex")},
            cookies=auth_cookies
        )
    assert upload_resp.status_code == 200, f"Resume upload failed: {upload_resp.text}"
    print("Resume uploaded successfully:", upload_resp.json())

    # 5. Populate Profile Graph & Knowledge Base
    print("\n---> 4. Setting Candidate Profile Graph & Preferences...")
    prof_update = client.put("/api/v1/profile/", json={
        "phone": "+1 555-0199",
        "current_location": "San Francisco, CA",
        "degree": "Bachelors in Computer Science",
        "grad_year": 2025,
        "years_experience": 2.0,
        "us_work_auth": True,
        "requires_sponsorship": False
    }, cookies=auth_cookies)
    assert prof_update.status_code == 200

    # Add an achievement (Hackathon winner)
    ach_resp = client.post("/api/v1/profile/achievements", json={
        "title": "1st Place Winner - AI Systems Hackathon 2024",
        "category": "hackathon",
        "issuer_or_event": "Global AI Challenge",
        "year_or_date": "2024",
        "description": "Architected low-latency distributed agent workflow."
    }, cookies=auth_cookies)
    assert ach_resp.status_code == 200
    print("Added candidate achievement (Hackathon Winner).")

    # Add a course certification
    course_resp = client.post("/api/v1/profile/courses", json={
        "name": "Distributed Systems & Cloud Architecture",
        "issuer": "Stanford Online",
        "issue_date": "2024",
        "credential_url": "https://credentials.stanford.edu/verify/12345",
        "skills_covered": ["Distributed Systems", "Cloud Computing", "Python"]
    }, cookies=auth_cookies)
    assert course_resp.status_code == 200, f"Add course failed: {course_resp.text}"
    print("Added candidate course certification.")

    # 6. GitHub Sync
    print("\n---> 5. Syncing GitHub Projects & Skills...")
    gh_sync_resp = client.post("/api/v1/github/sync", json={"github_username": "octocat"}, cookies=auth_cookies)
    print("GitHub sync response:", gh_sync_resp.json())
    assert gh_sync_resp.status_code == 200

    # 7. Job Discovery
    print("\n---> 6. Running Job Discovery...")
    disc_resp = client.post("/api/v1/jobs/discover", json={
        "source": "lever",
        "keywords": "Software Engineer",
        "location": "Remote",
        "job_type": "fulltime",
        "only_suited": False
    }, cookies=auth_cookies)
    print("Discovery triggered:", disc_resp.json())
    assert disc_resp.status_code == 200

    # Fetch jobs
    jobs_resp = client.get("/api/v1/jobs/", cookies=auth_cookies)
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    print(f"Discovered {len(jobs)} jobs in database.")
    assert len(jobs) > 0, "No jobs found in database."

    target_job = jobs[0]
    job_id = target_job["id"]
    print(f"Targeting Job ID={job_id}: '{target_job['title']}' at '{target_job['company']}'")

    # 8. Initialize Tailoring Room Background Pipeline
    print(f"\n---> 7. Initializing Tailoring Room Concurrent Pipeline for Job #{job_id}...")
    init_resp = client.post(f"/api/v1/applications/initialize/{job_id}", cookies=auth_cookies)
    assert init_resp.status_code == 200, f"Initialization failed: {init_resp.text}"
    app_id = init_resp.json()["application_id"]
    print(f"Created Application ID={app_id}. Polling progress checklist...")

    # 9. Poll progress until complete (LLM tailoring can take several minutes)
    max_wait = 420
    start_time = time.time()
    completed = False
    last_prog = {}
    while time.time() - start_time < max_wait:
        prog_resp = client.get(f"/api/v1/applications/{app_id}/progress", cookies=auth_cookies)
        assert prog_resp.status_code == 200
        prog_data = prog_resp.json()
        status = prog_data.get("status")
        last_prog = prog_data.get("progress", {})
        
        running_tasks = [k for k, v in last_prog.items() if v == "running"]
        completed_tasks = [k for k, v in last_prog.items() if v == "completed"]
        print(f"  Status: {status} | Completed tasks ({len(completed_tasks)}/6): {', '.join(completed_tasks)}")
        
        if status in ("generated", "completed") and len(completed_tasks) >= 4:
            completed = True
            break
        if status == "failed":
            break
        time.sleep(2)

    print(f"\nPipeline finished! Final status: {status}")
    print("Task progress summary:", json.dumps(last_prog, indent=2))
    assert status == "generated", f"Pipeline did not reach 'generated' status: {json.dumps(last_prog)}"

    # 10. Test PDF and LaTeX Download Endpoints
    print("\n---> 8. Testing Resume PDF & LaTeX Download Endpoints...")
    pdf_resp = client.get(f"/api/v1/applications/{app_id}/resume.pdf", cookies=auth_cookies)
    print(f"PDF download status: {pdf_resp.status_code}, content-type: {pdf_resp.headers.get('content-type')}, bytes: {len(pdf_resp.content)}")
    assert pdf_resp.status_code == 200
    assert len(pdf_resp.content) > 100

    tex_resp = client.get(f"/api/v1/applications/{app_id}/resume.tex", cookies=auth_cookies)
    print(f"LaTeX download status: {tex_resp.status_code}, content-type: {tex_resp.headers.get('content-type')}, bytes: {len(tex_resp.content)}")
    assert tex_resp.status_code == 200
    assert len(tex_resp.content) > 100

    # 11. Cover Letter Retrieval & Download
    print("\n---> 9. Testing Cover Letter Retrieval & Export...")
    cl_list_resp = client.get("/api/v1/cover-letters/", cookies=auth_cookies)
    assert cl_list_resp.status_code == 200
    cls = cl_list_resp.json()
    print(f"User has {len(cls)} cover letters.")
    if cls:
        cl_id = cls[0]["id"]
        cl_pdf_resp = client.get(f"/api/v1/cover-letters/download/{cl_id}?format=pdf", cookies=auth_cookies)
        assert cl_pdf_resp.status_code == 200
        print(f"Downloaded Cover Letter PDF: {len(cl_pdf_resp.content)} bytes.")

    # 12. Submit Application (Autopilot) & History Timeline
    print("\n---> 10. Submitting Application (Autopilot) & Verifying Timeline...")
    submit_resp = client.post(f"/api/v1/applications/{app_id}/submit", cookies=auth_cookies)
    assert submit_resp.status_code == 200
    print("Application submitted successfully.")

    history_resp = client.get(f"/api/v1/applications/{app_id}/history", cookies=auth_cookies)
    assert history_resp.status_code == 200
    timeline = history_resp.json()
    print(f"Application history events logged: {len(timeline)}")
    for ev in timeline:
        print(f"  - [{ev.get('from_status')} -> {ev.get('to_status')}] by {ev.get('actor')}: {ev.get('notes')}")

    # 13. Analytics Overview
    print("\n---> 11. Testing Analytics Overview...")
    analytics_resp = client.get("/api/v1/analytics/overview", cookies=auth_cookies)
    assert analytics_resp.status_code == 200
    print("Analytics overview:", json.dumps(analytics_resp.json(), indent=2))

    print("\n=====================================================================")
    print("   ALL 11 END-TO-END PRODUCT FLOW TESTS PASSED FLAWLESSLY!   ")
    print("=====================================================================\n")

if __name__ == "__main__":
    run_full_e2e_test()
