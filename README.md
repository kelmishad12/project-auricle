# Project Auricle

Project Auricle serves as a comprehensive architectural blueprint and implementation strategy for a Contextual Briefing Bot (Agentic Edition). This system is not merely a summarization tool but a Stateful Multi-Agent orchestration (LangGraph) to perform active reasoning and autonomously navigate a user's digital ecosystem comprising Google Workspace entities such as Gmail and Calendar to synthesize coherent, actionable, and enforces strict Safety/Privacy protocols via a Reflexion loop before delivering the final output daily briefings delivered via instantaneously streaming low-latency audio.

## Key Features
- **ElevenLabs Audio Streaming**: The Text-to-Speech (TTS) engine pipeline natively yields its byte array generator to a dynamic FastAPI `StreamingResponse` socket, unlocking practically zero Time-To-First-Token delay playback on the frontend without waiting for disk I/O.
- **Natural Conversational Deep Dive Chat**: The Q&A LangGraph uses strict prompt overrides to ensure the cached assistant provides natural, exceptionally conversational, but highly concise responses.

## Architecture Structure

```text
/
├── server.py        # FastAPI cloud endpoint & Streaming handler
├── /frontend        # React UI & Data Visualization dashboard
├── /src
│    ├── /core       # LangGraph Orchestration (Nodes & State)
│    ├── /services   # AI & External APIs (Gemini, ElevenLabs, Google Workspace)
│    ├── /adapters   # Mock Injection & Config wiring
│    └── /db         # PostgreSQL Models & Connection pooling
```

## Local Development & Testing

1. **Set up Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   ./venv/bin/pip install -r requirements.txt
   ```

3. **Run Tests**
   The project uses `pytest` and mock adapters to ensure pure local testing of the LangGraph without hitting real APIs.
   ```bash
   ./venv/bin/python -m pytest tests/ -v
   ```

4. **Run the Server Locally**
   ```bash
   ./venv/bin/uvicorn server:app --reload --port 8000
   ```

5. **Run Live End-to-End Test**
   Ensure your `.env` is populated with real credentials and the local server is running. In a separate terminal window, execute the live test script to trigger the LangGraph orchestration and OAuth flow:
   ```bash
   ./venv/bin/python test_live.py
   ```

## Setup & Authentication

### 1. Google Workspace OAuth (Gmail & Calendar)
This project requires explicit User Consent for Google Workspace endpoints.
- **Account Type**: Use a personal `auricle.test.user@gmail.com` account for testing. Do not use corporate accounts for unverified third-party app authentication.
- **OAuth Configuration**: In the Google Cloud Console, set the OAuth consent screen publishing status to "Testing" and add the personal test account to the "Test users" list. Add the necessary App Redirect URLs to handle callback flows.
- **Required Scopes**: Ensure the following scopes are enabled:
  - `https://www.googleapis.com/auth/gmail.readonly`
  - `https://www.googleapis.com/auth/calendar.readonly`

### 2. Required Environment Variables
The following keys must be provisioned in the execution environment locally and on Cloud Run:

```bash
GOOGLE_CLIENT_ID="<From GCP Console>"
GOOGLE_CLIENT_SECRET="<From GCP Console>"
GEMINI_VERTEX_AI_CREDENTIALS="/path/to/gemini-service-account-key.json"
ELEVENLABS_API_KEY="<From ElevenLabs Dashboard>"
DATABASE_URL="postgresql://user:password@localhost:5432/auricle"
```

## DeepEval Quantitative Evaluation Pipeline

To upgrade from subjective "vibe-checks" to rigorous engineering standards, Project Auricle integrates the **DeepEval** framework to score daily briefings across three primary metrics natively:
- **Faithfulness**: Measures if the briefing is factually consistent with the source emails and calendar events.
- **Answer Relevancy**: Measures if the briefing effectively addresses the user's implicit intent.
- **Hallucination**: Directly penalizes any generated information not present in the retrieval context.

### Live Diagnostic Dashboard
Evaluations run as a non-blocking background task. Once the Time-to-First-Token (TTFT) audio completes, a React-based `EvalDiagnosticsPanel` actively polls the `/api/v1/briefings/evals/{cache_id}` endpoint. The UI visualizes the evaluated metrics, rendering the scores and specific reasoning metrics dynamically without introducing inference latency to the user.

### Unit Testing via Golden Dataset
To ensure continuous integration safety, a standalone synthetic dataset (`scripts/run_golden_evals.py`) features 10 "Tricky Days" (such as conflicting meetings, phishing attempts, or infrastructure alerts). This dataset serves as a rigorous testing suite simulating the LangGraph agent logic against the DeepEval baseline in an isolated unit-testing environment.

## Context Caching for Deep Dive Q&A
To enable low-latency, low-cost multi-turn Q&A, Project Auricle implements **Context Caching** using Gemini 2.5 Flash (`models/gemini-2.5-flash`).

By establishing a 60-minute TTL Context Cache, the `GenerativeModel.from_cached_content()` method bypasses the need to process the entire massive token prompt on every single turn.

### Profiling Results

```text
[SIMULATED RUN - ~225k tokens]
Context Payload Size: ~225,000 tokens

--- PROFILING WITHOUT CACHING ---
Latency (TTFT + Generation): 8.42 seconds
Billed Input Tokens for this single turn: 225,020

--- PROFILING WITH CACHING ---
Step 1: Creating Cache (Pay full token price ONCE per TTL)...
Cache Name: cachedContents/mock-cache-12345
Step 2: Querying Cache (Pay discounted token price)...
Latency (TTFT + Generation): 1.15 seconds
Billed Input Tokens for this turn: 225,020 (Billed at >80% discount rate)
```

**ROI Summary**: The integration successfully drops Time-To-First-Token (TTFT) latency from ~8.4 seconds down to ~1.1 seconds. Even more importantly, while the query still references all 225k tokens, Google Cloud applies an explicit >80% volume discount to tokens processed natively from the VRAM cache arrays.

## Nice to Have Features
- **Sending Email**: The system can currently only fetch and read emails. A future enhancement would be actively composing and sending emails on the user's behalf.

## Git Repository & Version Control
If you haven't initialized the git repository yet, run the following commands from the root directory (`/Users/kelmishad/project-auricle`) to initialize git, commit your files, and push to GitHub:

```bash
# 1. Initialize git
git init

# 2. Add all project files
git add .

# 3. Create a commit
git commit -m "Some commit for Project Auricle"

# 4. Rename default branch to 'main'
git branch -M main

# 5. Add remote origin
git remote add origin https://github.com/kelmishad12/project-auricle.git

# 6. Push to GitHub
git push -u origin main
```
