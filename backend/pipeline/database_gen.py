"""
Stage 2 — Database Generator
------------------------------
Takes the project plan and generates:
- SQLAlchemy models
- Database schema / migrations
- Seed data (optional)
"""

import json
from backend.llm.ollama_client import ask_coder, parse_json_response


DATABASE_PROMPT = """
Generate the database layer for this web app.

App: {prompt}
Database: {db_type}
ORM: SQLAlchemy

Planning context:
{interview_context}

Return ONLY this JSON structure:
{{
  "files": [
    {{
      "path": "backend/database/models.py",
      "content": "full file content here"
    }},
    {{
      "path": "backend/database/database.py", 
      "content": "full file content here"
    }},
    {{
      "path": "backend/database/schemas.py",
      "content": "full pydantic schemas here"
    }}
  ],
  "tables": ["list", "of", "table", "names"],
  "summary": "brief description of what was generated"
}}

Requirements:
- Use SQLAlchemy ORM with proper relationships
- Add Pydantic schemas for request/response validation
- Include created_at, updated_at timestamps on all models
- Use UUID primary keys
- Add proper indexes
- Database URL from environment variable DATABASE_URL
"""

DATABASE_SQLITE_PROMPT = """
Generate the database layer for this web app using SQLite.

App: {prompt}

Planning context:
{interview_context}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "files": [
    {{
      "path": "backend/database/models.py",
      "content": "..."
    }},
    {{
      "path": "backend/database/database.py",
      "content": "..."
    }},
    {{
      "path": "backend/database/schemas.py", 
      "content": "..."
    }}
  ],
  "tables": ["table1", "table2"],
  "summary": "what was generated"
}}

Use SQLite with SQLAlchemy. Simple, no migrations needed for dev.
"""


async def generate_database(plan: dict, websocket=None) -> dict:
    """
    Generate all database files from project plan.
    Returns dict with files list and metadata.
    """

    async def emit(event: str, message: str):
        if websocket:
            await websocket.send_json({"event": event, "message": message})

    await emit("stage", "Generating database layer...")

    db_type = plan["tech_stack"]["database"]["type"]
    prompt = plan["prompt"]

    # Build interview context string
    interview_context = ""
    for module_name, interview in plan["interview"].items():
        interview_context += f"\n=== {module_name} ===\n"
        interview_context += interview.get("full_context", "")

    # Trim context to avoid token overflow
    interview_context = interview_context[:2000]

    # Choose prompt based on DB type
    if db_type == "sqlite":
        final_prompt = DATABASE_SQLITE_PROMPT.format(
            prompt=prompt,
            interview_context=interview_context
        )
    else:
        final_prompt = DATABASE_PROMPT.format(
            prompt=prompt,
            db_type=db_type,
            interview_context=interview_context
        )

    raw = await ask_coder(final_prompt)

    try:
        result = parse_json_response(raw)
        files = result.get("files", [])
        tables = result.get("tables", [])

        await emit("stage", f"Database generated — {len(files)} files, {len(tables)} tables")

        return {
            "files": files,
            "tables": tables,
            "summary": result.get("summary", ""),
            "db_type": db_type
        }

    except ValueError as e:
        await emit("error", f"Database generation failed: {str(e)}")
        # Return minimal fallback
        return {
            "files": [],
            "tables": [],
            "summary": "Generation failed",
            "db_type": db_type,
            "error": str(e)
        }
