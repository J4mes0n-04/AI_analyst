"""Traceability matrix: business → user/system requirements → use cases / tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MatrixRow:
    """Single row in the traceability matrix."""

    row_id: str
    business_req_id: str
    business_text: str
    user_req_ids: list[str] = field(default_factory=list)
    system_req_ids: list[str] = field(default_factory=list)
    use_case_ids: list[str] = field(default_factory=list)
    test_ids: list[str] = field(default_factory=list)
    status: str = "draft"  # draft | reviewed | approved
    notes: str = ""


class TraceabilityMatrix:
    """Maintains bidirectional trace links for requirements engineering."""

    def __init__(self) -> None:
        self._rows: dict[str, MatrixRow] = {}

    def add_row(
        self,
        business_text: str,
        business_req_id: str | None = None,
        **kwargs: Any,
    ) -> MatrixRow:
        rid = business_req_id or f"BR-{uuid.uuid4().hex[:8].upper()}"
        row_id = str(uuid.uuid4())
        row = MatrixRow(
            row_id=row_id,
            business_req_id=rid,
            business_text=business_text,
            user_req_ids=list(kwargs.get("user_req_ids", [])),
            system_req_ids=list(kwargs.get("system_req_ids", [])),
            use_case_ids=list(kwargs.get("use_case_ids", [])),
            test_ids=list(kwargs.get("test_ids", [])),
            status=str(kwargs.get("status", "draft")),
            notes=str(kwargs.get("notes", "")),
        )
        self._rows[row_id] = row
        return row

    def update_row(self, row_id: str, **fields: Any) -> MatrixRow | None:
        row = self._rows.get(row_id)
        if not row:
            return None
        for k, v in fields.items():
            if hasattr(row, k) and k != "row_id":
                setattr(row, k, v)
        return row

    def remove_row(self, row_id: str) -> bool:
        return self._rows.pop(row_id, None) is not None

    def rows(self) -> list[MatrixRow]:
        return list(self._rows.values())

    def to_serializable(self) -> list[dict[str, Any]]:
        return [
            {
                "row_id": r.row_id,
                "business_req_id": r.business_req_id,
                "business_text": r.business_text,
                "user_req_ids": r.user_req_ids,
                "system_req_ids": r.system_req_ids,
                "use_case_ids": r.use_case_ids,
                "test_ids": r.test_ids,
                "status": r.status,
                "notes": r.notes,
            }
            for r in self._rows.values()
        ]

    def from_serializable(self, data: list[dict[str, Any]]) -> None:
        self._rows.clear()
        for d in data:
            row = MatrixRow(
                row_id=d["row_id"],
                business_req_id=d.get("business_req_id", ""),
                business_text=d.get("business_text", ""),
                user_req_ids=list(d.get("user_req_ids", [])),
                system_req_ids=list(d.get("system_req_ids", [])),
                use_case_ids=list(d.get("use_case_ids", [])),
                test_ids=list(d.get("test_ids", [])),
                status=d.get("status", "draft"),
                notes=d.get("notes", ""),
            )
            self._rows[row.row_id] = row

    def sync_from_analysis(self, analysis: dict[str, Any]) -> int:
        """Append matrix rows from use case analysis (by goal/source)."""
        added = 0
        for uc in analysis.get("use_cases", []):
            goal = uc.get("goal") or uc.get("name", "")
            uc_id = uc.get("id", "")
            if not goal:
                continue
            # avoid duplicate by same uc_id linked
            existing = [r for r in self._rows.values() if uc_id in r.use_case_ids]
            if existing:
                continue
            self.add_row(
                business_text=goal[:500],
                business_req_id=None,
                use_case_ids=[uc_id] if uc_id else [],
            )
            added += 1
        return added
