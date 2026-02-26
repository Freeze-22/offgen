"""
Stage 4 — Frontend Generator
------------------------------
Generates React frontend using API spec as context.
Never uses full backend code — only the API spec.
This keeps context small and focused.
"""

from backend.llm.ollama_client import ask_coder, parse_json_response


FRONTEND_PROMPT = """
Generate a React frontend for this web app.

App: {prompt}

Backend API endpoints available:
{api_spec}

Planning context:
{interview_context}

Return ONLY valid JSON:
{{
  "files": [
    {{
      "path": "frontend/src/App.jsx",
      "content": "..."
    }},
    {{
      "path": "frontend/src/pages/[Page].jsx",
      "content": "..."
    }},
    {{
      "path": "frontend/src/api/client.js",
      "content": "..."
    }},
    {{
      "path": "frontend/package.json",
      "content": "..."
    }},
    {{
      "path": "frontend/index.html",
      "content": "..."
    }},
    {{
      "path": "frontend/vite.config.js",
      "content": "..."
    }},
    {{
      "path": "frontend/tailwind.config.js",
      "content": "..."
    }}
  ],
  "pages": ["list", "of", "page", "names"],
  "summary": "what was generated"
}}

Requirements:
- React 18 with hooks (useState, useEffect, useContext)
- React Router DOM for navigation
- TailwindCSS for styling
- Axios for API calls (base URL http://localhost:8000)
- JWT token stored in localStorage
- Clean, modern UI
- Vite as build tool
- Responsive design
"""

FRONTEND_MODULE_PROMPT = """
Generate React pages for the {module_name} module.

App: {prompt}

API endpoints for this module:
{module_endpoints}

Existing pages already built: {existing_pages}

Return ONLY valid JSON:
{{
  "files": [
    {{
      "path": "frontend/src/pages/{ModuleName}Page.jsx",
      "content": "..."
    }}
  ],
  "pages": ["{module_name}"],
  "summary": "what was generated"
}}

Use Tailwind for styling. Import axios from existing api/client.js.
"""


def _format_api_spec(api_spec: dict) -> str:
    """Format API spec as readable string for prompt."""
    endpoints = api_spec.get("endpoints", [])
    if not endpoints:
        return "No endpoints defined yet."

    lines = []
    for ep in endpoints:
        lines.append(f"{ep.get('method', 'GET')} {ep.get('path', '/')} — {ep.get('description', '')}")

    return "\n".join(lines)


async def generate_frontend(plan: dict, backend_result: dict, websocket=None) -> dict:
    """Generate React frontend from plan + backend API spec."""

    async def emit(event: str, message: str):
        if websocket:
            await websocket.send_json({"event": event, "message": message})

    await emit("stage", "Generating frontend...")

    prompt = plan["prompt"]
    needs_modules = plan.get("needs_modules", False)
    modules = plan.get("modules", [])
    api_spec = backend_result.get("api_spec", {"endpoints": []})
    api_spec_str = _format_api_spec(api_spec)

    all_files = []
    all_pages = []

    if needs_modules and modules:
        # Generate base app structure first
        await emit("stage", "Generating app shell and routing...")

        base_raw = await ask_coder(FRONTEND_PROMPT.format(
            prompt=prompt,
            api_spec=api_spec_str[:800],
            interview_context=plan["interview"].get(
                list(plan["interview"].keys())[0], {}
            ).get("full_context", "")[:400]
        ))

        try:
            base_result = parse_json_response(base_raw)
            all_files.extend(base_result.get("files", []))
            all_pages.extend(base_result.get("pages", []))
        except ValueError as e:
            await emit("warning", f"Base frontend failed: {str(e)}")

        # Generate per module pages
        existing_pages = list(all_pages)
        for module in modules:
            await emit("stage", f"Generating {module['name']} pages...")

            module_endpoints = [
                ep for ep in api_spec.get("endpoints", [])
                if module["name"].lower() in ep.get("path", "").lower()
            ]
            module_ep_str = _format_api_spec({"endpoints": module_endpoints})

            raw = await ask_coder(FRONTEND_MODULE_PROMPT.format(
                module_name=module["name"],
                prompt=prompt,
                module_endpoints=module_ep_str,
                existing_pages=", ".join(existing_pages)
            ))

            try:
                result = parse_json_response(raw)
                all_files.extend(result.get("files", []))
                all_pages.extend(result.get("pages", []))
                existing_pages.extend(result.get("pages", []))
            except ValueError as e:
                await emit("warning", f"Module {module['name']} frontend failed: {str(e)}")

    else:
        # Single pass
        interview_context = plan["interview"].get("main", {}).get("full_context", "")[:600]

        raw = await ask_coder(FRONTEND_PROMPT.format(
            prompt=prompt,
            api_spec=api_spec_str[:800],
            interview_context=interview_context
        ))

        try:
            result = parse_json_response(raw)
            all_files = result.get("files", [])
            all_pages = result.get("pages", [])
        except ValueError as e:
            await emit("error", f"Frontend generation failed: {str(e)}")
            return {"files": [], "pages": [], "error": str(e)}

    await emit("stage", f"Frontend generated — {len(all_files)} files, {len(all_pages)} pages")

    return {
        "files": all_files,
        "pages": all_pages
    }
