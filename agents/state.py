from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):

    # --- INPUT -------------------------------------------
    change_description: str
    # ex: "Add PayPal support"

    repo_path: str
    # ex: "./bob-demo"

    # --- AGENT 1 - DEPENDENCY ----------------------------
    affected_files: List[str]
    # ex: ["src/payment.js", "src/order.js"]

    # --- AGENT 2 - DATABASE ------------------------------
    database_impact: List[Dict[str, str]]
    # ex: [{"table": "transactions", "risk": "HIGH"}]

    # --- AGENT 3 - TEST ----------------------------------
    tests_to_run: List[str]
    # ex: ["tests/payment.test.js"]

    # --- IMPACT REPORT -----------------------------------
    risk_level: str
    # HIGH / MEDIUM / LOW

    impact_summary: str
    # markdown summary

    # --- IMPLEMENTATION PLAN -----------------------------
    implementation_plan: str
    # step-by-step plan

    # --- HUMAN APPROVAL ----------------------------------
    human_approved: bool

    # --- BOB EXECUTION -----------------------------------
    code_modified: bool
    test_results: Dict[str, Any]
    retry_count: int

    # --- FINAL REPORT ------------------------------------
    final_report: str

    # --- ERRORS ------------------------------------------
    errors: List[str]

    # --- WEB MODE (optional - absent in CLI runs) --------
    run_id: Optional[str]
    # UUID string passed by api.py; absent when run from main.py

    _session: Optional[Any]
    # RunSession object injected by api.py so human_approval_node
    # can push SSE events without importing api.py directly.
