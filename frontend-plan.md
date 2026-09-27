# Bob Change Impact Mode — Frontend Implementation Plan

## Top-Level Overview

**Goal:** Add a single-page HTML frontend (`index.html`) to the existing Python CLI tool so that
the full LangGraph pipeline is driven from a browser instead of the terminal.

**Approach:**

1. Wrap the existing LangGraph graph in a FastAPI application (`api.py`) that exposes three
   endpoints: start a run, stream events via SSE, and submit the human-approval decision.
2. Modify `human_approval_node` in `graph.py` so it suspends the pipeline and waits for an
   HTTP signal instead of blocking on `input()`.
3. Build a single `index.html` file (Tailwind CDN + vanilla JS) that drives the staged UI
   entirely from SSE events.

**Scope — files to create or modify:**

| Action   | File                                  |
|----------|---------------------------------------|
| Create   | `IBM_BOB_2.0/api.py`                  |
| Create   | `IBM_BOB_2.0/index.html`              |
| Modify   | `IBM_BOB_2.0/agents/orchestrator/graph.py` |
| No change | All agent files, state.py, bob_client.py |

---

## Sub-Task 1 — Design and document the API contract

**Intent:**  
Establish the exact HTTP API that the frontend will consume. Every other sub-task depends on
this contract being stable.

**Expected Outcomes:**
- Three endpoints defined with request/response shapes.
- SSE event catalogue defined (one event type per pipeline stage).
- Session/run-ID strategy chosen (UUID stored in a server-side dict).

**API Contract:**

### POST /run
Starts a new pipeline run. Returns immediately with a `run_id`.

Request body:
```json
{
  "change_description": "Add PayPal support",
  "repo_path": "./payment/IBM-bob-payment-demo"
}
```

Response:
```json
{ "run_id": "uuid4-string" }
```

### GET /stream/{run_id}
Server-Sent Events stream. Keeps the connection open until `final_report_done` or an error.

Each SSE message is:
```
data: { "event": "<event_name>", "payload": { ...fields } }\n\n
```

| event name               | payload fields                                                                               |
|--------------------------|----------------------------------------------------------------------------------------------|
| `pipeline_started`       | `{}`                                                                                         |
| `parallel_agents_done`   | `{ affected_files, database_impact, tests_to_run }`                                          |
| `impact_report_done`     | `{ risk_level, impact_summary }`                                                             |
| `implementation_plan_done` | `{ implementation_plan }`                                                                  |
| `awaiting_approval`      | `{}` — frontend shows Approve/Reject buttons                                                 |
| `bob_execution_done`     | `{ code_modified, affected_files }`                                                          |
| `test_results_done`      | `{ test_results }` — full test_results object                                                |
| `final_report_done`      | `{ final_report, human_approved, errors }`                                                   |
| `error`                  | `{ message }`                                                                                |

### POST /approve/{run_id}
Sends the human approval decision. Unblocks the suspended pipeline.

Request body:
```json
{ "approved": true }
```

Response:
```json
{ "status": "ok" }
```

**Todo List:**
- [x] Define three endpoints and their shapes (documented above)
- [x] Define SSE event catalogue (documented above)

**Status:** `[x] done`

---

## Sub-Task 2 — Backend: `api.py` (FastAPI application)

**Intent:**  
Create a new `api.py` that wraps the existing LangGraph graph in FastAPI routes.
The CLI `main.py` is left untouched and continues to work as before.

**Expected Outcomes:**
- `uvicorn api:app` starts the server.
- `POST /run` launches the pipeline in a background thread and returns `run_id`.
- `GET /stream/{run_id}` streams SSE events to the caller.
- `POST /approve/{run_id}` sets the approval flag and unblocks the pipeline.

**Todo List:**
- [ ] Create `api.py` at the project root.
- [ ] Import `agent_graph` from `agents.orchestrator.graph`; import `AgentState`.
- [ ] Create an in-memory run registry: `runs: dict[str, RunSession]` where `RunSession`
      holds the current `state`, an `asyncio.Event` (approval gate), and a `Queue` of
      SSE events.
- [ ] Implement `POST /run`: build `initial_state`, create a `RunSession`, launch the
      pipeline in a `ThreadPoolExecutor` background thread, return `{"run_id": run_id}`.
- [ ] Implement `GET /stream/{run_id}`: use `EventSourceResponse` (from `sse-starlette`
      or a manual `StreamingResponse`) to drain the session's event queue.
