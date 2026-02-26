import json
from backend.llm.ollama_client import ask_coder, unload_model, parse_json_response

SIMPLE_PLAN_PROMPT = """Analyze this web app and return ONLY JSON, no explanation:

Request: "{prompt}"

Return exactly this structure:
{{"complexity":"simple","app_type":"short description","tables":["table1","table2"],"endpoints":["/api/route1","/api/route2"],"pages":["Page1","Page2"],"auth_needed":true,"db_type":"sqlite"}}"""

async def build_project_plan(prompt: str, websocket=None) -> dict:
    async def emit(event: str, message: str, data: dict = None):
        if websocket:
            await websocket.send_json({"event": event, "message": message, "data": data or {}})

    await emit("interview", "Planning app structure...")

    raw = await ask_coder(SIMPLE_PLAN_PROMPT.format(prompt=prompt))

    try:
        plan_data = parse_json_response(raw)
    except Exception:
        plan_data = {"complexity":"simple","app_type":"web app","tables":["users","items"],"endpoints":["/api/items"],"pages":["Home","Dashboard"],"auth_needed":True,"db_type":"sqlite"}

    await emit("thinking", f"Tables: {', '.join(plan_data.get('tables', []))}")
    await emit("thinking", f"Pages: {', '.join(plan_data.get('pages', []))}")

    return {
        "prompt": prompt,
        "complexity": "simple",
        "needs_modules": False,
        "modules": [],
        "interview": {
            "main": {
                "full_context": f"App: {prompt}\nTables: {', '.join(plan_data.get('tables',[]))}\nEndpoints: {', '.join(plan_data.get('endpoints',[]))}\nPages: {', '.join(plan_data.get('pages',[]))}\nAuth: {plan_data.get('auth_needed',True)}",
                "questions": [],
                "answers": plan_data
            }
        },
        "tech_stack": {
            "frontend": {"framework":"react","styling":"tailwindcss","state":"useState","routing":"react-router-dom"},
            "backend": {"framework":"fastapi","language":"python","auth":"jwt"},
            "database": {"type":"sqlite","orm":"sqlalchemy"},
            "extra": []
        }
    }
