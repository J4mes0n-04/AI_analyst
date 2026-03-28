"""Diagram generation: sequence, state, ER — export PNG / SVG / PDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

DiagramKind = Literal["sequence", "state", "er"]


class RequirementVisualizer:
    """Builds matplotlib-based diagrams from analysis / domain hints."""

    def __init__(self) -> None:
        self._fig_size = (10, 6)
        self._dpi = 120

    def build_sequence(self, analysis: dict[str, Any] | None = None) -> plt.Figure:
        """Simple sequence diagram from primary actor and first use case steps."""
        analysis = analysis or {}
        actors = analysis.get("actors") or ["Пользователь", "Система"]
        if len(actors) < 2:
            actors = ["Пользователь", "Система"]
        a1, a2 = actors[0][:20], actors[1][:20] if len(actors) > 1 else "Система"
        ucs = analysis.get("use_cases") or []
        steps: list[tuple[str, str]] = []
        if ucs:
            for s in ucs[0].get("main_success", [])[:6]:
                steps.append((s.get("actor_action", "?"), s.get("system_response", "?")))
        else:
            steps = [
                (f"{a1}: запрос", f"{a2}: обработка"),
                (f"{a1}: данные", f"{a2}: ответ"),
            ]

        fig, ax = plt.subplots(figsize=self._fig_size, dpi=self._dpi)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis("off")
        ax.set_title("Диаграмма последовательности (черновик)", fontsize=12, pad=12)

        x1, x2 = 2.0, 7.0
        y0 = 9.0
        dy = min(1.2, 7.0 / max(len(steps), 1))
        ax.plot([x1, x1], [1, y0 + 0.3], color="#64748b", linewidth=1)
        ax.plot([x2, x2], [1, y0 + 0.3], color="#64748b", linewidth=1)
        ax.text(x1, y0 + 0.5, a1, ha="center", fontsize=9, fontweight="bold")
        ax.text(x2, y0 + 0.5, a2, ha="center", fontsize=9, fontweight="bold")
        for i, (left, right) in enumerate(steps):
            y = y0 - i * dy
            ax.annotate(
                "",
                xy=(x2 - 0.2, y - 0.1),
                xytext=(x1 + 0.2, y - 0.1),
                arrowprops=dict(arrowstyle="->", color="#2563eb"),
            )
            ax.text((x1 + x2) / 2, y, left[:45], ha="center", va="bottom", fontsize=8)
            y2 = y - dy * 0.35
            ax.annotate(
                "",
                xy=(x1 + 0.2, y2),
                xytext=(x2 - 0.2, y2),
                arrowprops=dict(arrowstyle="->", color="#059669"),
            )
            ax.text((x1 + x2) / 2, y2 - 0.05, right[:45], ha="center", va="top", fontsize=8)
        return fig

    def build_state(self, analysis: dict[str, Any] | None = None) -> plt.Figure:
        """Simple state diagram for a generic requirement lifecycle."""
        fig, ax = plt.subplots(figsize=self._fig_size, dpi=self._dpi)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.axis("off")
        ax.set_title("Диаграмма состояний (жизненный цикл требования)", fontsize=12, pad=12)

        states = [
            (1.5, 3, "Черновик"),
            (4.2, 3, "Уточнение"),
            (6.9, 3, "Согласовано"),
            (4.2, 1.0, "Реализовано"),
        ]
        for x, y, label in states:
            box = FancyBboxPatch(
                (x - 0.7, y - 0.35),
                1.4,
                0.7,
                boxstyle="round,pad=0.05",
                edgecolor="#334155",
                facecolor="#f1f5f9",
            )
            ax.add_patch(box)
            ax.text(x, y, label, ha="center", va="center", fontsize=9)

        arrows = [
            ((2.2, 3), (3.5, 3)),
            ((5.6, 3), (6.2, 3)),
            ((6.5, 2.65), (5.0, 1.35)),
            ((3.8, 1.0), (2.0, 2.65)),
        ]
        for (x0, y0), (x1, y1) in arrows:
            ax.add_patch(
                FancyArrowPatch(
                    (x0, y0),
                    (x1, y1),
                    arrowstyle="->",
                    mutation_scale=12,
                    color="#475569",
                    linewidth=1.2,
                )
            )
        ax.text(0.6, 3, "Начало", fontsize=8)
        ax.annotate("", xy=(1.4, 3), xytext=(0.9, 3), arrowprops=dict(arrowstyle="->", color="#475569"))
        return fig

    def build_er(self, analysis: dict[str, Any] | None = None) -> plt.Figure:
        """Minimal ER-style diagram with inferred entities from goals."""
        analysis = analysis or {}
        goals = analysis.get("goals") or []
        entities = ["Требование", "Вариант использования", "Тест", "Релиз"]
        if goals:
            for g in goals[:2]:
                word = g.split()[0][:18] if g.split() else ""
                if word and word not in entities:
                    entities.insert(0, word)

        fig, ax = plt.subplots(figsize=self._fig_size, dpi=self._dpi)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 8)
        ax.axis("off")
        ax.set_title("ER-диаграмма (концептуальная)", fontsize=12, pad=12)

        positions = [(2, 6), (6.5, 6), (2, 2.5), (6.5, 2.5)]
        for i, ent in enumerate(entities[:4]):
            x, y = positions[i]
            w, h = 2.2, 0.9
            ax.add_patch(
                FancyBboxPatch(
                    (x - w / 2, y - h / 2),
                    w,
                    h,
                    boxstyle="round,pad=0.02",
                    edgecolor="#7c3aed",
                    facecolor="#faf5ff",
                )
            )
            ax.text(x, y, ent[:22], ha="center", va="center", fontsize=8)

        rel = [((2, 5.4), (6.5, 5.4)), ((2, 3.1), (6.5, 3.1)), ((3.2, 5.5), (3.2, 3.4))]
        for (xa, ya), (xb, yb) in rel:
            ax.plot([xa, xb], [ya, yb], color="#a78bfa", linewidth=1.5)
        ax.text(4.2, 5.55, "связан", fontsize=7, color="#6d28d9")
        ax.text(4.2, 2.95, "покрывает", fontsize=7, color="#6d28d9")
        return fig

    def get_figure(self, kind: DiagramKind, analysis: dict[str, Any] | None = None) -> plt.Figure:
        if kind == "sequence":
            return self.build_sequence(analysis)
        if kind == "state":
            return self.build_state(analysis)
        return self.build_er(analysis)

    def export(
        self,
        kind: DiagramKind,
        path: str | Path,
        analysis: dict[str, Any] | None = None,
    ) -> Path:
        path = Path(path)
        fig = self.get_figure(kind, analysis)
        suffix = path.suffix.lower()
        path.parent.mkdir(parents=True, exist_ok=True)
        if suffix == ".png":
            fig.savefig(path, bbox_inches="tight", facecolor="white")
        elif suffix == ".svg":
            fig.savefig(path, format="svg", bbox_inches="tight", facecolor="white")
        elif suffix == ".pdf":
            fig.savefig(path, format="pdf", bbox_inches="tight", facecolor="white")
        else:
            fig.savefig(path.with_suffix(".png"), bbox_inches="tight", facecolor="white")
            path = path.with_suffix(".png")
        plt.close(fig)
        return path
