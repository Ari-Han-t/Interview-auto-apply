import re
import uuid
from typing import Dict, List, Any, Optional

# Curated knowledge dictionary of technology taxonomies
TECH_DICTIONARY = {
    "programming_languages": {
        "Python": [r"\bpython\b", r"\bpy3\b"],
        "TypeScript": [r"\btypescript\b", r"\bts\b"],
        "JavaScript": [r"\bjavascript\b", r"\bjs\b", r"\bes6\b", r"\bnode(?:\.js)?\b"],
        "Go": [r"\bgolang\b", r"\bgo\s+language\b", r"\bgo\b"],
        "Rust": [r"\brust\b", r"\bcargo\b"],
        "C++": [r"\bc\+\+\b", r"\bcpp\b"],
        "C": [r"\bclang\b", r"\bc\s+programming\b"],
        "Java": [r"\bjava\b", r"\bjvm\b"],
        "Kotlin": [r"\bkotlin\b"],
        "Swift": [r"\bswift\b"],
        "SQL": [r"\bsql\b", r"\bstructured\s+query\s+language\b"],
        "HTML/CSS": [r"\bhtml5?\b", r"\bcss3?\b"],
        "R": [r"\br\s+language\b", r"\brlang\b"],
        "Scala": [r"\bscala\b"],
    },
    "frameworks": {
        "FastAPI": [r"\bfastapi\b"],
        "React": [r"\breact(?:\.js)?\b"],
        "Next.js": [r"\bnext(?:\.js)?\b"],
        "Django": [r"\bdjango\b"],
        "Flask": [r"\bflask\b"],
        "Express": [r"\bexpress(?:\.js)?\b"],
        "Vue": [r"\bvue(?:\.js)?\b"],
        "Angular": [r"\bangular\b"],
        "Spring Boot": [r"\bspring\s+boot\b", r"\bspring\b"],
        "Node.js": [r"\bnode(?:\.js)?\b"],
        "NestJS": [r"\bnest(?:\.js)?\b"],
        "TailwindCSS": [r"\btailwind(?:css)?\b"],
    },
    "libraries": {
        "Pydantic": [r"\bpydantic\b"],
        "SQLAlchemy": [r"\bsqlalchemy\b"],
        "Redux": [r"\bredux\b"],
        "Celery": [r"\bcelery\b"],
        "Pandas": [r"\bpandas\b"],
        "NumPy": [r"\bnumpy\b"],
        "SciPy": [r"\bscipy\b"],
        "Axios": [r"\baxios\b"],
        "Zod": [r"\bzod\b"],
        "Prisma": [r"\bprisma\b"],
        "Lucide React": [r"\blucide\b"],
    },
    "databases": {
        "PostgreSQL": [r"\bpostgres(?:ql)?\b"],
        "SQLite": [r"\bsqlite3?\b"],
        "Redis": [r"\bredis\b"],
        "MongoDB": [r"\bmongo(?:db)?\b"],
        "MySQL": [r"\bmysql\b"],
        "Elasticsearch": [r"\belasticsearch\b", r"\belastic\b"],
        "Supabase": [r"\bsupabase\b"],
        "DynamoDB": [r"\bdynamodb\b"],
        "Firebase Firestore": [r"\bfirestore\b", r"\bfirebase\b"],
        "Neo4j": [r"\bneo4j\b"],
        "FAISS": [r"\bfaiss\b"],
        "ChromaDB": [r"\bchroma(?:db)?\b"],
        "Pinecone": [r"\bpinecone\b"],
        "Qdrant": [r"\bqdrant\b"],
    },
    "apis": {
        "REST API": [r"\brest(?:ful)?(?:\s+api)?\b"],
        "GraphQL": [r"\bgraphql\b"],
        "gRPC": [r"\bgrpc\b"],
        "WebSockets": [r"\bwebsocket(?:s)?\b"],
        "OAuth 2.0": [r"\boauth2?(?:\.0)?\b"],
        "Stripe API": [r"\bstripe\b"],
        "OpenAI API": [r"\bopenai\s+api\b"],
        "GitHub API": [r"\bgithub\s+api\b"],
    },
    "ai_ml_techniques": {
        "PyTorch": [r"\bpytorch\b"],
        "TensorFlow": [r"\btensorflow\b"],
        "Scikit-learn": [r"\bscikit-learn\b", r"\bsklearn\b"],
        "LangChain": [r"\blangchain\b"],
        "HuggingFace": [r"\bhuggingface\b", r"\btransformers\b"],
        "RAG (Retrieval-Augmented Generation)": [r"\brag\b", r"\bretrieval[\s-]augmented\b"],
        "Vector Embeddings": [r"\bvector\s+embedding(?:s)?\b", r"\bembeddings?\b"],
        "Fine-tuning / LoRA": [r"\bfine-tuning\b", r"\blora\b", r"\bqlora\b"],
        "Computer Vision": [r"\bcomputer\s+vision\b", r"\bcv\b", r"\byolo\b"],
        "NLP": [r"\bnlp\b", r"\bnatural\s+language\s+processing\b"],
        "LLM Agents": [r"\bagents?\b", r"\bllm\s+agent\b"],
    },
    "deployment_technologies": {
        "Docker": [r"\bdocker\b", r"\bdockerfile\b", r"\bcontainer(?:s)?\b"],
        "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
        "AWS": [r"\baws\b", r"\bamazon\s+web\s+services\b", r"\bs3\b", r"\bec2\b"],
        "Google Cloud (GCP)": [r"\bgcp\b", r"\bgoogle\s+cloud\b"],
        "Vercel": [r"\bvercel\b"],
        "GitHub Actions / CI/CD": [r"\bgithub\s+actions\b", r"\bci/cd\b", r"\bpipeline(?:s)?\b"],
        "Nginx": [r"\bnginx\b"],
        "Linux": [r"\blinux\b", r"\bubuntu\b"],
        "Terraform": [r"\bterraform\b"],
    }
}


