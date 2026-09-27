# 🤖 Bob Change Impact Mode — IBM BOB 2.0

> Analyse the impact of a code change **before** it is made.  
> Powered by **IBM watsonx.ai** (Granite 4), orchestrated with **LangGraph**, and served via **FastAPI + Uvicorn**.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Agents](#agents)
- [Pipeline Flow](#pipeline-flow)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup (Virtual Environment)](#setup-virtual-environment)
- [Configuration](#configuration)
- [Running the Program](#running-the-program)
  - [Mode 1 — Web UI (Uvicorn / FastAPI)](#mode-1--web-ui-uvicorn--fastapi-recommended)
  - [Mode 2 — CLI (terminal)](#mode-2--cli-terminal)
- [API Endpoints](#api-endpoints)
- [State Schema](#state-schema)
- [Troubleshooting](#troubleshooting)

---

## Overview

Bob Change Impact Mode solves a common developer problem: **you want to change a piece of code but you do not know what else will break**.

Instead of exploring the codebase manually, you describe your intended change in plain English. Bob then:

1. Scans the repository and identifies every affected file, database table, and test.
2. Assesses overall risk (`HIGH / MEDIUM / LOW`).
3. Generates a numbered implementation plan.
4. Waits for your approval before doing anything.
5. Simulates execution, runs tests, and produces a structured final report.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Web Mode (api.py + index.html)             │
│  uvicorn api:app --reload --port 8000       │
└──────────────────────┬──────────────────────┘
                       │  POST /run  →  SSE /stream/{run_id}
┌─────────────────────────────────────────────┐
│  CLI Mode (main.py)                         │
│  python main.py                             │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
          LangGraph StateGraph (agents/orchestrator/graph.py)
                 │
                 ├── [Parallel] dependency_agent   ← agents/dependency/agent.py
                 ├── [Parallel] database_agent     ← agents/database/agent.py
                 ├── [Parallel] test_agent         ← agents/test_agent/agent.py
                 │
                 ├── impact_report_node            (IBM Granite via watsonx.ai)
                 ├── implementation_plan_node      (IBM Granite via watsonx.ai)
                 ├── human_approval_node           (Web: POST /approve | CLI: y/n gate)
                 │
                 ├── [Conditional] bob_execution_node
                 ├── test_runner_node
                 │    └── [Retry router] → bob_execution_node (max 1 retry)
                 │
                 └── final_report_node             (IBM Granite via watsonx.ai)

Shared IBM watsonx.ai client → agents/bob_client.py
Shared LangGraph state       → agents/state.py
```

All three analysis agents run **concurrently** using `ThreadPoolExecutor(max_workers=3)`.



---

## Agents

### 1. Dependency Agent (`agents/dependency/agent.py`)

| Item | Detail |
|---|---|
| **Input** | `change_description`, `repo_path` |
| **Output** | `affected_files: list[str]` |
| **What it does** | Walks the repository, reads every `.js / .ts / .jsx / .tsx` file (capped at 500 chars each, skipping `node_modules`, `.git`, `dist`, `build`), then asks the model to identify which files are directly or indirectly affected by the change. |

### 2. Database Agent (`agents/database/agent.py`)

| Item | Detail |
|---|---|
| **Input** | `change_description`, `repo_path`, `affected_files` |
| **Output** | `database_impact: list[{ table: str, risk: HIGH\|MEDIUM\|LOW }]` |
| **What it does** | Reads the affected source files, then searches the repo for schema/migration/model files (`.sql`, filenames containing `schema / migration / model / database / seed`, or files inside a `models/` directory). Passes all of this to the model to identify impacted DB tables and assign a risk level. |

### 3. Test Agent (`agents/test_agent/agent.py`)

| Item | Detail |
|---|---|
| **Input** | `change_description`, `repo_path`, `affected_files` |
| **Output** | `tests_to_run: list[str]` |
| **What it does** | Discovers all `*.test.js / *.spec.js` (and `.ts / .jsx / .tsx` variants) under `<repo_path>/tests/`. Reads a 400-char snippet of each test, then asks the model which tests are relevant to the change and the affected files. |

---

## Pipeline Flow

```
START
  │
  ▼
[Parallel] Dependency + Database + Test Agents
  │
  ▼
Impact Report  →  risk_level + impact_summary (markdown)
  │
  ▼
Implementation Plan  →  numbered step-by-step plan (markdown)
  │
  ▼
Human Approval Gate  →  y / n
  │
  ├─ rejected ──────────────────────────────────► Final Report
  │
  ▼ approved
Bob Execution  →  simulates file edits (code_modified = True)
  │
  ▼
Test Runner  →  per-test pass/fail + summary counts
  │
  ├─ all pass ──────────────────────────────────► Final Report
  │
  ├─ some fail + retry_count < 1 ──────────────► Bob Execution (retry)
  │
  └─ some fail + retry_count ≥ 1 ──────────────► Final Report
        │
        ▼
      END
```

---

## Project Structure

```
IBM_BOB_2.0/
├── api.py                         # FastAPI app — web entry point (uvicorn)
├── main.py                        # CLI entry point — interactive terminal loop
├── index.html                     # Single-page frontend served by api.py at GET /
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variable template
├── .env                           # Your local credentials (git-ignored)
├── .gitignore
├── CONCEPTION.md                  # Project design document
│
└── agents/
    ├── __init__.py
    ├── bob_client.py              # Shared watsonx.ai client factory
    ├── state.py                   # LangGraph AgentState TypedDict
    │
    ├── orchestrator/
    │   └── graph.py               # Full LangGraph pipeline (7 nodes + 2 routers)
    │
    ├── dependency/
    │   └── agent.py               # Agent 1 — file dependency analysis
    │
    ├── database/
    │   └── agent.py               # Agent 2 — database/schema impact analysis
    │
    └── test_agent/
        └── agent.py               # Agent 3 — test discovery & relevance filtering
```

---

## Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **pip** (bundled with Python)
- An **IBM watsonx.ai** account with:
  - An API key
  - A project ID
  - Access to `ibm/granite-4-h-small` (or another supported model)

---

## Setup (Virtual Environment)

### 1. Navigate to the project

```bash
cd d:\Work\Hackathon\IBM_BOB_2.0
```

### 2. Create the virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows — PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows — Command Prompt:**
```cmd
venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

> ✅ When active, your prompt shows `(venv)` at the start.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

Dependencies installed:

| Package | Purpose |
|---|---|
| `langgraph` | Multi-agent pipeline orchestration |
| `langchain-core` | Core LangChain abstractions used by LangGraph |
| `ibm-watsonx-ai` | IBM Granite model inference client |
| `python-dotenv` | Loads `.env` credentials at runtime |
| `fastapi` | REST API layer (for future frontend integration) |
| `uvicorn` | ASGI server for FastAPI |

---

## Configuration

### 1. Copy the example file

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

### 2. Edit `.env` with your credentials

```env
# IBM watsonx.ai credentials
WATSONX_API_KEY=your-api-key-here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_PROJECT_ID=your-project-id-here

# Model to use
WATSONX_MODEL_ID=ibm/granite-4-h-small

# Path to the repository Bob will analyse
REPO_PATH=./payment/IBM-bob-payment-demo
```

| Variable | Required | Description |
|---|---|---|
| `WATSONX_API_KEY` | ✅ | Your IBM Cloud API key |
| `WATSONX_URL` | ✅ | Regional watsonx.ai endpoint |
| `WATSONX_PROJECT_ID` | ✅ | Your watsonx.ai project ID |
| `WATSONX_MODEL_ID` | optional | Defaults to `ibm/granite-4-h-small` |
| `REPO_PATH` | set in `main.py` | Override in `main.py` if needed |

> 🔒 `.env` is listed in `.gitignore` and will never be committed.

---

## Running the Program

> **Always activate the virtual environment first** (see [Setup](#setup-virtual-environment)).

---

### Mode 1 — Web UI (Uvicorn / FastAPI) ✅ Recommended

`api.py` is the web entry point. It starts a FastAPI server that:
- Serves the **`index.html`** frontend at `GET /`
- Accepts pipeline runs via `POST /run`
- Streams real-time progress via **Server-Sent Events** at `GET /stream/{run_id}`
- Accepts human approval via `POST /approve/{run_id}`

#### Start the server

```powershell
# From d:\Work\Hackathon\IBM_BOB_2.0, with venv activated:
uvicorn api:app --reload --port 8000
```

| Flag | Effect |
|---|---|
| `api:app` | Load the `app` object from `api.py` |
| `--reload` | Auto-restart on file changes (dev mode) |
| `--port 8000` | Listen on port 8000 (change freely) |

#### Optional flags

```powershell
# Bind to all interfaces (useful for LAN / Docker)
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# Production mode (no reload, multiple workers)
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Open the UI

Once the server is running, open your browser at:

```
http://localhost:8000
```

The browser loads `index.html`. Fill in:
- **Change description** — plain-English description of the intended change
- **Repository path** — path to the JS/TS repo Bob will analyse (e.g. `./payment/IBM-bob-payment-demo`)

Bob streams results in real-time and prompts you to **Approve / Reject** the implementation plan before executing.

#### Expected terminal output on startup

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [...]
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

### Mode 2 — CLI (terminal)

`main.py` runs the full pipeline interactively in your terminal (no browser required). Human approval is via a simple `y/n` prompt.

```powershell
python main.py
```

You will see:

```
╔══════════════════════════════════════════════════╗
║        🤖  Bob Change Impact Mode                ║
╚══════════════════════════════════════════════════╝

📝  Describe your change
    (default: Add PayPal support alongside existing Stripe integration)
    >
```

- Press **Enter** to use the built-in example change, or
- Type your own change description and press **Enter**.

Bob will run the full pipeline and print the final report.

### Changing the target repository

Edit the two constants at the top of `main.py`:

```python
_DEFAULT_CHANGE = "Your default change description"
_REPO_PATH      = "./path/to/your/repo"
```

The repository must contain JS/TS source files and optionally a `tests/` directory.

### Deactivating the virtual environment

```bash
deactivate
```

---

## API Endpoints

All endpoints are served by `api.py` when running via uvicorn.

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves `index.html` (the frontend SPA) |
| `POST` | `/run` | Start a new pipeline run. Returns a `run_id`. |
| `GET` | `/stream/{run_id}` | SSE stream of pipeline events for the given run |
| `POST` | `/approve/{run_id}` | Submit human approval decision (approve/reject) |

### `POST /run` — Request body

```json
{
  "change_description": "Add PayPal support alongside existing Stripe integration",
  "repo_path": "./payment/IBM-bob-payment-demo"
}
```

### `POST /run` — Response

```json
{ "run_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6" }
```

### `GET /stream/{run_id}` — SSE events

Events are emitted as `data: <json>\n\n` in the SSE stream:

| Event name | Key payload fields |
|---|---|
| `pipeline_started` | *(empty)* |
| `parallel_agents_done` | `affected_files`, `database_impact`, `tests_to_run` |
| `impact_report_done` | `risk_level`, `impact_summary` |
| `implementation_plan_done` | `implementation_plan` |
| `awaiting_approval` | *(triggers the approve UI in the frontend)* |
| `bob_execution_done` | `code_modified`, `affected_files` |
| `test_results_done` | `test_results` |
| `final_report_done` | `final_report`, `human_approved`, `errors` |
| `error` | `message` |

### `POST /approve/{run_id}` — Request body

```json
{ "approved": true }
```



---

## State Schema

The full shared state (`agents/state.py`) passed between every node:

```python
class AgentState(TypedDict):
    # Input
    change_description: str          # e.g. "Add PayPal support"
    repo_path: str                   # e.g. "./payment/demo"

    # Agent 1 — Dependency
    affected_files: List[str]        # e.g. ["src/payment.js"]

    # Agent 2 — Database
    database_impact: List[Dict]      # e.g. [{"table": "transactions", "risk": "HIGH"}]

    # Agent 3 — Test
    tests_to_run: List[str]          # e.g. ["payment.test.js"]

    # Impact Report
    risk_level: str                  # "HIGH" | "MEDIUM" | "LOW"
    impact_summary: str              # markdown

    # Implementation Plan
    implementation_plan: str         # markdown, numbered steps

    # Human Approval
    human_approved: bool

    # Execution
    code_modified: bool
    test_results: Dict[str, Any]     # { status, passed, per_test, tests_run, ... }
    retry_count: int

    # Final Report
    final_report: str                # markdown

    # Errors
    errors: List[str]
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError` | Activate the venv and run `pip install -r requirements.txt` |
| PowerShell script blocked | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry activation |
| `KeyError: WATSONX_API_KEY` | Ensure `.env` exists and contains the correct key |
| `AuthenticationError` | Double-check `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` |
| `No test files found` | The target repo must have a `tests/` folder with `*.test.js` or `*.spec.js` files |
| `No JS/TS files found` | The Dependency Agent only scans `.js / .ts / .jsx / .tsx` files |
| JSON parse errors in output | Usually a model response format issue — check `errors` field in the final report |
| `uvicorn: command not found` | Run `pip install uvicorn` inside the activated venv |
| Port 8000 already in use | Change the port: `uvicorn api:app --reload --port 8001` |
| Browser shows "index.html not found" | Ensure you start uvicorn **from** `d:\Work\Hackathon\IBM_BOB_2.0` (the directory containing `index.html`) |
| SSE stream hangs / no events | Check the browser DevTools Network tab — if the `/stream/` request is pending, the pipeline is still running |
| `_session` KeyError in pipeline | You are running `main.py` with a state dict that lacks `_session`; this field is only needed in web mode via `api.py` |

