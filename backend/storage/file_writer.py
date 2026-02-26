"""
File Writer
-----------
Takes list of {path, content} and writes them to the project directory.
Handles directory creation, file overwriting, and tracking.
"""

import os
import json
from pathlib import Path
from datetime import datetime


PROJECTS_DIR = Path("projects")


def get_project_path(project_id: str) -> Path:
    return PROJECTS_DIR / project_id / "current"


def get_version_path(project_id: str, version: int) -> Path:
    return PROJECTS_DIR / project_id / f"v{version}"


def write_files(project_id: str, files: list[dict]) -> list[str]:
    """
    Write list of files to project directory.
    files: [{"path": "relative/path.py", "content": "..."}]
    Returns list of written file paths.
    """
    project_path = get_project_path(project_id)
    written = []

    for file_info in files:
        rel_path = file_info.get("path", "")
        content = file_info.get("content", "")

        if not rel_path or not content:
            continue

        # Security: prevent path traversal
        full_path = (project_path / rel_path).resolve()
        if not str(full_path).startswith(str(project_path.resolve())):
            continue

        # Create directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        full_path.write_text(content, encoding="utf-8")
        written.append(rel_path)

    return written


def read_file(project_id: str, file_path: str) -> str | None:
    """Read a single file from the project."""
    full_path = get_project_path(project_id) / file_path
    if full_path.exists():
        return full_path.read_text(encoding="utf-8")
    return None


def get_file_tree(project_id: str) -> list[dict]:
    """
    Get the full file tree of a project.
    Returns nested structure for UI file tree.
    """
    project_path = get_project_path(project_id)
    if not project_path.exists():
        return []

    files = []
    for path in sorted(project_path.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(project_path))
            # Skip hidden files and __pycache__
            if any(part.startswith(".") or part == "__pycache__" for part in path.parts):
                continue
            files.append({
                "path": rel,
                "size": path.stat().st_size,
                "modified": path.stat().st_mtime
            })

    return files


def snapshot_version(project_id: str, version: int):
    """
    Save current project state as a version snapshot.
    Used before applying any changes (for rollback).
    """
    import shutil
    current = get_project_path(project_id)
    version_path = get_version_path(project_id, version)

    if current.exists():
        if version_path.exists():
            shutil.rmtree(version_path)
        shutil.copytree(current, version_path)


def restore_version(project_id: str, version: int) -> bool:
    """Restore project to a previous version."""
    import shutil
    version_path = get_version_path(project_id, version)
    current = get_project_path(project_id)

    if not version_path.exists():
        return False

    if current.exists():
        shutil.rmtree(current)
    shutil.copytree(version_path, current)
    return True


def list_versions(project_id: str) -> list[int]:
    """List all available versions for a project."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return []

    versions = []
    for path in project_dir.iterdir():
        if path.is_dir() and path.name.startswith("v"):
            try:
                versions.append(int(path.name[1:]))
            except ValueError:
                pass

    return sorted(versions)


def get_all_files_content(project_id: str, max_size: int = 50000) -> dict[str, str]:
    """
    Get all files and their contents.
    Used by iteration pipeline to build context.
    max_size: total character limit across all files
    """
    project_path = get_project_path(project_id)
    if not project_path.exists():
        return {}

    files = {}
    total_size = 0

    for path in sorted(project_path.rglob("*")):
        if not path.is_file():
            continue
        if any(part.startswith(".") or part == "__pycache__" for part in path.parts):
            continue

        rel = str(path.relative_to(project_path))
        content = path.read_text(encoding="utf-8", errors="ignore")

        if total_size + len(content) > max_size:
            break

        files[rel] = content
        total_size += len(content)

    return files


def init_project(project_id: str, metadata: dict):
    """Initialize a new project directory with metadata."""
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    get_project_path(project_id).mkdir(parents=True, exist_ok=True)

    # Save metadata
    meta_file = project_dir / "meta.json"
    meta_file.write_text(json.dumps({
        **metadata,
        "created_at": datetime.now().isoformat(),
        "version": 0
    }, indent=2))


def update_project_meta(project_id: str, updates: dict):
    """Update project metadata."""
    project_dir = PROJECTS_DIR / project_id
    meta_file = project_dir / "meta.json"

    if meta_file.exists():
        meta = json.loads(meta_file.read_text())
    else:
        meta = {}

    meta.update(updates)
    meta_file.write_text(json.dumps(meta, indent=2))


def get_project_meta(project_id: str) -> dict | None:
    """Get project metadata."""
    meta_file = PROJECTS_DIR / project_id / "meta.json"
    if meta_file.exists():
        return json.loads(meta_file.read_text())
    return None
