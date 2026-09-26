import json
from concurrent.futures import ThreadPoolExecutor
from typing import Literal
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

from agents.state import AgentState
from agents.dependency.agent import dependency_agent
from agents.database.agent import database_agent
from agents.test_agent.agent import test_agent
from agents.bob_client import get_model, chat

load_dotenv()
model = get_model()


# ═══════════════════════════════════════
# NODE 1 — Run 3 agents in PARALLEL
# ═══════════════════════════════════════
def parallel_agents_node(state: AgentState) -> dict:
    """Lance les 3 agents en parallèle"""
    print("\n🚀 Running 3 agents in parallel...")

    with ThreadPoolExecutor(max_workers=3) as executor:
        f1 = executor.submit(dependency_agent, state)
        f2 = executor.submit(database_agent, state)
        f3 = executor.submit(test_agent, state)

        dep    = f1.result()
        db     = f2.result()
        tests  = f3.result()

    return {
        "affected_files":  dep["affected_files"],
        "database_impact": db["database_impact"],
        "tests_to_run":    tests["tests_to_run"]
    }


# ═══════════════════════════════════════
# NODE 2 — Generate Impact Report
# ═══════════════════════════════════════
def impact_report_node(state: AgentState) -> dict:
    """Génère le rapport d'impact"""
    print("\n📊 Generating Impact Report...")

    prompt = f"""
You are a senior tech lead reviewing a code change.

Change requested: "{state['change_description']}"

Analysis results:
- Affected files ({len(state['affected_files'])}):
  {state['affected_files']}
- Database tables impacted:
  {json.dumps(state['database_impact'], indent=2)}
- Tests to run ({len(state['tests_to_run'])}):
  {state['tests_to_run']}

Generate a clear impact report.
Return ONLY valid JSON:
{{
    "risk_level": "HIGH",
    "impact_summary": "## Impact Report\\n...",
    "key_risks": ["risk1", "risk2"],
    "estimated_effort": "2-3 hours"
}}
"""

    try:
        text = chat(model, prompt)
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
    except:
        result = {
            "risk_level": "UNKNOWN",
            "impact_summary": "Could not generate report",
            "key_risks": [],
            "estimated_effort": "Unknown"
        }

    print(f"⚠️  Risk Level: {result['risk_level']}")
    return {
        "risk_level": result["risk_level"],
        "impact_summary": result["impact_summary"]
    }


# ═══════════════════════════════════════
# NODE 3 — Generate Implementation Plan
# ═══════════════════════════════════════
def implementation_plan_node(state: AgentState) -> dict:
    """Génère le plan d'implémentation"""
    print("\n📋 Generating Implementation Plan...")

    prompt = f"""
You are a senior developer creating an implementation plan.

Change: "{state['change_description']}"
Risk Level: {state['risk_level']}
Affected files: {state['affected_files']}
DB Impact: {state['database_impact']}
Tests: {state['tests_to_run']}

Create a detailed step-by-step implementation plan.

Return ONLY valid JSON:
{{
    "implementation_plan": "## Plan\\n1. ...\\n2. ...\\n3. ..."
}}
"""

    try:
        text = chat(model, prompt)
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        plan = result.get("implementation_plan", "")
    except:
        plan = "Could not generate plan"

    print("✅ Plan generated!")
    return {"implementation_plan": plan}


# ═══════════════════════════════════════
# NODE 4 — Human Approval Gate
# ═══════════════════════════════════════
def human_approval_node(state: AgentState) -> dict:
    """Gate d'approbation humaine"""

    print("\n" + "═"*60)
    print("📊  IMPACT REPORT")
    print("═"*60)
    print(state["impact_summary"])
    print("\n📋  IMPLEMENTATION PLAN")
    print("═"*60)
    print(state["implementation_plan"])
    print("═"*60)
    print(f"\n⚠️  Risk Level: {state['risk_level']}")
    print(f"📁  Files: {len(state['affected_files'])}")
    print(f"🗄️  DB Tables: {len(state['database_impact'])}")
    print(f"🧪  Tests: {len(state['tests_to_run'])}")
    print("═"*60)

    answer = input("\n✅ Approve this change? (yes/no): ")
    approved = answer.strip().lower() in ["yes", "y", "oui"]

    if approved:
        print("✅ Change APPROVED!")
    else:
        print("❌ Change REJECTED!")

    return {
        "human_approved": approved,
        "retry_count": 0
    }


