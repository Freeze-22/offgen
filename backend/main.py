import uuid
import asyncio
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

from backend.pipeline.interviewer import build_project_plan
from backend.pipeline.database_gen import generate_database
from backend.pipeline.backend_gen import generate_backend
from backend.pipeline.frontend_gen import generate_frontend
from backend.pipeline.infra_gen import generate_infra
from backend.storage.file_writer import (
    write_files, get_file_tree, read_file,
    snapshot_version, restore_version, list_versions,
    init_project, update_project_meta, get_project_meta,
    get_all_files_content
)
from backend.execution.runner import run_project, stop_project, get_project_status
from backend.iteration.change_analyzer import (
    analyze_change, select_relevant_files, format_relevant_files,
    CONTEXT_BUILD_PROMPT
)
from backend.llm.ollama_client import (
    check_ollama_running, list_available_models,
    ask_coder, parse_json_response, unload_model
)

app = FastAPI(title="OffRepl API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    ollama_ok = await check_ollama_running()
    models = await list_available_models() if ollama_ok else []
    return {"status": "ok", "ollama": ollama_ok, "models": models}

@app.get("/projects")
async def list_projects():
    projects_dir = Path("projects")
    if not projects_dir.exists():
        return []
    projects = []
    for project_dir in sorted(projects_dir.iterdir(), reverse=True):
        meta = get_project_meta(project_dir.name)
        if meta:
            projects.append({"id": project_dir.name, **meta})
    return projects

@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    meta = get_project_meta(project_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"id": project_id, **meta}

@app.get("/projects/{project_id}/files")
async def get_files(project_id: str):
    return get_file_tree(project_id)

@app.get("/projects/{project_id}/files/{file_path:path}")
async def get_file(project_id: str, file_path: str):
    content = read_file(project_id, file_path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": file_path, "content": content}

@app.get("/projects/{project_id}/versions")
async def get_versions(project_id: str):
    return list_versions(project_id)

class RestoreRequest(BaseModel):
    version: int

@app.post("/projects/{project_id}/restore")
async def restore(project_id: str, req: RestoreRequest):
    ok = restore_version(project_id, req.version)
    if not ok:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"success": True, "version": req.version}

@app.get("/projects/{project_id}/status")
async def project_status(project_id: str):
    return await get_project_status(project_id)

@app.post("/projects/{project_id}/stop")
async def stop(project_id: str):
    await stop_project(project_id)
    return {"success": True}

@app.websocket("/ws/generate")
async def generate_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        prompt = data.get("prompt", "").strip()

        if not prompt:
            await websocket.send_json({"event": "error", "message": "Prompt is required"})
            return

        if not await check_ollama_running():
            await websocket.send_json({"event": "error", "message": "Ollama is not running. Start it with: ollama serve"})
            return

        project_id = str(uuid.uuid4())[:8]
        init_project(project_id, {"prompt": prompt, "status": "generating", "version": 0})

        await websocket.send_json({"event": "start", "message": "Starting generation...", "data": {"project_id": project_id}})

        all_files = []

        # Phase 1 - Planning
        print(f"[{project_id}] Starting planning phase...")
        try:
            plan = await build_project_plan(prompt, websocket)
            print(f"[{project_id}] Planning done. Complexity: {plan.get('complexity')}")
        except Exception as e:
            err = traceback.format_exc()
            print(f"[{project_id}] PLANNING ERROR:\n{err}")
            await websocket.send_json({"event": "error", "message": f"Planning failed: {str(e)}"})
            return

        # Stage 2 - Database
        print(f"[{project_id}] Starting database generation...")
        try:
            db_result = await generate_database(plan, websocket)
            all_files.extend(db_result.get("files", []))
            print(f"[{project_id}] DB done. Files: {len(db_result.get('files', []))}")
        except Exception as e:
            err = traceback.format_exc()
            print(f"[{project_id}] DB ERROR:\n{err}")
            db_result = {"files": [], "tables": [], "summary": ""}

        # Stage 3 - Backend
        print(f"[{project_id}] Starting backend generation...")
        try:
            backend_result = await generate_backend(plan, db_result, websocket)
            all_files.extend(backend_result.get("files", []))
            print(f"[{project_id}] Backend done. Files: {len(backend_result.get('files', []))}")
        except Exception as e:
            err = traceback.format_exc()
            print(f"[{project_id}] BACKEND ERROR:\n{err}")
            backend_result = {"files": [], "api_spec": {"endpoints": []}}

        # Stage 4 - Frontend
        print(f"[{project_id}] Starting frontend generation...")
        try:
            frontend_result = await generate_frontend(plan, backend_result, websocket)
            all_files.extend(frontend_result.get("files", []))
            print(f"[{project_id}] Frontend done. Files: {len(frontend_result.get('files', []))}")
        except Exception as e:
            err = traceback.format_exc()
            print(f"[{project_id}] FRONTEND ERROR:\n{err}")
            frontend_result = {"files": [], "pages": []}

        # Stage 5 - Infra
        print(f"[{project_id}] Starting infra generation...")
        try:
            infra_result = await generate_infra(plan, db_result, backend_result, frontend_result, websocket)
            all_files.extend(infra_result.get("files", []))
        except Exception as e:
            print(f"[{project_id}] INFRA ERROR: {str(e)}")
            infra_result = {"files": []}

        # Write files
        await websocket.send_json({"event": "writing", "message": f"Writing {len(all_files)} files..."})
        written = write_files(project_id, all_files)
        print(f"[{project_id}] Written {len(written)} files to disk")

        snapshot_version(project_id, 1)
        update_project_meta(project_id, {
            "status": "ready",
            "version": 1,
            "file_count": len(written),
            "tables": db_result.get("tables", []),
            "endpoints": len(backend_result.get("api_spec", {}).get("endpoints", [])),
            "pages": frontend_result.get("pages", [])
        })

        await websocket.send_json({
            "event": "complete",
            "message": "Project generated successfully!",
            "data": {
                "project_id": project_id,
                "file_count": len(written),
                "files": get_file_tree(project_id)
            }
        })

        await unload_model("qwen2.5-coder:1.5b")

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        err = traceback.format_exc()
        print(f"GENERATION ERROR:\n{err}")
        try:
            await websocket.send_json({"event": "error", "message": f"Generation failed: {str(e)}"})
        except:
            pass

@app.websocket("/ws/iterate/{project_id}")
async def iterate_ws(websocket: WebSocket, project_id: str):
    await websocket.accept()
    try:
        meta = get_project_meta(project_id)
        if not meta:
            await websocket.send_json({"event": "error", "message": "Project not found"})
            return

        data = await websocket.receive_json()
        change_request = data.get("change", "").strip()

        if not change_request:
            await websocket.send_json({"event": "error", "message": "Change request is required"})
            return

        original_prompt = meta.get("prompt", "")
        current_version = meta.get("version", 1)

        await websocket.send_json({"event": "analyzing", "message": "Analyzing what needs to change..."})

        analysis = await analyze_change(original_prompt, change_request)
        affected = analysis.get("affected_layers", ["backend", "frontend"])

        await websocket.send_json({"event": "analysis", "message": f"Affected: {', '.join(affected)}", "data": analysis})

        all_files = get_all_files_content(project_id)
        relevant = select_relevant_files(all_files, affected, change_request)
        relevant_str = format_relevant_files(relevant)

        await websocket.send_json({"event": "generating", "message": "Generating changes..."})

        raw = await ask_coder(CONTEXT_BUILD_PROMPT.format(
            change_request=change_request,
            affected_layers=", ".join(affected),
            relevant_files=relevant_str
        ))

        try:
            result = parse_json_response(raw)
            new_files = result.get("files", [])

            new_version = current_version + 1
            snapshot_version(project_id, current_version)
            written = write_files(project_id, new_files)

            update_project_meta(project_id, {"version": new_version, "last_change": change_request})

            await websocket.send_json({
                "event": "complete",
                "message": f"Changes applied — {len(written)} files updated",
                "data": {"changed_files": written, "version": new_version, "files": get_file_tree(project_id)}
            })
        except ValueError as e:
            await websocket.send_json({"event": "error", "message": f"Failed to parse changes: {str(e)}"})

        await unload_model("qwen2.5-coder:1.5b")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        err = traceback.format_exc()
        print(f"ITERATION ERROR:\n{err}")
        try:
            await websocket.send_json({"event": "error", "message": f"Iteration failed: {str(e)}"})
        except:
            pass

@app.websocket("/ws/run/{project_id}")
async def run_ws(websocket: WebSocket, project_id: str):
    await websocket.accept()
    try:
        result = await run_project(project_id, websocket)
        await websocket.send_json({"event": "running", "message": "Project is live!", "data": result})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"event": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
