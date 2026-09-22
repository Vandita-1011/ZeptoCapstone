# Module 3 - Support Assistant

A small GenAI service that answers Zepto policy questions using retrieval-augmented
generation (RAG), running fully offline via a deterministic mock LLM mode.

## Files

| File | Purpose |
|---|---|
| `docs/doc_01.txt` ... `doc_08.txt` | The 8 policy documents (verbatim from the spec) |
| `ingest.py` | Embeds the 8 documents and stores them in ChromaDB |
| `test_retrieval.py` | A standalone sanity check for retrieval quality |
| `prompt_template.py` | The structured prompt template (used by the optional real-LLM path) |
| `schema.py` | Pydantic request/response models |
| `graph.py` | The LangGraph StateGraph: 3 nodes, conditional routing, MOCK_LLM branching |
| `main.py` | FastAPI app exposing `POST /ask` |
| `Dockerfile` | Builds and runs the FastAPI app locally |
| `requirements.txt` | Libraries needed for this module |
| `chroma_db/` | The persisted ChromaDB collection (embeddings for the 8 documents) |

## How to run

1. Install the libraries: `pip install -r requirements.txt`
2. Build the ChromaDB collection (only needed once, or after changing the docs):
       python ingest.py
3. Run the API locally:
       python -m uvicorn main:app --reload
4. It serves on `http://127.0.0.1:8000`. Test with a POST request to `/ask`, e.g.:
       curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" -d "{\"query\": \"How long does delivery take?\"}"

`MOCK_LLM` is left at its default (unset, meaning mock mode) for grading. No API key,
signup, or network access to any LLM provider is needed for this path.

## Architecture: ingestion -> embedding -> retrieval -> generation

**Ingestion:** `ingest.py` reads all 8 `.txt` files from `docs/`. Each file is short
enough to be treated as a single chunk, so chunking here is simply "one chunk per
document" (`doc_01` through `doc_08`).

**Embedding:** Each chunk is embedded locally using `sentence-transformers`' 
`all-MiniLM-L6-v2` model (`ingest.py`, and again at query time inside 
`retrieve_and_answer` in `graph.py`). No API key or network call is needed beyond
the model's one-time download.

**Storage:** The embeddings are stored in a persistent ChromaDB collection named
`zepto_policies` (`ingest.py`), backed by the files under `chroma_db/`.

**Retrieval:** The `retrieve_and_answer` node in `graph.py` embeds the incoming
query with the same MiniLM model, then queries ChromaDB for the top-3 most similar
chunks by cosine similarity. This step always runs for real, in both MOCK_LLM modes,
since it needs no API key.

**Generation:** The LangGraph graph (`graph.py`) has 3 nodes:
- `classify_intent`: in mock mode (the default, graded path), classifies the query
  using a keyword heuristic (checking for words like "delivery", "return", "refund",
  etc.) into `policy_question` or `general_question`. No LLM call is made.
- A conditional edge routes `policy_question` queries to `retrieve_and_answer`, and
  `general_question` queries to `direct_answer`.
- `retrieve_and_answer`: in mock mode, returns a canned templated answer built from
  the top retrieved chunk (`f"Based on the retrieved context: {top_chunk_snippet}"`),
  with no LLM call.
- `direct_answer`: in mock mode, returns a fixed canned string with no retrieval and
  no LLM call.

The final response is validated against the Pydantic `AskResponse` schema
(`schema.py`): `answer` (string), `sources` (the retrieved chunk IDs, empty for
general questions), and `confidence` (a fixed 1.0 in mock mode, since there is no
LLM output to be uncertain about).

**What MOCK_LLM changes:** `MOCK_LLM` is checked at the top of `graph.py`
(`MOCK_LLM = os.environ.get("MOCK_LLM", "1") == "1"`). Left unset or set to `1`
(the default, graded path), every generation step in every node uses the
deterministic mock logic described above — no API key, signup, or LLM network call
is ever made. If `MOCK_LLM=0` is explicitly set, the same 3 nodes would instead
call a real LLM (using the structured prompt template in `prompt_template.py`,
which follows a role-context-task-format-length skeleton with a negative
constraint and a few-shot example) to classify intent, generate a grounded answer,
or answer directly. This optional path is not required for full marks and is not
what is graded.

## Example API calls (MOCK_LLM left at default)

**Call 1 - routes to `retrieve_and_answer` (policy_question):**

Request: `{"query": "How long does delivery take?"}`

Response:
```json
{
  "answer": "Based on the retrieved context: Zepto delivers grocery and household essentials to serviceable pin codes within 10 to 30 minutes of order confirmation, depending on the customer's delivery zone and current order volume. Standard del",
  "sources": ["doc_01", "doc_02", "doc_04"],
  "confidence": 1.0
}
```

**Call 2 - routes to `direct_answer` (general_question):**

Request: `{"query": "What is the capital of France?"}`

Response:
```json
{
  "answer": "I can only answer questions about Zepto policies right now.",
  "sources": [],
  "confidence": 1.0
}
```

## Docker

The Dockerfile builds the FastAPI app and serves it on port 7860:

docker build -t zepto-support-assistant .
docker run -p 7860:7860 zepto-support-assistant

This was built and run locally, and the `/ask` endpoint was confirmed working
inside the container with the same request/response shown above. No push to a
remote registry or cloud deployment was done — that is an optional, ungraded step
per the spec.