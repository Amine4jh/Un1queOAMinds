"""
api.py — FastAPI wrapper around the LangGraph pipeline.

Start with:
    uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import json
import queue
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

load_dotenv()

# ── Lazy import of agent_graph to avoid watsonx connect at import time if
#    the module-level model initialisation happens there.  We import it once
#    at first request instead (see _get_graph()).
_agent_graph = None
_graph_lock = threading.Lock()


def _get_graph():
    global _agent_graph
    if _agent_graph is None:
        with _graph_lock:
            if _agent_graph is None:
                from agents.orchestrator.graph import agent_graph  # noqa: PLC0415
                _agent_graph = agent_graph
    return _agent_graph


# ─────────────────────────────────────────────
#  Run registry
# ─────────────────────────────────────────────

@dataclass
class RunSession:
    state: Dict[str, Any] = field(default_factory=dict)
    approval_event: threading.Event = field(default_factory=threading.Event)
    approved: bool = False
    queue: queue.Queue = field(default_factory=queue.Queue)


# run_id → RunSession
runs: Dict[str, RunSession] = {}

_executor = ThreadPoolExecutor(max_workers=4)

# ─────────────────────────────────────────────
#  Node-name → SSE event-name lookup
# ─────────────────────────────────────────────

_NODE_EVENT: Dict[str, str] = {
    "parallel_agents":     "parallel_agents_done",
    "impact_report":       "impact_report_done",
    "implementation_plan": "implementation_plan_done",
    "bob_execution":       "bob_execution_done",
    "test_runner":         "test_results_done",
    "final_report":        "final_report_done",
}

# Fields to extract from the state delta per event
_EVENT_FIELDS: Dict[str, list] = {
    "parallel_agents_done":     ["affected_files", "database_impact", "tests_to_run"],
    "impact_report_done":       ["risk_level", "impact_summary"],
    "implementation_plan_done": ["implementation_plan"],
    "bob_execution_done":       ["code_modified", "affected_files"],
    "test_results_done":        ["test_results"],
    "final_report_done":        ["final_report", "human_approved", "errors"],
}


def _pick(delta: dict, fields: list) -> dict:
    return {k: delta[k] for k in fields if k in delta}


# ─────────────────────────────────────────────
#  Pipeline runner (background thread)
# ─────────────────────────────────────────────

def _run_pipeline(run_id: str, initial_state: dict) -> None:
    session = runs[run_id]
    try:
        graph = _get_graph()

        # Signal that we have started
        session.queue.put({"event": "pipeline_started", "payload": {}})

        for chunk in graph.stream(initial_state, stream_mode="updates"):
            # chunk is {node_name: state_delta}
            for node_name, delta in chunk.items():
                # Merge delta into session state
                session.state.update(delta)

                event_name = _NODE_EVENT.get(node_name)
                if event_name is None:
                    # e.g. "human_approval" — awaiting_approval is pushed
                    # from within the node via _session; nothing extra here.
                    continue

                fields = _EVENT_FIELDS.get(event_name, [])
                payload = _pick(delta, fields)
                session.queue.put({"event": event_name, "payload": payload})

                if event_name == "final_report_done":
                    # Sentinel closes the SSE stream
                    session.queue.put(None)
                    return

        # If stream ends without final_report (e.g. graph has no such node)
        session.queue.put(None)

    except Exception as exc:  # noqa: BLE001
        session.queue.put({"event": "error", "payload": {"message": str(exc)}})
        session.queue.put(None)


# ─────────────────────────────────────────────
#  FastAPI application
# ─────────────────────────────────────────────

app = FastAPI(title="Bob Change Impact API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────

class RunRequest(BaseModel):
    change_description: str
    repo_path: str


class ApproveRequest(BaseModel):
    approved: bool


# ── Routes ───────────────────────────────────

@app.get("/")
def serve_index():
    """Serve the frontend SPA."""
    try:
        return FileResponse("index.html")
    except Exception:  # noqa: BLE001
        return PlainTextResponse(
            "index.html not found. Start the frontend (Sub-Task 5).",
            status_code=200,
        )


@app.post("/run")
def start_run(body: RunRequest):
    """Launch the pipeline in a background thread and return a run_id."""
    run_id = str(uuid.uuid4())
    session = RunSession()
    runs[run_id] = session

    initial_state: dict = {
        # ── Input ──────────────────────────────────────
        "change_description":  body.change_description,
        "repo_path":           body.repo_path,
        # ── Agent outputs (empty until agents run) ─────
        "affected_files":      [],
        "database_impact":     [],
        "tests_to_run":        [],
        # ── Impact report ──────────────────────────────
        "risk_level":          "",
        "impact_summary":      "",
        # ── Implementation plan ────────────────────────
        "implementation_plan": "",
        # ── Human approval ─────────────────────────────
        "human_approved":      False,
        # ── Execution ──────────────────────────────────
        "code_modified":       False,
        "test_results":        {},
        "retry_count":         0,
        # ── Final report ───────────────────────────────
        "final_report":        "",
        # ── Errors ─────────────────────────────────────
        "errors":              [],
        # ── Web-mode metadata (not part of AgentState TypedDict,
        #    but Python dicts accept extra keys at runtime) ────
        "run_id":              run_id,
        "_session":            session,
    }

    _executor.submit(_run_pipeline, run_id, initial_state)
    return {"run_id": run_id}


@app.get("/stream/{run_id}")
def stream_run(run_id: str):
    """SSE stream of pipeline events for the given run."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="run_id not found")

    session = runs[run_id]

    def _generator() -> Generator[str, None, None]:
        while True:
            item = session.queue.get()
            if item is None:
                # Sentinel — close the stream
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/approve/{run_id}")
def approve_run(run_id: str, body: ApproveRequest):
    """Record the human decision and unblock the pipeline thread."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="run_id not found")

    session = runs[run_id]
    session.approved = body.approved
    session.approval_event.set()
    return {"status": "ok"}
