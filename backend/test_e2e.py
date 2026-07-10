import os
import httpx
import time

def run_test():
    # 1. Login to get token
    print("1. Logging in...")
    login_resp = httpx.post("http://localhost:8000/api/v1/auth/login", data={"username": "test@example.com", "password": "password"})
    if login_resp.status_code != 200:
        print("Login failed:", login_resp.text)
        return
    token = login_resp.cookies.get("access_token")
    cookies = {"access_token": token}
    
    # 2. Upload the resume
    print("2. Uploading resume.tex...")
    with open("resume.tex", "rb") as f:
        files = {"file": ("resume.tex", f, "application/x-tex")}
        up_resp = httpx.post("http://localhost:8000/api/v1/resume/upload", files=files, cookies=cookies)
        print("Upload Response:", up_resp.json())
        
    # 3. Create a dummy job to test against
    print("3. Creating a dummy job in the DB...")
    from app.core.database import SessionLocal
    from app.models.job import Job
    db = SessionLocal()
    job = Job(
        title="Senior Software Engineer",
        company="Google",
        url="https://google.com/jobs",
        description="Looking for an expert backend engineer with strong Python, FastAPI, and Next.js skills. Must be able to architect robust APIs and deploy microservices. Experience with LLM integration is a huge plus."
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()
    
    print(f"Created Job ID: {job_id}")
    
    # 4. Trigger Application Generation
    print("4. Generating Application Materials (Tailored Resume + Cover Letter) via Groq LLM...")
    start = time.time()
    gen_resp = httpx.post(f"http://localhost:8000/api/v1/applications/generate/{job_id}", cookies=cookies, timeout=120.0)
    print(f"Generation Response (took {time.time() - start:.1f}s):", gen_resp.json())
    
if __name__ == "__main__":
    run_test()
