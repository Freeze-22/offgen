"""
Process Runner
--------------
Runs generated projects directly (no Docker needed).
Starts backend with uvicorn and frontend with vite.
Designed for Dell laptop with limited RAM.
"""

import asyncio
import subprocess
import os
import signal
from pathlib import Path
from backend.storage.file_writer import get_project_path


# Track running processes per project
running_processes: dict[str, dict] = {}


async def run_project(project_id: str, websocket=None) -> dict:
    """
    Start the generated project.
    Returns ports where it's running.
    """

    async def emit(event: str, message: str):
        if websocket:
            await websocket.send_json({"event": event, "message": message})

    project_path = get_project_path(project_id)

    # Stop any existing process for this project
    await stop_project(project_id)

    await emit("running", "Installing backend dependencies...")

    backend_path = project_path / "backend"
    frontend_path = project_path / "frontend"

    # Install Python deps
    if (backend_path / "requirements.txt").exists():
        proc = await asyncio.create_subprocess_exec(
            "pip", "install", "-r", "requirements.txt", "--quiet",
            cwd=backend_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

    await emit("running", "Starting backend server...")

    # Start FastAPI backend
    backend_proc = await asyncio.create_subprocess_exec(
        "python", "-m", "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
        cwd=backend_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": str(backend_path)}
    )

    # Wait a bit for backend to start
    await asyncio.sleep(2)

    await emit("running", "Installing frontend dependencies...")

    # Install Node deps
    if (frontend_path / "package.json").exists():
        npm_proc = await asyncio.create_subprocess_exec(
            "npm", "install", "--silent",
            cwd=frontend_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await npm_proc.communicate()

    await emit("running", "Starting frontend dev server...")

    # Start React frontend
    frontend_proc = await asyncio.create_subprocess_exec(
        "npm", "run", "dev", "--", "--host", "--port", "5173",
        cwd=frontend_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Store process references
    running_processes[project_id] = {
        "backend": backend_proc,
        "frontend": frontend_proc,
        "backend_port": 8000,
        "frontend_port": 5173
    }

    await asyncio.sleep(2)

    await emit("ready", "Project is running!")

    return {
        "frontend_url": "http://localhost:5173",
        "backend_url": "http://localhost:8000",
        "api_docs_url": "http://localhost:8000/docs"
    }


async def stop_project(project_id: str):
    """Stop all running processes for a project."""
    if project_id not in running_processes:
        return

    procs = running_processes[project_id]

    for key in ["backend", "frontend"]:
        proc = procs.get(key)
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
            except Exception:
                pass

    del running_processes[project_id]


async def get_project_status(project_id: str) -> dict:
    """Check if project processes are running."""
    if project_id not in running_processes:
        return {"running": False}

    procs = running_processes[project_id]
    backend_running = procs["backend"].returncode is None
    frontend_running = procs["frontend"].returncode is None

    return {
        "running": backend_running or frontend_running,
        "backend": {"running": backend_running, "port": procs.get("backend_port", 8000)},
        "frontend": {"running": frontend_running, "port": procs.get("frontend_port", 5173)},
        "frontend_url": "http://localhost:5173",
        "backend_url": "http://localhost:8000"
    }


async def get_logs(project_id: str, service: str = "backend", lines: int = 50) -> list[str]:
    """Get recent logs from a running service."""
    if project_id not in running_processes:
        return []

    procs = running_processes[project_id]
    proc = procs.get(service)

    if not proc or proc.stdout is None:
        return []

    try:
        # Read available output without blocking
        output = []
        while True:
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=0.1)
                if line:
                    output.append(line.decode("utf-8", errors="ignore").strip())
                else:
                    break
            except asyncio.TimeoutError:
                break

        return output[-lines:]
    except Exception:
        return []
