import ollama

LLM_MODEL = "llama3.1"

SYSTEM_PROMPT = """You are a professional Arabic translator specializing in pediatric health and parenting content.

Your job is to translate English text into natural, fluent Modern Standard Arabic (MSA) that reads as native copy — not a literal translation.

Rules:
- Translate only. Do not add commentary, disclaimers, or extra information.
- Use terminology familiar to Arabic-speaking parents in the Gulf/MENA region.
- Medical terms should be translated accurately. When a medical term has no clean Arabic equivalent, use the English term transliterated in Arabic script.
- Output Arabic text only. No English. No explanation.
- Preserve the meaning and tone exactly — if the original is a warning, the translation must feel like a warning.
- If you are unsure of the best translation, pick one. Never output alternatives or use the word "or".
"""


def translate_to_arabic(english_text: str) -> str:
    """Translate a piece of English text to Arabic."""
    if not english_text or not english_text.strip():
        return ""

    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Translate the following to Arabic:\n\n{english_text}"},
        ],
        options={"temperature": 0.2},
    )

    return response["message"]["content"].strip()


def translate_verdict(verdict_dict: dict) -> dict:
    """
    Takes a SafetyVerdict as a dict, returns a parallel dict with
    Arabic translations for all human-facing string fields.
    Numeric and boolean fields are passed through unchanged.
    """
    arabic = {}

    # Fields to translate
    text_fields = ["reasoning"]
    list_fields = ["warnings"]

    for field in text_fields:
        if field in verdict_dict and verdict_dict[field]:
            arabic[field] = translate_to_arabic(verdict_dict[field])
        else:
            arabic[field] = verdict_dict.get(field, "")

    for field in list_fields:
        if field in verdict_dict and verdict_dict[field]:
            arabic[field] = [translate_to_arabic(item) for item in verdict_dict[field]]
        else:
            arabic[field] = []

    # Translate verdict label itself
    verdict_labels = {
        "safe": "آمن",
        "unsafe": "غير آمن",
        "consult_doctor": "استشر الطبيب",
        "insufficient_data": "بيانات غير كافية",
    }
    arabic["verdict"] = verdict_labels.get(verdict_dict.get("verdict", ""), verdict_dict.get("verdict", ""))

    # Pass through non-text fields unchanged
    arabic["confidence"] = verdict_dict.get("confidence")
    arabic["doctor_flag"] = verdict_dict.get("doctor_flag")
    arabic["product_name"] = verdict_dict.get("product_name", "")

    return arabic


if __name__ == "__main__":
    # Smoke test
    sample_verdict = {
        "verdict": "consult_doctor",
        "reasoning": "Product P003 contains avocado perseose, which may exacerbate eczema, and the doctor_consult_flags indicate a need to consult a doctor if the child has eczema or severe skin conditions.",
        "confidence": 0.8,
        "doctor_flag": True,
        "warnings": ["eczema exacerbation", "consult doctor"],
        "product_name": "Mustela Baby Hydra Bebe Body Lotion",
    }

    print("Translating verdict to Arabic...\n")
    arabic = translate_verdict(sample_verdict)

    import json
    print(json.dumps(arabic, ensure_ascii=False, indent=2))