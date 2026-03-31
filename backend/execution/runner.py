import asyncio
import os
import subprocess
from pathlib import Path

running_processes: dict[str, dict] = {}


async def run_project(project_id: str, websocket=None) -> dict:
    async def emit(event: str, message: str):
        if websocket:
            await websocket.send_json({"event": event, "message": message})

    project_path = Path(f"projects/{project_id}/current")
    backend_path = project_path / "backend"
    frontend_path = project_path / "frontend"

    await stop_project(project_id)

    # Install backend deps synchronously (wait for it to fully finish)
    if (backend_path / "requirements.txt").exists():
        await emit("running", "Installing backend dependencies...")
        result = subprocess.run(
            ["pip", "install", "-r", "requirements.txt", "-q"],
            cwd=str(backend_path),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            await emit("running", f"pip warning: {result.stderr[:100]}")

    # Create .env if not exists
    env_example = project_path / ".env.example"
    env_file = project_path / ".env"
    if env_example.exists() and not env_file.exists():
        env_file.write_text(env_example.read_text())

    await emit("running", "Starting backend server...")

    env = {
        **os.environ,
        "PYTHONPATH": str(backend_path),
        "DATABASE_URL": f"sqlite:///{backend_path}/app.db"
    }

    backend_proc = await asyncio.create_subprocess_exec(
        "python3", "-m", "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", "8001",
        cwd=str(backend_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )

    # Wait and check if backend started successfully
    await asyncio.sleep(4)

    if backend_proc.returncode is not None:
        stderr = await backend_proc.stderr.read()
        await emit("running", f"Backend error: {stderr.decode()[:200]}")
    else:
        await emit("running", "Backend started successfully!")

    # Install frontend deps synchronously
    if (frontend_path / "package.json").exists():
        await emit("running", "Installing frontend dependencies...")
        result = subprocess.run(
            ["npm", "install", "--silent"],
            cwd=str(frontend_path),
            capture_output=True,
            text=True
        )

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
    backend_running = procs["backend"].returncode is None
    frontend_running = procs["frontend"].returncode is None
    return {
        "running": backend_running or frontend_running,
        "frontend_url": "http://localhost:3000",
        "backend_url": "http://localhost:8001"
    }
