# PDF Chatbot Evaluation

This folder contains a simple Chapter 6 evaluation workflow for the existing PDF chatbot. It uses the current FastAPI APIs and the three newest uploaded machine-readable PDFs. It does not add OCR, change backend behavior, or compare models.

## Files

- `evaluation_questions.csv`: 30 evaluation questions, 10 for each uploaded PDF.
- `run_evaluation.py`: logs in, lists notebooks/documents, asks the chatbot, scores results, and writes outputs.
- `evaluation_results.csv`: CSV header/template for per-question results.
- `evaluation_summary.json`: generated after a run.

## Configure `.env`

Add these variables to the repository root `.env` file:

```env
EVAL_API_BASE_URL=http://localhost:8000
EVAL_EMAIL=your-email@example.com
EVAL_PASSWORD=your-password
EVAL_NOTEBOOK_ID=
EVAL_OUTPUT_DIR=evaluation
EVAL_TOP_K=5
```

`EVAL_NOTEBOOK_ID` is optional. If omitted, the script lists the account notebooks and documents, then uses the three newest processed PDFs it can access. The script never hard-codes credentials, notebook IDs, or document IDs.

## Run

From the repository root:

```powershell
python evaluation\run_evaluation.py
```

The script writes:

- `evaluation/evaluation_results.csv`
- `evaluation/evaluation_summary.json`

If `EVAL_OUTPUT_DIR` is set to another folder, the files are written there instead.

## Metrics

Functional Pass Rate: a question passes when the chatbot API returns a non-empty answer, no request error occurs, the answer does not look like a failure fallback, and the answer contains at least one expected keyword.

Precision@1, Precision@3, Precision@5: for each question, the script checks whether the top retrieved sources contain an expected answer keyword or expected source hint. Precision@k is relevant sources in the top k divided by k.

Mean Reciprocal Rank: for each question, the script finds the first relevant retrieved source. Reciprocal rank is `1 / rank`, or `0` when no relevant source is found. MRR is the average over all questions.

Answer Grounding Score: rule-based score from 0 to 1. A score of `1.0` means the answer contains expected keywords and at least one retrieved source is relevant. `0.5` means only one of those checks passed. `0.0` means the answer is unsupported by the rule checks or no source was returned.

Average Response Time: measured around each `POST /api/chatbot/ask` request with Python's monotonic timer and averaged across all questions.

## API Shape Confirmed

- Login: `POST /api/auth/login` with JSON `{ "email": "...", "password": "..." }`, response includes `access_token`.
- Notebooks: `GET /api/notebooks/`.
- Documents: `GET /api/documents/` or `GET /api/documents/?notebook_id=...`.
- Chatbot: `POST /api/chatbot/ask` with `query`, `top_k`, `document_id`, `document_ids`, optional `notebook_id`, and `save_history`.
- Chatbot response fields inspected: `answer`, `sources`, `retrieval_latency_ms`, and `total_latency_ms`. The script scores `answer` and `sources`; response time is measured around the API call.

## Limitations

This is a lightweight bachelor-thesis evaluation, not a human annotation framework. Relevance and grounding use keyword and source-hint matching, so paraphrases may be under-scored. The `manual_review_note` column flags uncertain cases that should be checked manually. Results also depend on the current uploaded documents, existing chunking, current embedding index, Qdrant retrieval, and the configured LLM.
