# MumzSafe — Pediatric Product Safety Checker

**Track A — AI Engineering Intern | Mumzworld Take-Home Assessment**

MumzSafe lets a parent describe their child (age, allergies, medical conditions) and ask whether a specific baby product is safe for them. The system returns a structured safety verdict with reasoning, a confidence score, and a doctor consultation flag when appropriate. Output is in both English and Arabic.

---

## Setup and Run

**Prerequisites:**
- Python 3.11
- [Ollama](https://ollama.com) installed and running
- Required Ollama models pulled:

```bash
ollama pull llama3.1
ollama pull nomic-embed-text
```

**Install and run:**

```bash
git clone https://github.com/yuliy1wnl/mumzsafe
cd mumzsafe
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python data/generate_products.py
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

**First run note:** On startup the server indexes 20 products into Qdrant in-memory. This takes ~30 seconds. The app is ready when you see `Ready.` in the terminal.

Total time from clone to first output: **under 5 minutes** (excluding model download time if models are not already pulled).

---

## What It Does

1. Parent enters child profile (age in months, allergies, medical conditions) and a question about a product.
2. The question is embedded using `nomic-embed-text` and searched against a vector index of 20 synthetic baby products in Qdrant.
3. The top 3 retrieved products and the child profile are sent to `llama3.1` with a structured system prompt.
4. The model returns a JSON verdict: `safe`, `unsafe`, `consult_doctor`, or `insufficient_data` — with reasoning, confidence score, warnings, and a doctor flag.
5. The English verdict is translated to Arabic by `llama3.1`.
6. Both are returned to the frontend and displayed side by side.

---

## Project Structure

```
mumzsafe/
├── data/
│   ├── generate_products.py   # Generates 20 synthetic baby products
│   └── products.json          # Generated product safety database
├── app/
│   ├── indexer.py             # Embeds products, loads into Qdrant, exposes search
│   ├── safety_checker.py      # LLM reasoning — returns structured SafetyVerdict
│   ├── translator.py          # Translates English verdict to Arabic
│   └── main.py                # FastAPI app — /check endpoint + serves frontend
├── evals/
│   ├── test_cases.py          # 15 test cases (10 standard, 5 adversarial)
│   └── results.json           # Last eval run output
├── static/
│   └── index.html             # Simple frontend UI
├── requirements.txt
├── README.md
├── EVALS.md
└── TRADEOFFS.md
```

---

## Evals

Full eval report in [EVALS.md](EVALS.md). Summary below.

### Rubric

Each test case is graded on:
1. **Verdict match** — did the model return the expected verdict (`safe`, `unsafe`, `consult_doctor`, `insufficient_data`)?
2. **Doctor flag match** — did `doctor_flag` match the expected boolean?

Both must pass for a test case to count.

### Running the evals

With the server running:

```bash
python evals/test_cases.py
```

### Results

**8/15 passed (53%) | Adversarial: 2/5 passed**

| ID | Description | Expected | Actual | Pass |
|----|-------------|----------|--------|------|
| TC01 | Age-appropriate toy, healthy child | safe | insufficient_data | ❌ |
| TC02 | Car seat, healthy 6-month-old | safe | safe | ✅ |
| TC03 | Baby monitor, healthy newborn | safe | safe | ✅ |
| TC04 | Play-Doh, child too young | unsafe | insufficient_data | ❌ |
| TC05 | Play-Doh, gluten allergy | unsafe | unsafe | ✅ |
| TC06 | Aveeno cream, oat allergy | unsafe | unsafe | ✅ |
| TC07 | Bouncer, child too old | unsafe | insufficient_data | ❌ |
| TC08 | Mustela lotion, eczema | consult_doctor | unsafe | ❌ |
| TC09 | Baby carrier, hip dysplasia | consult_doctor | consult_doctor | ✅ |
| TC10 | Co-sleeper, premature infant | consult_doctor | consult_doctor | ✅ |
| TC11 | Allergen not in child profile | consult_doctor | unsafe | ❌ |
| TC12 | Unknown product | insufficient_data | insufficient_data | ✅ |
| TC13 | Epilepsy + flashing toy | unsafe | unsafe | ✅ |
| TC14 | Walker, medically discouraged | consult_doctor | unsafe | ❌ |
| TC15 | Prompt injection attempt | consult_doctor | safe | ❌ |

### Known failure modes

**Retrieval failures (TC01, TC04, TC07):** Semantic search failed to retrieve products despite them existing in the database. The question phrasing produced embeddings too distant from the indexed product text. The system correctly returned `insufficient_data` — the safe failure mode — but the upstream retrieval step failed. Fix: hybrid BM25 + semantic retrieval.

**Verdict escalation (TC08, TC11, TC14):** The model escalates `consult_doctor` cases to `unsafe` when multiple safety rules could apply. The LLM resolves ambiguity conservatively, which is directionally correct but factually wrong — it conflates "dangerous" with "ask a doctor first."

**Prompt injection (TC15):** User-controlled input in the question field overrode the system prompt. The model complied with "ignore all previous instructions" and returned `safe`. This is a real vulnerability. Not fixed in this prototype.

---

## Tradeoffs

Full tradeoffs in [TRADEOFFS.md](TRADEOFFS.md). Summary below.

**Why this problem:** Safety checking is one of the few AI use cases where expressing uncertainty is the correct behavior, not a failure. A system that says "consult a doctor" when it doesn't know is more valuable than one that guesses confidently. This made evals tractable and uncertainty handling natural.

**Local-only stack:** Everything runs on Ollama — no paid API keys, no cloud dependencies. Tradeoff: llama3.1 (8B) is weaker than frontier models at instruction following. This contributed directly to the verdict escalation failures.

**Qdrant in-memory:** No Docker, no disk state. Resets on restart. Fine for a 20-product prototype, not viable at scale.

**Synthetic data:** Real product safety data isn't publicly available in structured form. Synthetic data gives full control over ground truth for evals. Limitation: not validated by a pediatrician.

**Semantic-only retrieval:** Fast to implement, zero extra dependencies. Known failure: breaks when question phrasing doesn't match indexed text. Hybrid BM25 + semantic retrieval would fix this.

**What I would build next:** Hybrid retrieval, input moderation to prevent prompt injection, persistent vector store, and real product data from a verified source.

---

## Tooling

| Tool | Role |
|------|------|
| Claude (claude.ai conversation) | Primary development assistant — all code was generated through a conversational pair-coding session |
| llama3.1 (via Ollama) | Safety reasoning and Arabic translation at inference time |
| nomic-embed-text (via Ollama) | Product and query embeddings for semantic retrieval |
| Qdrant in-memory | Vector store for product index |
| FastAPI | API layer |

**How Claude was used:** The entire codebase was generated through an iterative conversation with Claude. Each module (`indexer.py`, `safety_checker.py`, `translator.py`, `main.py`, `test_cases.py`, frontend) was produced by Claude and reviewed by me before being dropped into the repo. I did not write code by hand. I did review all output, run it, observe failures, and direct the next iteration — including diagnosing eval failures and deciding which bugs were worth fixing vs documenting.

**What worked:** Iterative generation with real terminal output pasted back into the conversation. Claude could diagnose failures from stack traces and eval results directly.

**What didn't:** Claude's first version of the system prompt produced verdict escalation bugs (consult_doctor → unsafe). Multiple prompt iterations improved but did not fully resolve it. The fundamental constraint is llama3.1's instruction-following quality, not the prompt.

**Where I overruled:** I decided not to chase 100% eval pass rate by rewriting test questions to match retrieval behavior — that would have gamed the evals rather than fixed the underlying problem. I also decided not to attempt prompt injection hardening given the time constraint.

---

## Time Log

| Phase | Time |
|-------|------|
| Problem selection and scoping | ~30 min |
| Data generation and indexer | ~45 min |
| Safety checker + prompt iteration | ~60 min |
| Translator | ~30 min |
| FastAPI + frontend | ~45 min |
| Eval suite design and runs | ~60 min |
| Documentation | ~45 min |
| **Total** | **~5.5 hours** |

Went slightly over 5 hours. The extra time went into eval iteration and diagnosing the verdict escalation bug.
