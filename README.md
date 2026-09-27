# 🤖 Bob Change Impact Mode — IBM BOB 2.0

> Analyse the impact of a code change **before** it is made.  
> Powered by **IBM watsonx.ai** (Granite 4), orchestrated with **LangGraph**, and served via **FastAPI**.

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
main.py
  └── LangGraph StateGraph (agents/orchestrator/graph.py)
        │
        ├── [Parallel] dependency_agent   ← agents/dependency/agent.py
        ├── [Parallel] database_agent     ← agents/database/agent.py
        ├── [Parallel] test_agent         ← agents/test_agent/agent.py
        │
        ├── impact_report_node            (IBM Granite via watsonx.ai)
        ├── implementation_plan_node      (IBM Granite via watsonx.ai)
        ├── human_approval_node           (terminal y/n gate)
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
├── main.py                        # Entry point — CLI loop, initial state
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

Ensure the virtual environment is **activated**, then:

```bash
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