def extract_technologies_for_review(text: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scans candidate-provided project description or README and produces
    structured technology suggestions with review metadata (confidence and detection reason).
    Prevents assuming raw dependencies equal genuine proficiency.
    """
    categorized_suggestions: Dict[str, List[Dict[str, Any]]] = {
        "programming_languages": [],
        "frameworks": [],
        "libraries": [],
        "databases": [],
        "apis": [],
        "ai_ml_techniques": [],
        "deployment_technologies": [],
    }

    text_lower = text.lower()

    for category, items in TECH_DICTIONARY.items():
        for tech_name, patterns in items.items():
            matches = 0
            for pattern in patterns:
                found = re.findall(pattern, text_lower)
                matches += len(found)

            if matches > 0:
                confidence = "high" if matches >= 2 else "medium"
                categorized_suggestions[category].append({
                    "name": tech_name,
                    "confidence": confidence,
                    "occurrences": matches,
                    "source": "readme_keyword_scan",
                    "status": "suggested_for_review"
                })

    return categorized_suggestions


def parse_project_readme(
    text: str,
    github_url: Optional[str] = None,
    candidate_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts structured project metadata, problem statement, architecture implementation,
    selectable outcome bullets with metrics, and suggested technologies for review.
    """
    clean_text = text.strip()
    lines = [line.strip() for line in clean_text.split("\n")]

    # 1. Project Title / Name
    extracted_name = candidate_name
    if not extracted_name:
        for line in lines:
            if line.startswith("# "):
                extracted_name = line.replace("# ", "").strip()
                break
            elif line.startswith("## ") and not extracted_name:
                extracted_name = line.replace("## ", "").strip()
                break
        if not extracted_name and lines:
            extracted_name = lines[0].strip("#* ")[:60]

    # 2. Problem Statement extraction
    problem = ""
    problem_match = re.search(
        r"(?:problem(?:\s+statement)?|motivation|why|background|challenge)[\s\S]*?(?=\n##|\n#|$)",
        clean_text,
        re.IGNORECASE
    )
    if problem_match:
        problem = problem_match.group(0).strip()
        # Strip header
        problem = re.sub(r"^(?:#+\s*)?(?:problem|motivation|why|background|challenge)[:\s]*", "", problem, flags=re.IGNORECASE).strip()

    # 3. Description extraction
    description = ""
    # Look for overview or first paragraph after main heading
    desc_match = re.search(r"(?:overview|about|introduction|description)[\s\S]*?(?=\n##|\n#|$)", clean_text, re.IGNORECASE)
    if desc_match:
        description = desc_match.group(0).strip()
        description = re.sub(r"^(?:#+\s*)?(?:overview|about|introduction|description)[:\s]*", "", description, flags=re.IGNORECASE).strip()
    elif len(lines) > 1:
        # Fallback to first non-heading paragraph
        para = []
        for line in lines[1:8]:
            if line.startswith("#"):
                break
            if line:
                para.append(line)
        description = " ".join(para)

    # 4. Implementation / Architecture
    implementation = ""
    impl_match = re.search(
        r"(?:architecture|implementation|how it works|technical design|system design)[\s\S]*?(?=\n##|\n#|$)",
        clean_text,
        re.IGNORECASE
    )
    if impl_match:
        implementation = impl_match.group(0).strip()
        implementation = re.sub(r"^(?:#+\s*)?(?:architecture|implementation|how it works|technical design|system design)[:\s]*", "", implementation, flags=re.IGNORECASE).strip()

    # 5. Extract bullets and metrics
    bullets = []
    # Identify markdown list items or bullet points
    bullet_lines = re.findall(r"(?:^|\n)\s*[-*•]\s+([^\n]+)", clean_text)
    metric_pattern = re.compile(r"(\b\d+(?:\.\d+)?(?:%|k|x|ms|s|h|gb|mb|\+)?\b|\breduced\b|\bincreased\b|\boptimized\b|\baccelerated\b)", re.IGNORECASE)

    for b in bullet_lines:
        b_clean = b.strip()
        if len(b_clean) > 15:
            # Check for metrics
            has_metric = metric_pattern.search(b_clean)
            detected_metric = has_metric.group(0) if has_metric else None
            bullets.append({
                "id": f"b_{uuid.uuid4().hex[:8]}",
                "text": b_clean,
                "is_selected": True,
                "metric": detected_metric
            })

    if not bullets and description:
        # Generate initial bullet from description
        sentences = [s.strip() for s in re.split(r"[.!?]", description) if len(s.strip()) > 15]
        for s in sentences[:3]:
            bullets.append({
                "id": f"b_{uuid.uuid4().hex[:8]}",
                "text": s,
                "is_selected": True,
                "metric": None
            })

    # 6. Extract categorized technology suggestions
    tech_suggestions = extract_technologies_for_review(clean_text)

    # Extract flat list of top technologies
    flat_techs = []
    for cat_list in tech_suggestions.values():
        for t in cat_list:
            flat_techs.append(t["name"])

    return {
        "name": extracted_name or "Untitled Project",
        "problem": problem or None,
        "description": description or None,
        "personal_contribution": None,
        "implementation": implementation or None,
        "github": github_url or None,
        "live_link": None,
        "supporting_evidence": None,
        "bullets": bullets,
        "suggested_technologies": tech_suggestions,
        "flat_technologies": sorted(list(set(flat_techs))),
        "technical_challenges": None,
        "verified_outcomes": [b["text"] for b in bullets if b.get("metric")]
    }
