# OffRepl — Offline AI Project Generator

> Describe your web app. Get full stack code. No internet needed.

Like Bolt.new / Replit — but fully offline on your own machine.

---

## What It Does

1. You type a prompt: *"build a todo app with user auth"*
2. It thinks and plans (Phi-3 Mini)
3. It generates full stack code (Qwen2.5-Coder)
4. You get a complete React + FastAPI + SQLite project
5. Click Run → your app is live at localhost:5173
6. Keep refining: *"add dark mode"*, *"add search"*, unlimited times

---

## Stack

**Your tool (OffRepl itself):**
- Frontend: React + TailwindCSS + Vite
- Backend: FastAPI + WebSockets
- LLM: Ollama (Phi-3 Mini + Qwen2.5-Coder 1.5B)
- Storage: JSON files (no DB needed)

**What it generates:**
- Frontend: React + TailwindCSS
- Backend: FastAPI (Python)
- Database: SQLite (or PostgreSQL)
- Infra: docker-compose + startup scripts

---

## Requirements

- Ubuntu 22.04
- Python 3.10+
- Node.js 18+
- 8GB RAM (minimum)
- Ollama

---

## Quick Start

```bash
chmod +x start.sh
./start.sh
```

That's it. Script handles everything:
- Installs Ollama
- Downloads models
- Installs dependencies
- Starts backend + frontend

Open http://localhost:5173

---

## Manual Setup

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Models:**
```bash
ollama pull phi3:mini
ollama pull qwen2.5-coder:1.5b
```

---

## Hardware Guide

| Machine | Model | Speed |
|---|---|---|
| Dell i5 8GB (your laptop) | qwen2.5-coder:1.5b | slow but works |
| ASUS i7 16GB GTX1650 | qwen2.5-coder:3b | good |
| RTX 3060 12GB | qwen2.5-coder:14b | fast + high quality |

To change model, edit `backend/llm/ollama_client.py`:
```python
CODER_MODEL = "qwen2.5-coder:1.5b"  # change this
```

---

## Network Access (Tailscale)

To access from another laptop on a different network:

```bash
# Install Tailscale on both machines
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up

# Backend is now accessible at:
# http://<tailscale-ip>:8000
# http://<tailscale-ip>:5173
```

---

## Project Structure

```
offrepl/
  frontend/          ← React UI (this tool's interface)
  backend/
    main.py          ← FastAPI + WebSocket server
    pipeline/
      interviewer.py ← Phi-3 self-interview (planning)
      database_gen.py← Stage 2: DB generation
      backend_gen.py ← Stage 3: API generation
      frontend_gen.py← Stage 4: UI generation
      infra_gen.py   ← Stage 5: docker/env/readme
    iteration/
      change_analyzer.py ← What changed?
    storage/
      file_writer.py ← File I/O + versioning
    execution/
      runner.py      ← Run generated projects
    llm/
      ollama_client.py ← Ollama API wrapper
  projects/          ← Generated projects stored here
  start.sh           ← One-command startup
```

---

## Research Paper References

- MetaGPT: Multi-Agent Collaborative Framework (arxiv:2308.00352)
- ChatDev: Communicative Agents for Software Dev (arxiv:2307.07924)
- Self-Planning Code Generation with LLMs (ACM 2024)
- Qwen2.5-Coder Technical Report (arxiv:2409.12186)
- SWE-bench: Evaluating LMs on Real Engineering (arxiv:2310.06770)

---

*Built for IEEE research paper on offline AI-powered full-stack code generation*
