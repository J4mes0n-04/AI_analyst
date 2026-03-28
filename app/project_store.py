"""Project persistence (JSON) and autosave paths."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def app_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / "AI_Analyst"
    return Path.home() / ".local" / "share" / "AI_Analyst"


@dataclass
class ProjectData:
    """In-memory project model shared across modules."""

    business_text: str = ""
    analysis: dict[str, Any] = field(default_factory=dict)
    matrix_rows: list[dict[str, Any]] = field(default_factory=list)
    converter_input: str = ""
    converter_source: str = "text"
    converter_target: str = "user_stories"
    priority_items: list[dict[str, Any]] = field(default_factory=list)
    file_path: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "business_text": self.business_text,
            "analysis": self.analysis,
            "matrix_rows": self.matrix_rows,
            "converter_input": self.converter_input,
            "converter_source": self.converter_source,
            "converter_target": self.converter_target,
            "priority_items": self.priority_items,
        }

    @classmethod
    def from_json_dict(cls, d: dict[str, Any]) -> ProjectData:
        p = cls()
        p.business_text = d.get("business_text", "")
        p.analysis = d.get("analysis") or {}
        p.matrix_rows = d.get("matrix_rows") or []
        p.converter_input = d.get("converter_input", "")
        p.converter_source = d.get("converter_source", "text")
        p.converter_target = d.get("converter_target", "user_stories")
        p.priority_items = d.get("priority_items") or []
        return p


def save_project(path: str | Path, data: ProjectData) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = data.to_json_dict()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    data.file_path = str(path)


def load_project(path: str | Path) -> ProjectData:
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    d = json.loads(raw)
    p = ProjectData.from_json_dict(d)
    p.file_path = str(path)
    return p


def autosave_path() -> Path:
    d = app_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "autosave.json"


def save_autosave(data: ProjectData) -> None:
    try:
        save_project(autosave_path(), data)
    except OSError:
        pass


def load_autosave() -> ProjectData | None:
    p = autosave_path()
    if not p.is_file():
        return None
    try:
        return load_project(p)
    except (OSError, json.JSONDecodeError):
        return None
