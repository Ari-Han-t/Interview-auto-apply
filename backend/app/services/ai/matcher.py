import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

client = None
api_key = os.getenv("GROQ_API_KEY")
if api_key:
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )

def analyze_job_match(profile_text: str, job_description: str) -> dict:
    """
    Analyzes a job description against a user's profile to determine match percentage,
    strengths, weaknesses, and missing keywords.
    """
    if not client:
        logger.warning("GROQ_API_KEY not set. Falling back to mock data.")
        import random
        match_percentage = random.randint(40, 95)
        missing_keywords = ["Python"] if "python" in job_description.lower() and "python" not in profile_text.lower() else []
        return {
            "match_percentage": match_percentage,
            "strengths": ["Strong educational background", "Relevant internship experience"],
            "weaknesses": ["Lacks production experience in some listed frameworks"],
            "missing_keywords": missing_keywords or ["Docker", "Kubernetes", "AWS"],
            "likelihood": "High" if match_percentage > 75 else "Medium"
        }

    import time
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant", # Or any model preferred by the user
                messages=[
                    {"role": "system", "content": "You are an expert technical recruiter. Analyze the job description against the user's profile. Respond ONLY in pure JSON format without markdown wrapping. Schema: { 'match_percentage': int, 'strengths': [str], 'weaknesses': [str], 'missing_keywords': [str], 'likelihood': str }"},
                    {"role": "user", "content": f"Profile:\n{profile_text}\n\nJob Description:\n{job_description}"}
                ]
            )
            content = response.choices[0].message.content.strip()
            
            # Strip potential markdown formatting if the model disobeys
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
                
            return json.loads(content)
            
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                logger.warning(f"Rate limited (429). Retrying in 5 seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(5)
                continue
            
            logger.error(f"Error calling Groq: {e}")
            # Fallback to mock on error
            return {
                "match_percentage": 50,
                "strengths": ["API Error - Mock Data"],
                "weaknesses": ["API Error - Mock Data"],
                "missing_keywords": ["API Error"],
                "likelihood": "Low"
            }

