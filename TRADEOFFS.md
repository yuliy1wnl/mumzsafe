# TRADEOFFS.md — MumzSafe Design Decisions

## Problem Selection

### Why a Safety Checker, not a Gift Finder or Recommendation Engine

Mumzworld's example problems lean toward personalization and discovery. I chose pediatric product safety because:

1. **Uncertainty handling is the core feature, not a bolt-on.** A gift finder that says "I don't know" has failed. A safety checker that says "consult a doctor" has succeeded. This inverts the typical LLM failure mode — the system is rewarded for admitting uncertainty, not penalized.

2. **Structured output with ground truth.** Safety verdicts are discrete and verifiable: safe, unsafe, consult_doctor, insufficient_data. This makes evals tractable. Recommendation quality is subjective and hard to eval rigorously.

3. **Maps directly to Mumzworld's user base.** Parents buying baby products on Mumzworld have genuine safety questions. A product that answers "is this lotion safe for my baby with eczema?" is immediately useful to their core audience.

4. **Non-trivial AI engineering.** The problem requires RAG (retrieval), structured output (Pydantic schema enforcement), multilingual output (Arabic translation), and uncertainty quantification (confidence scores + doctor flags). It hits every dimension of the grading rubric.

---

## Architecture Decisions

### Local-only stack (Ollama + Qdrant in-memory)

**Decision:** Run everything locally. No paid API keys, no cloud dependencies.

**Why:** Zero setup friction for the evaluator. Clone, install, run — no account creation, no API key management, no rate limits. The tradeoff is model quality: llama3.1 (8B) is materially weaker than GPT-4 or Claude at instruction following and structured output. This contributed directly to the verdict escalation failures documented in EVALS.md.

**What was cut:** OpenAI or Anthropic APIs would have produced more reliable structured output and better rule adherence. Rejected to keep the prototype self-contained.

---

### Qdrant in-memory (not persistent)

**Decision:** Use Qdrant's in-memory mode. The vector index resets on every server restart.

**Why:** No Docker required, no disk state to manage, simple setup. For a 20-product prototype this is acceptable — indexing takes ~30 seconds on startup.

**What was cut:** Persistent Qdrant (Docker) or a hosted vector DB would be necessary for production. At scale, re-indexing on every boot is not viable.

---

### Synthetic product data

**Decision:** Generate 20 synthetic baby products with structured safety metadata rather than scraping real product data.

**Why:** Real product safety data is not publicly available in structured form. Scraping Mumzworld or third-party databases would introduce legal and data quality risks. Synthetic data lets us control the ground truth precisely, which is essential for eval design.

**Limitation:** The synthetic products are plausible but not authoritative. The safety metadata (allergen warnings, contraindications) was designed to be realistic but has not been validated by a pediatrician or regulatory body. This system should not be used for real medical decisions.

---

### Single LLM for both reasoning and translation

**Decision:** Use llama3.1 for both safety reasoning and Arabic translation.

**Why:** Simplicity. One model already downloaded, one dependency, no token routing logic.

**Tradeoff:** A dedicated translation model (e.g. Helsinki-NLP/opus-mt) would produce more consistent Arabic output. llama3.1's Arabic translation showed one known failure: outputting multiple translation alternatives separated by "or" for ambiguous medical terms. Mitigated with a system prompt fix but not fully resolved.

---

### Semantic-only retrieval

**Decision:** Use cosine similarity on nomic-embed-text embeddings for product retrieval. No keyword search.

**Why:** Fast to implement, zero additional dependencies, works well for descriptive queries.

**Known failure:** Retrieval fails when the question phrasing doesn't produce embeddings close to the indexed product text. In evals, LEGO DUPLO, Hasbro Play-Doh, and Fisher-Price Bouncer were not retrieved despite existing in the database. This caused 3 test failures (TC01, TC04, TC07).

**What was cut:** Hybrid retrieval (BM25 + semantic) is the standard fix for this. The `rank_bm25` library would add keyword matching as a second retrieval pass, with results merged by Reciprocal Rank Fusion. Estimated 2-3 hours of additional work. Cut due to time constraints.

---

### Product name not translated to Arabic

**Decision:** Pass `product_name` through to the Arabic output unchanged (English brand name).

**Why:** Arabic-speaking parents in the Gulf/MENA region recognize "Mustela" and "Aveeno" as English brand names. Transliterating them to Arabic script ("مستلا") reduces recognizability without adding value. Brand names are not translated in professional Arabic marketing copy either.

---

## What Was Cut

| Feature | Reason cut |
|---------|------------|
| Hybrid BM25 + semantic retrieval | Time. Would fix 3 eval failures. |
| Prompt injection hardening | Time. Would require input moderation layer. |
| Persistent vector store | Unnecessary for prototype scope. |
| Real product data | Legal/data quality risk. |
| Fine-tuned model | Out of scope for intern prototype. |
| Streaming API responses | Nice UX but not core to the eval story. |
| User session state | Single-turn queries sufficient for demo. |

---

## What Would Change in Production

1. **Model:** Replace llama3.1 with a frontier model (GPT-4o, Claude 3.5 Sonnet) for better instruction adherence and structured output reliability.
2. **Retrieval:** Hybrid BM25 + semantic search with Reciprocal Rank Fusion.
3. **Data:** Partner with a pediatric database or regulatory body for verified product safety data.
4. **Input moderation:** Sanitize user input before passing to LLM to prevent prompt injection.
5. **Medical disclaimer:** Every response should carry a clear disclaimer that this is not a substitute for professional medical advice.
6. **Persistent storage:** Qdrant Docker or a hosted vector DB with incremental indexing.
7. **Evaluation:** Replace LLM-as-judge with pediatrician-reviewed ground truth labels.
