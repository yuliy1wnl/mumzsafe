import json
import ollama
from pydantic import BaseModel
from typing import Literal

LLM_MODEL = "llama3.1"


class ChildProfile(BaseModel):
    age_months: int
    allergies: list[str] = []
    medical_conditions: list[str] = []


class SafetyVerdict(BaseModel):
    verdict: Literal["safe", "unsafe", "consult_doctor", "insufficient_data"]
    reasoning: str
    confidence: float  # 0.0 - 1.0
    doctor_flag: bool
    warnings: list[str] = []
    product_name: str


SYSTEM_PROMPT = """You are a pediatric product safety assistant. Your job is to assess whether a baby/child product is safe for a specific child profile.

You will be given:
1. A child profile (age in months, allergies, medical conditions)
2. Retrieved product data from a safety database
3. The parent's question

You MUST respond with a single valid JSON object — nothing else. No explanation outside the JSON.

Rules:
- Be conservative. When in doubt, flag for doctor consult.
- If the product data does not contain enough information to answer, verdict = "insufficient_data"
- If child's age_months is less than the product's min_months OR greater than the product's max_months, verdict = "unsafe". Otherwise the child is within the age range and age is NOT a disqualifying factor.
- If any allergen in the child profile matches product allergen_warnings, verdict = "unsafe"
- If any medical condition matches doctor_consult_flags or contraindications, verdict = "consult_doctor"
- confidence must reflect your actual certainty (0.0 to 1.0). Do not always output 0.9.
- doctor_flag = true if verdict is "consult_doctor" or "insufficient_data"
- warnings is a list of specific issues found. Empty list if none.
- reasoning must be grounded in the product data provided. Do not invent facts.

JSON schema:
{
  "verdict": "safe" | "unsafe" | "consult_doctor" | "insufficient_data",
  "reasoning": "<string>",
  "confidence": <float 0.0-1.0>,
  "doctor_flag": <boolean>,
  "warnings": ["<string>", ...],
  "product_name": "<string>"
}"""


def build_user_prompt(child: ChildProfile, products: list[dict], question: str) -> str:
    child_str = (
        f"Child age: {child.age_months} months\n"
        f"Allergies: {', '.join(child.allergies) if child.allergies else 'None reported'}\n"
        f"Medical conditions: {', '.join(child.medical_conditions) if child.medical_conditions else 'None reported'}"
    )

    products_str = json.dumps(products, indent=2)

    return (
        f"CHILD PROFILE:\n{child_str}\n\n"
        f"RETRIEVED PRODUCT DATA:\n{products_str}\n\n"
        f"PARENT QUESTION:\n{question}\n\n"
        f"Respond with JSON only."
    )


def check_safety(child: ChildProfile, products: list[dict], question: str) -> SafetyVerdict:
    if not products:
        return SafetyVerdict(
            verdict="insufficient_data",
            reasoning="No matching products found in the safety database.",
            confidence=0.0,
            doctor_flag=True,
            warnings=["Product not found in database. Consult a doctor or pharmacist."],
            product_name="Unknown",
        )

    prompt = build_user_prompt(child, products, question)

    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0.1},  # Low temp — we want determinism not creativity
    )

    raw = response["message"]["content"].strip()

    # Strip markdown fences if model wraps JSON anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
        return SafetyVerdict(**data)
    except (json.JSONDecodeError, Exception) as e:
        # Model failed to return valid JSON — fail safe
        return SafetyVerdict(
            verdict="insufficient_data",
            reasoning=f"Safety check could not be completed due to a system error. Raw model output: {raw[:200]}",
            confidence=0.0,
            doctor_flag=True,
            warnings=["System error during safety check. Please consult a healthcare professional."],
            product_name=products[0].get("product_name", "Unknown") if products else "Unknown",
        )


if __name__ == "__main__":
    # Smoke test — requires indexer to be running
    from indexer import index_products, search_products

    index_products()

    child = ChildProfile(
        age_months=6,
        allergies=["fragrance"],
        medical_conditions=["eczema"],
    )
    question = "Is this lotion safe for my baby with eczema?"
    products = search_products("baby lotion eczema sensitive skin")

    verdict = check_safety(child, products, question)
    print(verdict.model_dump_json(indent=2))