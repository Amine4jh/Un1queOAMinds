import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

def database_agent(state: dict) -> dict:
    """
    Agent 2 — Database Agent
    Trouve l'impact sur la base de données
    """
    print("🗄️ Database Agent running...")

    affected_files = state["affected_files"]
    repo_path = state["repo_path"]

    # ── Lire le contenu des fichiers touchés ──
    files_content = {}
    for filepath in affected_files:
        full_path = os.path.join(
            repo_path,
            filepath.lstrip("/\\")
        )
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                files_content[filepath] = f.read()[:1000]
        except:
            files_content[filepath] = "File not found"

    # ── Chercher aussi les fichiers schema/migration ──
    schema_files = {}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs
                   if d not in ['node_modules', '.git']]
        for file in files:
            if any(kw in file.lower() for kw in
                   ['schema', 'migration', 'model', 'database']):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        schema_files[file] = f.read()[:500]
                except:
                    pass

    prompt = f"""
You are a database impact analyzer.

Files being changed:
{json.dumps(files_content, indent=2)[:4000]}

Schema/Model files found:
{json.dumps(schema_files, indent=2)[:2000]}

Analyze the database impact of these changes.

Return ONLY valid JSON:
{{
    "tables_impacted": [
        {{
            "table": "transactions",
            "operations": ["INSERT", "SELECT"],
            "risk": "HIGH"
        }}
    ],
    "schema_changes_needed": true,
    "risk_level": "HIGH",
    "details": "brief explanation"
}}
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        text = response.content[0].text
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        db_impact = result.get("tables_impacted", [])
    except Exception as e:
        db_impact = [{"table": "unknown", "risk": "UNKNOWN"}]
        print(f"❌ Database Agent error: {e}")

    print(f"✅ Database Agent: {len(db_impact)} tables impacted")
    return {"database_impact": db_impact}
