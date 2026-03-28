"""Convert requirements between plain text, user stories, and functional specs."""

from __future__ import annotations

import re
from typing import Literal

FormatKind = Literal["text", "user_stories", "functional"]


class RequirementConverter:
    """Universal converter between supported requirement representations."""

    def convert(self, content: str, source: FormatKind, target: FormatKind) -> str:
        if source == target:
            return content
        if source == "text":
            blocks = self._split_blocks(content)
            if target == "user_stories":
                return self._text_to_stories(blocks)
            if target == "functional":
                return self._text_to_functional(blocks)
        if source == "user_stories":
            stories = self._parse_stories(content)
            if target == "text":
                return self._stories_to_text(stories)
            if target == "functional":
                return self._stories_to_functional(stories)
        if source == "functional":
            items = self._parse_functional(content)
            if target == "text":
                return self._functional_to_text(items)
            if target == "user_stories":
                return self._functional_to_stories(items)
        return content

    @staticmethod
    def _split_blocks(text: str) -> list[str]:
        parts = re.split(r"\n\s*\n+", (text or "").strip())
        return [p.strip() for p in parts if p.strip()] or ([text.strip()] if text.strip() else [])

    def _text_to_stories(self, blocks: list[str]) -> str:
        lines: list[str] = []
        for i, b in enumerate(blocks, start=1):
            role = "пользователь"
            benefit = b[:120] + ("…" if len(b) > 120 else "")
            lines.append(f"US-{i:03d}: Как {role}, я хочу <цель>, чтобы {benefit}.")
            lines.append(f"  Критерии приёмки: определены в исходном требовании #{i}.")
            lines.append("")
        return "\n".join(lines).strip()

    def _text_to_functional(self, blocks: list[str]) -> str:
        lines: list[str] = []
        for i, b in enumerate(blocks, start=1):
            lines.append(f"FR-{i:03d} [Функциональное требование]")
            lines.append(f"  Описание: {b}")
            lines.append("  Входные данные: (уточнить)")
            lines.append("  Обработка: (уточнить)")
            lines.append("  Выходные данные: (уточнить)")
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def _parse_stories(content: str) -> list[dict[str, str]]:
        stories: list[dict[str, str]] = []
        for block in re.split(r"\n\s*\n+", content.strip()):
            m = re.search(
                r"(US-\d{3}|User Story\s*\d+):\s*Как\s+([^,]+),\s*я хочу\s+(.+?),\s*чтобы\s+(.+)",
                block,
                re.IGNORECASE | re.DOTALL,
            )
            if m:
                stories.append(
                    {
                        "id": m.group(1),
                        "role": m.group(2).strip(),
                        "want": m.group(3).strip(),
                        "benefit": m.group(4).strip(),
                        "raw": block,
                    }
                )
            elif block.strip():
                stories.append({"id": f"US-{len(stories)+1:03d}", "role": "", "want": "", "benefit": "", "raw": block})
        return stories

    @staticmethod
    def _stories_to_text(stories: list[dict[str, str]]) -> str:
        return "\n\n".join(s.get("raw") or s.get("benefit", "") for s in stories if s).strip()

    def _stories_to_functional(self, stories: list[dict[str, str]]) -> str:
        lines: list[str] = []
        for i, s in enumerate(stories, start=1):
            lines.append(f"FR-{i:03d} [Из пользовательской истории {s.get('id', '')}]")
            lines.append(f"  Описание: {s.get('want', '') or s.get('raw', '')}")
            lines.append(f"  Обоснование (ценность): {s.get('benefit', '')}")
            lines.append(f"  Актор: {s.get('role', 'не указан')}")
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def _parse_functional(content: str) -> list[str]:
        items: list[str] = []
        current: list[str] = []
        for line in content.splitlines():
            if re.match(r"^FR-\d{3}\b", line.strip()):
                if current:
                    items.append("\n".join(current).strip())
                current = [line]
            elif current:
                current.append(line)
        if current:
            items.append("\n".join(current).strip())
        return items or ([content.strip()] if content.strip() else [])

    @staticmethod
    def _functional_to_text(items: list[str]) -> str:
        return "\n\n".join(items).strip()

    def _functional_to_stories(self, items: list[str]) -> str:
        lines: list[str] = []
        for i, it in enumerate(items, start=1):
            first = it.splitlines()[0] if it else ""
            body = "\n".join(it.splitlines()[1:]).strip() or it
            lines.append(f"US-{i:03d}: Как пользователь, я хочу выполнить функцию, описанную ниже, чтобы достичь цели.")
            lines.append(f"  Исходное ТЗ: {first}")
            lines.append(f"  {body[:400]}{'…' if len(body) > 400 else ''}")
            lines.append("")
        return "\n".join(lines).strip()
