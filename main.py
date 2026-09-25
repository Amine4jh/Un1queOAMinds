from agents.orchestrator.graph import agent_graph
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    print("╔══════════════════════════════════════╗")
    print("║   🤖 IBM Bob Change Impact Analyzer  ║")
    print("╚══════════════════════════════════════╝")

    change = input("\n📝 Describe your change: ")

    result = agent_graph.invoke({
        "change_description": change,
        "repo_path": os.getenv("REPO_PATH", "./bob-demo"),
        "affected_files": [],
        "database_impact": [],
        "tests_to_run": [],
        "risk_level": "",
        "impact_summary": "",
        "implementation_plan": "",
        "human_approved": False,
        "code_modified": False,
        "test_results": {},
        "retry_count": 0,
        "final_report": "",
        "errors": []
    })

    print("\n✅ Pipeline completed!")

if __name__ == "__main__":
    main()
