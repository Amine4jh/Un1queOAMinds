import os
import json
from dotenv import load_dotenv
from agents.bob_client import get_model, chat

load_dotenv()
model = get_model()

def dependency_agent(state: dict) -> dict:
    """
    Agent 1 — Dependency Agent
    Trouve tous les fichiers touchés
    par le changement demandé
    """
    print("🔍 Dependency Agent running...")

    change = state["change_description"]
    repo_path = state["repo_path"]

    # ── Lire tous les fichiers du repo ──
    all_files = []
    files_content = {}

    for root, dirs, files in os.walk(repo_path):
        # Ignorer les dossiers inutiles
        dirs[:] = [
            d for d in dirs
            if d not in [
                'node_modules', '.git',
                '__pycache__', '.next',
                'dist', 'build'
            ]
        ]
        for file in files:
            # Seulement les fichiers de code
            if file.endswith((
                '.js', '.ts', '.py',
                '.json', '.sql', '.env.example'
            )):
                filepath = os.path.join(root, file)
                relative = filepath.replace(repo_path, "").lstrip("/\\")
                all_files.append(relative)

                # Lire le contenu (max 500 chars)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        files_content[relative] = f.read()[:500]
                except:
                    files_content[relative] = ""

    # ── Demander à Claude ──
    prompt = f"""
You are a code dependency analyzer.

The developer wants to: "{change}"

Here are all the project files with their content:
{json.dumps(files_content, indent=2)[:8000]}

Analyze which files would be directly or indirectly
affected by this change.

Return ONLY valid JSON (no explanation):
{{
    "affected_files": ["file1.js", "file2.js"],
    "reason": "brief explanation"
}}
"""

    try:
        text = chat(model, prompt)
        # Nettoyer si y'a des backticks
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        affected = result.get("affected_files", [])
    except Exception as e:
        affected = ["Error parsing response"]
        print(f"❌ Dependency Agent error: {e}")

    print(f"✅ Dependency Agent: {len(affected)} files affected")
    return {"affected_files": affected}
