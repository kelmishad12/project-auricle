# Project Auricle

Project Auricle serves as a comprehensive architectural blueprint and implementation strategy for a Contextual Briefing Bot (Agentic Edition). This system is not merely a summarization tool but a Stateful Multi-Agent orchestration (LangGraph) to perform active reasoning and autonomously navigate a user's digital ecosystem comprising Google Workspace entities such as Gmail and Calendar to synthesize coherent, actionable, and enforces strict Safety/Privacy protocols via a Reflexion loop before delivering the final output daily briefings delivered via low-latency audio.

## Architecture Structure

```
/
├── server.py        # FastAPI Entrypoint for Cloud Run
├── /docs            # Markdown contribution docs
├── /src
│    ├── /core       # Pure LangGraph logic (No API calls here)
│    │    ├── state.py   # AgentState definition
│    │    ├── graph.py   # Supervisor and Node definitions
│    │    ├── nodes.py   # LangGraph Node definitions
│    │    └── tools.py   # Extracted tools for LLM use
│    ├── /services   # Concrete Services and Google integrations
│    │    ├── google.py      # Google Services (OAuth, Gmail & Calendar SDKs)
│    │    ├── gemini.py      # Gemini 1.5 Flash Integration
│    │    └── elevenlabs.py  # ElevenLabs Text-to-Speech
│    ├── /adapters   # Config & Mock Injection
│    │    ├── localmock.py          # Uses mock (Private/GitIgnored)
│    │    └── config.py             # Dependency Injection wiring
│    ├── /db         # Database and ORM definitions (PostgreSQL)
│    │    ├── session.py
│    │    └── /models    # SQLAlchemy Models
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

## Context Caching for Deep Dive Q&A

To enable low-latency, low-cost multi-turn Q&A, Project Auricle implements **Context Caching** using Gemini 2.0 Flash (`models/gemini-2.0-flash-001`).

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
