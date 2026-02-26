import asyncio
import os
from pathlib import Path

PROJECTS_DIR = Path("projects")

running_processes: dict[str, dict] = {}


def get_project_path(project_id: str) -> Path:
    return PROJECTS_DIR / project_id / "current"


async def run_project(project_id: str, websocket=None) -> dict:
    async def emit(event: str, message: str):
        if websocket:
            await websocket.send_json({"event": event, "message": message})

    project_path = Path(f"projects/{project_id}/current")

    await stop_project(project_id)

    backend_path = project_path / "backend"
    frontend_path = project_path / "frontend"

    await emit("running", "Installing backend dependencies...")

    if (backend_path / "requirements.txt").exists():
        proc = await asyncio.create_subprocess_exec(
            "pip", "install", "-r", "requirements.txt", "-q",
            cwd=str(backend_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

    await emit("running", "Starting backend server...")

    env = {**os.environ, "PYTHONPATH": str(backend_path)}

    backend_proc = await asyncio.create_subprocess_exec(
        "python3", "-m", "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", "8001",
        cwd=str(backend_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )

    await asyncio.sleep(3)

    await emit("running", "Installing frontend dependencies...")

    if (frontend_path / "package.json").exists():
        npm_proc = await asyncio.create_subprocess_exec(
            "npm", "install", "--silent",
            cwd=str(frontend_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await npm_proc.communicate()

    await emit("running", "Starting frontend...")

    frontend_proc = await asyncio.create_subprocess_exec(
        "npm", "run", "dev", "--", "--host", "--port", "3000",
        cwd=str(frontend_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    running_processes[project_id] = {
        "backend": backend_proc,
        "frontend": frontend_proc,
        "backend_port": 8001,
        "frontend_port": 3000
    }

    await asyncio.sleep(3)
    await emit("ready", "Project is running!")

    return {
        "frontend_url": "http://localhost:3000",
        "backend_url": "http://localhost:8001",
        "api_docs_url": "http://localhost:8001/docs"
    }


async def stop_project(project_id: str):
    if project_id not in running_processes:
        return
    procs = running_processes[project_id]
    for key in ["backend", "frontend"]:
        proc = procs.get(key)
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                proc.kill()
    del running_processes[project_id]


async def get_project_status(project_id: str) -> dict:
    if project_id not in running_processes:
        return {"running": False}
    procs = running_processes[project_id]
    return {
        "running": True,
        "frontend_url": "http://localhost:3000",
        "backend_url": "http://localhost:8001"
    }
