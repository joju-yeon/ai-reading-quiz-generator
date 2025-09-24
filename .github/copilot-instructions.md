# Copilot Instructions for AI 독서 문제 생성기

## Project Overview
This project is a Streamlit web application for generating reading comprehension questions from uploaded book files (PDF, Word, TXT). It integrates with an n8n workflow backend for file processing and question generation.

## Architecture & Data Flow
- **Frontend:** `app.py` (Streamlit)
  - Handles UI, file upload, user input, and displays generated questions.
  - Communicates with n8n backend via REST API endpoints (see `N8N_BASE_URL`).
- **Backend:** n8n workflow (external, not in repo)
  - Receives uploaded files and metadata.
  - Processes files and generates questions, returning results via polling.

## Key Patterns & Conventions
- All API calls use the `requests` library and expect JSON responses.
- Session state (`st.session_state`) is used for UI state, uploaded books, and generated questions.
- Book metadata includes both Korean and English titles (`bookTitleKr`, `bookTitleEn`).
- Polling for job results uses a loop with timeout (`POLL_INTERVAL_SEC`, `POLL_MAX_WAIT_SEC`).
- Download options for generated questions: Excel (via `openpyxl`) and CSV.
- UI is organized into three tabs: Upload, Generate Questions, View/Download Results.

## Developer Workflows
- **Run app:**
  ```powershell
  streamlit run app.py
  ```
- **Dependencies:**
  - All requirements are listed in `requirements.txt`.
  - Install with:
    ```powershell
    pip install -r requirements.txt
    ```
- **Secrets:**
  - API base URL is set via Streamlit secrets (`.streamlit/secrets.toml`).

## Integration Points
- n8n endpoints:
  - `/books` (GET): List uploaded books
  - `/book-upload` (POST): Upload book file
  - `/generate-questions` (POST): Start question generation
  - `/job-result` (GET): Poll for results

## Examples & Patterns
- Use `st.session_state` for persistent UI state:
  ```python
  if key not in st.session_state:
      st.session_state[key] = default
  ```
- Polling for async job results:
  ```python
  while True:
      r = requests.get(...)
      if r.status_code == 200 and r.json().get('status') == 'done':
          break
      time.sleep(POLL_INTERVAL_SEC)
  ```

## References
- Main file: `app.py`
- Requirements: `requirements.txt`
- User guide: `README.md`

---
If any conventions or workflows are unclear, please ask for clarification or provide feedback to improve these instructions.