- [ ] Implement `POST /approve/{run_id}`: store `approved` in the session and set the
      `threading.Event` that the modified `human_approval_node` is waiting on.
- [ ] Add CORS middleware (`allow_origins=["*"]`) so the HTML file can be opened directly
      from the filesystem during development.
- [ ] Mount `index.html` as a static file at `/` (optional convenience).
- [ ] Add `sse-starlette` to `requirements.txt`.

**Relevant Context:**
- `agents/orchestrator/graph.py` — `build_graph()` / `agent_graph` at module level.
- `agents/state.py` — `AgentState` TypedDict (all fields the pipeline reads/writes).
- `requirements.txt` — already has `fastapi` and `uvicorn`; add `sse-starlette`.

**Status:** `[ ] pending`

---

## Sub-Task 3 — Backend: modify `human_approval_node` in `graph.py`

**Intent:**  
Replace the blocking `input()` call with a mechanism that suspends the pipeline thread
until the `/approve/{run_id}` endpoint delivers the user's decision.

**Expected Outcomes:**
- The pipeline thread pauses at `human_approval_node` and does not consume CPU.
- When `/approve` is called, the thread resumes within milliseconds.
- The CLI (`main.py`) still works: detect whether a `run_id` is in the state and fall
  back to `input()` if not.

**Todo List:**
- [ ] Add an optional `run_id` field to `AgentState` in `agents/state.py`.
- [ ] In `human_approval_node`, check `state.get("run_id")`.
  - If `run_id` is present: emit an `awaiting_approval` SSE event via the run registry,
    then call `threading.Event.wait()` (blocking, with a long timeout e.g. 10 min).
  - If `run_id` is absent: keep the existing `input()` path (CLI unchanged).
- [ ] Import the run registry from `api.py` into `graph.py` using a lazy import or
      dependency-injection pattern to avoid circular imports.  
      **Preferred pattern:** pass a callback into the node via a closure or a thread-local;
      `api.py` wraps `build_graph()` by monkey-patching the node or by passing an
      `approval_callback` in the initial state.
- [ ] After `Event.wait()` resolves, read `approved` from the session and return
      `{"human_approved": approved, "retry_count": 0}`.
- [ ] Emit an SSE event for each completed node from within `api.py`'s pipeline runner
      (post-process the final state dict after each node, or use LangGraph's
      `stream_mode="values"` / `stream_mode="updates"` to receive node-by-node results).

**Relevant Context:**
- `graph.py` lines 128–152 — current `human_approval_node` with `input()`.
- LangGraph `agent_graph.invoke()` is synchronous; `agent_graph.stream()` yields
  `(node_name, state_delta)` tuples that can be mapped to SSE events.
- Use `agent_graph.stream(initial_state)` instead of `.invoke()` in the background thread
  so each node completion is observable without modifying the node functions.

**Status:** `[ ] pending`

---

## Sub-Task 4 — Backend: stream node completions as SSE events

**Intent:**  
Replace the single `agent_graph.invoke()` call with `agent_graph.stream()` so that each
node's output is forwarded to the SSE queue immediately when it completes, giving the
frontend live updates.

**Expected Outcomes:**
- After `parallel_agents_node` finishes, `parallel_agents_done` is pushed to the queue.
- After each subsequent node finishes, the matching SSE event is pushed.
- `awaiting_approval` is pushed before `human_approval_node` blocks.
- `final_report_done` is pushed last; the SSE stream closes.

**Todo List:**
- [ ] In the pipeline background thread in `api.py`, call
      `agent_graph.stream(initial_state, stream_mode="updates")`.
- [ ] Map each yielded `(node_name, delta)` to its SSE event name using a lookup dict:
  ```
  "parallel_agents"     → "parallel_agents_done"
  "impact_report"       → "impact_report_done"
  "implementation_plan" → "implementation_plan_done"
  "human_approval"      → (push "awaiting_approval" BEFORE the node runs — see sub-task 3)
  "bob_execution"       → "bob_execution_done"
  "test_runner"         → "test_results_done"
  "final_report"        → "final_report_done"
  ```
- [ ] Select only the relevant fields from `delta` for each event's payload (per the
      event catalogue in Sub-Task 1).
- [ ] After pushing `final_report_done`, push a sentinel `None` to the queue to close
      the SSE stream.

