from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from app.indexer import index_products, search_products
from app.safety_checker import ChildProfile, check_safety
from app.translator import translate_verdict


# --- Startup: index products once on boot ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Indexing products...")
    index_products()
    print("Ready.")
    yield

app = FastAPI(title="MumzSafe", lifespan=lifespan)


# --- Request / Response schemas ---

class CheckRequest(BaseModel):
    age_months: int
    allergies: list[str] = []
    medical_conditions: list[str] = []
    question: str


class CheckResponse(BaseModel):
    english: dict
    arabic: dict


# --- API endpoints ---

@app.post("/check", response_model=CheckResponse)
def check(req: CheckRequest):
    if req.age_months < 0 or req.age_months > 216:  # 0–18 years
        raise HTTPException(status_code=400, detail="age_months must be between 0 and 216.")
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty.")

    child = ChildProfile(
        age_months=req.age_months,
        allergies=req.allergies,
        medical_conditions=req.medical_conditions,
    )

    products = search_products(req.question, top_k=3)
    verdict = check_safety(child, products, req.question)
    verdict_dict = verdict.model_dump()

    arabic = translate_verdict(verdict_dict)

    return CheckResponse(english=verdict_dict, arabic=arabic)


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Serve frontend ---

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")