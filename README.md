# SentinelMind – Complete Hackathon MVP

A beginner-friendly SOC alert triage prototype. It combines a FastAPI backend, Groq LLM analysis, Hindsight memory (when configured), an HTML/CSS/JavaScript dashboard, and synthetic alert data.

## What is included
- 30 historical analyst-reviewed alerts in `data/history.json`
- 25 live/demo alerts in `data/live_alerts.json`
- Alert feed, triage recommendation, evidence panel and analyst feedback buttons
- `retain`, `recall`, and `reflect` memory operations in `backend/memory.py`
- Groq integration with a cautious rule-based fallback
- Metrics and learning curve chart
- Local JSON memory fallback so the dashboard can be tried before connecting Hindsight

## Windows setup
1. Install Python 3.11 or newer, VS Code, and Git.
2. Extract this ZIP to a folder such as `C:\SentinelMind_Complete_Project`.
3. Open that folder in VS Code.
4. Open Terminal → New Terminal (PowerShell).
5. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again.

6. Install packages:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

7. Copy `.env.example` to `.env`. Add your own `GROQ_API_KEY` and Hindsight settings. Never share `.env` or commit it to Git.

8. Run the app from the project root:

   ```powershell
   python -m uvicorn backend.main:app --reload
   ```

9. Open `http://127.0.0.1:8000`. API documentation: `http://127.0.0.1:8000/docs`.

## Connect Groq
Create an API key in the Groq console and put it in `.env`:
`GROQ_API_KEY=your_key_here`
The default model is `openai/gpt-oss-120b`. You can change `GROQ_MODEL` if needed. Without a key, rule-based fallback triage still works.

## Connect Hindsight
This project uses the official Python package `hindsight-client` and the SDK pattern `Hindsight(base_url=..., api_key=...)`, plus `create_bank`, `retain`, `recall`, and `reflect`.

- Start a Hindsight service or use your Hindsight Cloud deployment.
- Set `HINDSIGHT_BASE_URL` to that service's API URL.
- If your deployment requires an API key, set `HINDSIGHT_API_KEY`.
- Keep `HINDSIGHT_BANK_ID=sentinelmind-demo` for the demo organization.
- Restart FastAPI after changing `.env`.

If Hindsight is not configured or unavailable, the app transparently uses `backend/local_memory.json` as a basic local fallback. The fallback uses keyword overlap, not Hindsight semantic recall. For judging the Hindsight requirement, configure and demonstrate the real Hindsight service.

## Demo flow
1. Select an alert in Live alert feed.
2. Review the recommendation, severity, host, user, IP and recalled memories.
3. Enter why you chose a verdict.
4. Click Likely benign / Needs review / Escalate.
5. The verdict is retained in Hindsight (or local fallback).
6. Open Learned patterns and show the summary.
7. Compare routine backup alerts from `10.20.1.15` with lookalike alerts from a new external IP `203.0.113.77`. The changed source is deliberately included to demonstrate why memory must not be trusted blindly.

## API routes
- `GET /api/health`
- `GET /api/alerts`
- `POST /api/alerts`
- `POST /api/verdict`
- `GET /api/metrics`
- `GET /api/patterns`
- `POST /api/demo/reset`

## Team of three
- Member 1: Hindsight setup, `backend/memory.py`, and verdict retention.
- Member 2: Groq integration, triage logic, synthetic data, and testing.
- Member 3: dashboard, CSS, chart, and demo presentation.

## Important limitations
- This is an educational hackathon prototype, not a production SOC tool.
- Synthetic data is not real incident evidence.
- The confidence score is a heuristic, not a statistically calibrated probability.
- An AI recommendation must never automatically close or suppress a real security alert.
- The shipped history file is provided as a seed dataset; this MVP does not automatically import it into Hindsight. For the judging demo, add historical records to Hindsight using the import helper below or retain them through the UI feedback workflow.

## Optional: import historical analyst examples into Hindsight
After Hindsight is configured and the server is running, run:

```powershell
python -m backend.seed
```