**Relevant Context:**
- LangGraph `stream_mode="updates"` yields `{node_name: state_delta}` dicts.
- The approval-gate event (`awaiting_approval`) must be emitted by the node itself
  before it blocks; the stream loop will see `human_approval` appear in the delta only
  after the node completes — so the "awaiting" signal must come from within the node
  (via the session queue) before it calls `Event.wait()`.

**Status:** `[ ] pending`

---

## Sub-Task 5 — Frontend: HTML structure (`index.html`)

**Intent:**  
Build the static HTML skeleton with all section IDs that JavaScript will populate.
No JavaScript logic yet — just the DOM layout, Tailwind classes, and a markdown renderer
(marked.js via CDN).

**Expected Outcomes:**
- Opening `index.html` in a browser shows the form and empty stage placeholders.
- Tailwind dark-mode utility classes provide the visual style.
- A `<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js">` tag is present.

**HTML Section Map:**

```
<body>
  #header          — Title bar "🤖 Bob Change Impact Mode"
  #form-section    — change_description input, repo_path input, submit button
  #stages-container — (empty until JS fills it)
    #stage-1       — Agents Running (injected dynamically)
    #stage-2       — Impact Report
    #stage-3       — Implementation Plan
    #stage-4       — Human Approval
    #stage-5       — Bob Execution
    #stage-6       — Test Results
    #stage-7       — Final Report
  #error-panel     — Collapsible errors (hidden until errors array is non-empty)
```

**Todo List:**
- [ ] Create `index.html` with `<!DOCTYPE html>`, `<html lang="en">`, Tailwind CDN
      `<script src="https://cdn.tailwindcss.com">`, marked.js CDN.
- [ ] Add `#form-section` with two `<input>` fields (`id="change-desc"`,
      `id="repo-path"`) and a `<button id="analyse-btn">Analyse</button>`.
- [ ] Add `#stages-container` as an empty `<div>` where stage cards are appended.
- [ ] Add `#error-panel` as a hidden `<details>` element with `id="error-panel"`.
- [ ] Define CSS custom configuration for Tailwind inside a `<script>` block:
      configure the `tailwind.config` to include a `prose` variant for markdown
      (use the Tailwind Typography CDN plugin).
- [ ] Pre-define the seven stage card templates as hidden `<template>` elements so JS
      can clone them without building HTML strings.

**Status:** `[ ] pending`

---

## Sub-Task 6 — Frontend: JavaScript architecture (`index.html` script)

**Intent:**  
Implement the vanilla JS that drives the staged UI: starts a run, opens an SSE stream,
and renders each stage card as its event arrives.

**Expected Outcomes:**
- Clicking "Analyse" POSTs to `/run`, receives `run_id`, opens `EventSource`.
- Each SSE event reveals and populates the matching stage card.
- Markdown fields are rendered with `marked.parse()`.
- Approve/Reject buttons POST to `/approve/{run_id}` and then hide themselves.
- Errors array populates `#error-panel` if non-empty.

**JavaScript Module Outline:**

```
CONFIG           — BASE_URL (default "http://localhost:8000"), configurable
State            — { runId, eventSource }

analyseBtn.click → runPipeline()
  POST /run → runId
  openStream(runId)

openStream(runId)
  new EventSource(BASE_URL + "/stream/" + runId)
  onmessage → dispatch(event, payload)

dispatch(event, payload)
  "pipeline_started"          → showStage(1, "spinner")
  "parallel_agents_done"      → populateStage1(payload)
  "impact_report_done"        → populateStage2(payload)
  "implementation_plan_done"  → populateStage3(payload)
  "awaiting_approval"         → populateStage4(runId)
  "bob_execution_done"        → populateStage5(payload)
  "test_results_done"         → populateStage6(payload)
  "final_report_done"         → populateStage7(payload); closeStream()
  "error"                     → appendError(payload.message)

populateStage1(payload)
  Render affected_files as <ul>
  Render database_impact as <table> (table | risk badge)
  Render tests_to_run as <ul>

populateStage2(payload)
  marked.parse(impact_summary) into card body
  Risk badge: riskBadgeClass(risk_level)

populateStage3(payload)
  marked.parse(implementation_plan) into card body

populateStage4(runId)
  Show ✅ Approve / ❌ Reject buttons
  On click → POST /approve/{runId} { approved: bool } → hide buttons, show choice

populateStage5(payload)
  code_modified badge
  affected_files list with simulated action labels

populateStage6(payload)
  per_test table (test name | pass/fail badge)
  Summary row: X passed / Y failed / Z total

populateStage7(payload)
  marked.parse(final_report) into card body
  Final status badge: COMPLETED / REJECTED / FAILED

riskBadgeClass(level)
  HIGH   → "bg-red-100 text-red-800"
  MEDIUM → "bg-orange-100 text-orange-800"
  LOW    → "bg-yellow-100 text-yellow-800"
```

