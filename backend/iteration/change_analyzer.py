"""
Change Analyzer
---------------
When user wants to modify a project, this figures out
which layers (DB/Backend/Frontend) are affected.
Uses Phi-3 Mini for reasoning.
"""

from backend.llm.ollama_client import ask_planner, parse_json_response


CHANGE_ANALYSIS_PROMPT = """
A web app was built. The user wants to make a change.

Original app: {original_prompt}
User's change request: {change_request}

Which layers of the app need to be regenerated?

Respond ONLY with this JSON:
{{
  "affected_layers": ["database", "backend", "frontend", "infra"],
  "reason": "brief explanation",
  "scope": "small" | "medium" | "large",
  "description": "what exactly needs to change"
}}

Layer rules:
- "database": only if new tables, columns, or relationships needed
- "backend": if new endpoints, business logic, or auth changes
- "frontend": if UI changes, new pages, or different API calls
- "infra": only if new services (redis, celery, etc.) needed

Examples:
- "add dark mode" → ["frontend"] only
- "add user authentication" → ["database", "backend", "frontend"]
- "add a new field to user profile" → ["database", "backend", "frontend"]
- "change button color" → ["frontend"] only
- "add email notifications" → ["backend"] only
- "add payment processing" → ["database", "backend", "frontend"]
"""

CONTEXT_BUILD_PROMPT = """
I need to modify parts of a web app.

Change requested: {change_request}
Affected layers: {affected_layers}

Here are the relevant existing files:
{relevant_files}

Generate the updated files.
Return ONLY valid JSON:
{{
  "files": [
    {{
      "path": "path/to/file.py",
      "content": "full updated file content"
    }}
  ],
  "summary": "what was changed"
}}

Important:
- Return COMPLETE file contents, not just diffs
- Only return files that actually changed
- Keep unchanged code exactly as is
- Make minimal changes to accomplish the request
"""


async def analyze_change(original_prompt: str, change_request: str) -> dict:
    """
    Determine which layers are affected by a change request.
    Returns affected_layers list and scope.
    """
    raw = await ask_planner(CHANGE_ANALYSIS_PROMPT.format(
        original_prompt=original_prompt,
        change_request=change_request
    ))

    try:
        result = parse_json_response(raw)
        return result
    except ValueError:
        # Default — regenerate everything except infra
        return {
            "affected_layers": ["backend", "frontend"],
            "reason": "Could not analyze, defaulting to backend + frontend",
            "scope": "medium",
            "description": change_request
        }


def select_relevant_files(
    all_files: dict[str, str],
    affected_layers: list[str],
    change_request: str
) -> dict[str, str]:
    """
    From all project files, select only the ones relevant
    to the change. Keeps context small for LLM.
    """
    relevant = {}
    total_chars = 0
    MAX_CHARS = 3000  # Keep context tight for small model

    # Priority order for each layer
    layer_patterns = {
        "database": ["models.py", "schemas.py", "database.py"],
        "backend": ["routes/", "main.py", "core/security.py"],
        "frontend": ["App.jsx", "pages/", "api/client.js"],
        "infra": ["docker-compose.yml", ".env.example"]
    }

    for layer in affected_layers:
        patterns = layer_patterns.get(layer, [])
        for path, content in all_files.items():
            if total_chars >= MAX_CHARS:
                break
            if any(p in path for p in patterns):
                # Trim individual files too
                trimmed = content[:800]
                relevant[path] = trimmed
                total_chars += len(trimmed)

    return relevant


def format_relevant_files(files: dict[str, str]) -> str:
    """Format files dict as string for prompt."""
    parts = []
    for path, content in files.items():
        parts.append(f"=== {path} ===\n{content}\n")
    return "\n".join(parts)
