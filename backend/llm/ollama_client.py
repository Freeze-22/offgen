import httpx
import json
import asyncio
import re
from typing import AsyncGenerator

OLLAMA_URL = "http://localhost:11434"

PLANNER_MODEL = "phi3:mini"
CODER_MODEL   = "qwen2.5-coder:1.5b"


async def unload_model(model: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{OLLAMA_URL}/api/generate", json={
                "model": model,
                "keep_alive": 0
            }, timeout=10)
        except Exception:
            pass


async def ask_planner(prompt: str, system: str = "") -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(f"{OLLAMA_URL}/api/generate", json={
            "model": PLANNER_MODEL,
            "prompt": prompt,
            "system": system or "You are an expert software architect. Think carefully and respond concisely.",
            "stream": False,
            "keep_alive": "5m"
        })
        data = response.json()
        return data.get("response", "")


async def ask_coder(prompt: str, system: str = "") -> str:
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(f"{OLLAMA_URL}/api/generate", json={
            "model": CODER_MODEL,
            "prompt": prompt,
            "system": system or (
                "You are an expert full stack developer. "
                "You output ONLY valid JSON. No explanation. No markdown. No backticks. "
                "Use double quotes for ALL strings including multiline code. "
                "Escape newlines as \\n inside JSON strings. "
                "Just raw JSON that can be parsed directly."
            ),
            "stream": False,
            "keep_alive": "5m",
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 4096
            }
        })
        data = response.json()
        return data.get("response", "")


def _fix_backtick_values(s: str) -> str:
    result = []
    i = 0
    while i < len(s):
        if s[i] == '`':
            end = s.find('`', i + 1)
            if end != -1:
                content = s[i+1:end]
                content = content.replace('\\', '\\\\')
                content = content.replace('"', '\\"')
                content = content.replace('\n', '\\n')
                content = content.replace('\r', '\\r')
                content = content.replace('\t', '\\t')
                result.append('"' + content + '"')
                i = end + 1
                continue
        result.append(s[i])
        i += 1
    return ''.join(result)


def parse_json_response(raw: str) -> dict:
    import re
    raw = raw.strip()

    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    fixed = _fix_backtick_values(raw)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        chunk = raw[start:end]
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(_fix_backtick_values(chunk))
        except json.JSONDecodeError:
            pass

    path_matches = re.findall(r'"path"\s*:\s*["`]([^"`\n]+)["`]', raw)
    content_matches = re.findall(r'"content"\s*:\s*`(.*?)`', raw, re.DOTALL)

    if path_matches and content_matches:
        files = []
        for i, path in enumerate(path_matches):
            content = content_matches[i] if i < len(content_matches) else ""
            files.append({"path": path, "content": content})
        return {"files": files, "summary": "Extracted via fallback parser"}

    raise ValueError(f"Could not parse JSON from response: {raw[:300]}...")


async def check_ollama_running() -> bool:
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            return response.status_code == 200
        except Exception:
            return False


async def list_available_models() -> list[str]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []
