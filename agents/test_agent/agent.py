import os
import json
from dotenv import load_dotenv
from agents.bob_client import get_model, chat

load_dotenv()
model = get_model()

def test_agent(state: dict) -> dict:
    """
    Agent 3 — Test Agent
    Trouve les tests à lancer
    """
    print("🧪 Test Agent running...")

    affected_files = state["affected_files"]
    repo_path = state["repo_path"]

    # ── Trouver tous les fichiers de test ──
    test_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs
                   if d not in ['node_modules', '.git']]
        for file in files:
            if any(kw in file.lower() for kw in
                   ['test', 'spec', '.test.', '.spec.']):
                relative = os.path.join(root, file)\
                    .replace(repo_path, "").lstrip("/\\")
                test_files.append(relative)

    prompt = f"""
You are a test impact analyzer.

Files being changed: {affected_files}
Available test files: {test_files}

Which tests should be run for this change?
Also estimate if tests will pass or fail.

Return ONLY valid JSON:
{{
    "tests_to_run": ["test1.js", "test2.js"],
    "estimated_failures": ["test that might fail"],
    "coverage_percentage": 75,
    "recommendation": "Run all payment tests"
}}
"""

    try:
        text = chat(model, prompt)
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        tests = result.get("tests_to_run", [])
    except Exception as e:
        tests = ["Error finding tests"]
        print(f"❌ Test Agent error: {e}")

    print(f"✅ Test Agent: {len(tests)} tests to run")
    return {"tests_to_run": tests}
