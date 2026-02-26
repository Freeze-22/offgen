"""
Stage 3 — Backend Generator
-----------------------------
Generates FastAPI backend using the database models as context.
Returns API routes, business logic, auth middleware.
"""

from backend.llm.ollama_client import ask_coder, parse_json_response


BACKEND_PROMPT = """
Generate a FastAPI backend for this web app.

App: {prompt}

Database models already generated:
{models_content}

Planning context:
{interview_context}

Return ONLY valid JSON:
{{
  "files": [
    {{
      "path": "backend/main.py",
      "content": "..."
    }},
    {{
      "path": "backend/routes/auth.py",
      "content": "..."
    }},
    {{
      "path": "backend/routes/[entity].py",
      "content": "..."
    }},
    {{
      "path": "backend/core/security.py",
      "content": "..."
    }},
    {{
      "path": "backend/requirements.txt",
      "content": "..."
    }}
  ],
  "api_spec": {{
    "endpoints": [
      {{
        "method": "GET",
        "path": "/api/v1/endpoint",
        "description": "what it does"
      }}
    ]
  }},
  "summary": "what was generated"
}}

Requirements:
- FastAPI with proper router organization
- JWT authentication (if auth needed)
- CORS configured for localhost:5173
- Pydantic validation using schemas from models
- Proper HTTP status codes
- Error handling with HTTPException
- Environment variables via python-dotenv
"""


BACKEND_MODULE_PROMPT = """
Generate FastAPI routes for the {module_name} module.

App: {prompt}

Existing database models:
{models_content}

This module's planning:
{module_context}

Already generated modules: {existing_modules}

Return ONLY valid JSON:
{{
  "files": [
    {{
      "path": "backend/routes/{module_name}.py",
      "content": "..."
    }}
  ],
  "api_spec": {{
    "endpoints": []
  }},
  "summary": "what was generated"
}}

Import from existing models. Don't regenerate models.
"""


async def generate_backend(plan: dict, db_result: dict, websocket=None) -> dict:
    """Generate backend API from plan + database layer."""

    async def emit(event: str, message: str):
        if websocket:
            await websocket.send_json({"event": event, "message": message})

    await emit("stage", "Generating backend API...")

    prompt = plan["prompt"]
    needs_modules = plan.get("needs_modules", False)
    modules = plan.get("modules", [])

    # Get models content for context
    models_content = ""
    for f in db_result.get("files", []):
        if "models.py" in f["path"] or "schemas.py" in f["path"]:
            models_content += f"\n# {f['path']}\n{f['content'][:800]}\n"

    # Trim to avoid token overflow
    models_content = models_content[:1500]

    all_files = []
    all_endpoints = []

    if needs_modules and modules:
        # Generate per module
        existing_modules = []
        for module in modules:
            await emit("stage", f"Generating {module['name']} backend routes...")

            module_context = plan["interview"].get(module["name"], {}).get("full_context", "")[:500]

            raw = await ask_coder(BACKEND_MODULE_PROMPT.format(
                module_name=module["name"],
                prompt=prompt,
                models_content=models_content,
                module_context=module_context,
                existing_modules=", ".join(existing_modules)
            ))

            try:
                result = parse_json_response(raw)
                all_files.extend(result.get("files", []))
                all_endpoints.extend(result.get("api_spec", {}).get("endpoints", []))
                existing_modules.append(module["name"])
            except ValueError as e:
                await emit("warning", f"Module {module['name']} backend failed: {str(e)}")

        # Generate main.py that imports all modules
        main_py = _generate_main_py(modules)
        requirements_txt = _generate_requirements()
        all_files.append({"path": "backend/main.py", "content": main_py})
        all_files.append({"path": "backend/requirements.txt", "content": requirements_txt})

    else:
        # Single pass for simple/medium apps
        interview_context = plan["interview"].get("main", {}).get("full_context", "")[:800]

        raw = await ask_coder(BACKEND_PROMPT.format(
            prompt=prompt,
            models_content=models_content,
            interview_context=interview_context
        ))

        try:
            result = parse_json_response(raw)
            all_files = result.get("files", [])
            all_endpoints = result.get("api_spec", {}).get("endpoints", [])
        except ValueError as e:
            await emit("error", f"Backend generation failed: {str(e)}")
            return {"files": [], "api_spec": {"endpoints": []}, "error": str(e)}

    await emit("stage", f"Backend generated — {len(all_files)} files, {len(all_endpoints)} endpoints")

    return {
        "files": all_files,
        "api_spec": {"endpoints": all_endpoints}
    }


def _generate_main_py(modules: list[dict]) -> str:
    """Generate main.py that wires all module routers."""
    imports = "\n".join([
        f"from backend.routes.{m['name']} import router as {m['name']}_router"
        for m in modules
    ])
    includes = "\n".join([
        f"app.include_router({m['name']}_router, prefix='/api/v1/{m['name']}', tags=['{m['name']}'])"
        for m in modules
    ])

    return f"""from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database.database import engine, Base
{imports}

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Generated App", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

{includes}

@app.get("/health")
def health():
    return {{"status": "ok"}}
"""


def _generate_requirements() -> str:
    return """fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
python-multipart==0.0.6
aiofiles==23.2.1
"""