**Todo List:**
- [ ] Add a `<script>` block at the bottom of `index.html` with `BASE_URL` constant.
- [ ] Implement `runPipeline()`: disable the button, clear old stages, POST `/run`.
- [ ] Implement `openStream(runId)`: create `EventSource`, wire `onmessage` and `onerror`.
- [ ] Implement `dispatch()` switch statement mapping event names to render functions.
- [ ] Implement each `populateStageN()` function per the outline above.
- [ ] Implement `riskBadgeClass()` helper.
- [ ] Implement `appendError()`: reveal `#error-panel`, append `<li>` to error list.
- [ ] Implement `closeStream()`: close the `EventSource`.
- [ ] Parse SSE `data` field as JSON inside `onmessage`; extract `event` and `payload`.

**Status:** `[ ] pending`

---

## Sub-Task 7 — Frontend: Tailwind class strategy

**Intent:**  
Define the consistent Tailwind utility classes for stage cards, spinners, badges, and
markdown containers so the UI looks polished without a build step.

**Expected Outcomes:**
- Each stage card looks consistent: white rounded shadow card with a coloured left border
  to indicate the pipeline stage.
- Risk and test-result badges are clearly colour-coded.
- Markdown blocks are readable with `prose` typography.

**Class Reference:**

| Element                  | Tailwind classes                                                         |
|--------------------------|--------------------------------------------------------------------------|
| Stage card wrapper       | `bg-white rounded-xl shadow-md border-l-4 p-6 mb-4 transition-all`      |
| Stage card — pending     | `border-gray-200 opacity-50`                                             |
| Stage card — active/done | `border-blue-500 opacity-100`                                            |
| Stage title              | `text-lg font-semibold text-gray-800 mb-2`                               |
| Spinner                  | `animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full` |
| Risk badge HIGH          | `inline-block px-2 py-1 rounded text-xs font-bold bg-red-100 text-red-800`    |
| Risk badge MEDIUM        | `inline-block px-2 py-1 rounded text-xs font-bold bg-orange-100 text-orange-800` |
| Risk badge LOW           | `inline-block px-2 py-1 rounded text-xs font-bold bg-yellow-100 text-yellow-800` |
| Pass badge               | `inline-block px-2 py-1 rounded text-xs font-bold bg-green-100 text-green-800`   |
| Fail badge               | `inline-block px-2 py-1 rounded text-xs font-bold bg-red-100 text-red-800`       |
| Approve button           | `bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-6 rounded-lg`      |
| Reject button            | `bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-6 rounded-lg`          |
| Markdown container       | `prose prose-sm max-w-none`  (requires Tailwind Typography plugin)       |
| Error panel summary      | `cursor-pointer text-red-600 font-semibold`                              |

**Todo List:**
- [ ] Confirm Tailwind Typography CDN plugin is included (`@tailwindcss/typography`
      via `https://cdn.tailwindcss.com` already bundles it in v3 CDN builds).
- [ ] Apply card classes when each stage card is injected by JS.
- [ ] Apply badge classes in each `populateStageN()` function.

**Status:** `[ ] pending`

---

## Sub-Task 8 — Wiring and smoke-test checklist

**Intent:**  
Verify that all pieces connect end-to-end before declaring the implementation complete.

**Expected Outcomes:**
- `uvicorn api:app --reload` starts without import errors.
- Opening `index.html` in a browser, submitting the form, seeing all 7 stage cards appear.
- Approve/Reject buttons work and the pipeline continues correctly.
- CLI (`python main.py`) still works unchanged.

**Todo List:**
- [ ] Run `pip install sse-starlette` and add to `requirements.txt`.
- [ ] Start server with `uvicorn api:app --reload --port 8000`.
- [ ] Open `index.html` directly in browser (or via `python -m http.server`).
- [ ] Submit a test change and verify stage cards 1–3 appear.
- [ ] Click Approve and verify stages 5–7 appear.
- [ ] Click Reject and verify only stage 7 appears.
- [ ] Confirm `python main.py` still runs the CLI flow.
- [ ] Confirm errors array panel appears if a model call fails.

**Status:** `[ ] pending`