# ═══════════════════════════════════════
# NODE 5 — Bob Execution
# ═══════════════════════════════════════
def bob_execution_node(state: AgentState) -> dict:
    """IBM Bob modifie le code et lance les tests"""
    print("\n⚙️  IBM Bob executing change...")

    prompt = f"""
You are IBM Bob, an AI coding assistant.

Implement this change: "{state['change_description']}"

Files to modify: {state['affected_files']}
Implementation plan:
{state['implementation_plan']}

Generate the code changes needed.
Return ONLY valid JSON:
{{
    "changes_made": [
        {{
            "file": "src/payment.js",
            "change_type": "modified",
            "description": "Added PayPal integration"
        }}
    ],
    "success": true,
    "message": "Changes implemented successfully"
}}
"""

    try:
        text = chat(model, prompt)
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        success = result.get("success", False)
    except:
        success = False

    print(f"{'✅' if success else '❌'} Code modification {'successful' if success else 'failed'}")
    return {
        "code_modified": success,
        "test_results": {"status": "pending"}
    }


# ═══════════════════════════════════════
# NODE 6 — Test Runner
# ═══════════════════════════════════════
def test_runner_node(state: AgentState) -> dict:
    """Lance les tests"""
    print("\n🧪 Running tests...")

    # Simuler l'exécution des tests
    # En vrai : subprocess.run(["npm", "test"])
    import random
    passed = random.random() > 0.3  # 70% chance de succès

    results = {
        "passed": passed,
        "tests_run": len(state["tests_to_run"]),
        "tests_passed": len(state["tests_to_run"]) if passed else 0,
        "tests_failed": 0 if passed else len(state["tests_to_run"]),
        "output": "All tests passed! ✅" if passed else "Some tests failed ❌"
    }

    print(f"{'✅' if passed else '❌'} Tests: {results['output']}")
    return {"test_results": results}


# ═══════════════════════════════════════
# NODE 7 — Final Report
# ═══════════════════════════════════════
def final_report_node(state: AgentState) -> dict:
    """Génère le rapport final"""
    print("\n📄 Generating Final Report...")

    test_results = state.get("test_results", {})
    passed = test_results.get("passed", False)

    report = f"""
# 🤖 IBM Bob Change Analysis Report

## Change Request
**{state['change_description']}**

## Impact Analysis
- **Risk Level**: {state['risk_level']}
- **Files Affected**: {len(state['affected_files'])}
- **DB Tables Impacted**: {len(state['database_impact'])}
- **Tests Identified**: {len(state['tests_to_run'])}

## Execution Results
- **Code Modified**: {'✅ Yes' if state.get('code_modified') else '❌ No'}
- **Tests**: {'✅ PASSED' if passed else '❌ FAILED'}
- **Retry Count**: {state.get('retry_count', 0)}

## Status
{'✅ CHANGE COMPLETED SUCCESSFULLY' if passed else '❌ CHANGE FAILED - Manual review needed'}
"""

    print(report)
    return {"final_report": report}


# ═══════════════════════════════════════
# ROUTERS
# ═══════════════════════════════════════
def approval_router(state: AgentState) -> Literal["bob_execution", "final_report"]:
    if state["human_approved"]:
        return "bob_execution"
    return "final_report"


def test_result_router(state: AgentState) -> Literal["final_report", "bob_execution"]:
    results = state.get("test_results", {})
    retry_count = state.get("retry_count", 0)

    if results.get("passed", False):
        return "final_report"

    if retry_count >= 1:
        # Max 1 retry
        print("⚠️  Max retries reached. Stopping.")
        return "final_report"

    print(f"🔄 Tests failed. Retry {retry_count + 1}/1...")
    return "bob_execution"


# ═══════════════════════════════════════
# BUILD THE GRAPH
# ═══════════════════════════════════════
def build_graph():
    builder = StateGraph(AgentState)

    # Nodes
    builder.add_node("parallel_agents",      parallel_agents_node)
    builder.add_node("impact_report",        impact_report_node)
    builder.add_node("implementation_plan",  implementation_plan_node)
    builder.add_node("human_approval",       human_approval_node)
    builder.add_node("bob_execution",        bob_execution_node)
    builder.add_node("test_runner",          test_runner_node)
    builder.add_node("final_report",         final_report_node)

    # Edges
    builder.add_edge(START,                "parallel_agents")
    builder.add_edge("parallel_agents",    "impact_report")
    builder.add_edge("impact_report",      "implementation_plan")
    builder.add_edge("implementation_plan","human_approval")

    # Conditional edges
    builder.add_conditional_edges(
        "human_approval",
        approval_router,
        {
            "bob_execution": "bob_execution",
            "final_report":  "final_report"
        }
    )

    builder.add_edge("bob_execution", "test_runner")

    builder.add_conditional_edges(
        "test_runner",
        test_result_router,
        {
            "final_report":  "final_report",
            "bob_execution": "bob_execution"
        }
    )

    builder.add_edge("final_report", END)

    return builder.compile()


agent_graph = build_graph()
