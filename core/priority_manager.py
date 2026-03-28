"""Requirement prioritization (MoSCoW + weighted score inspired by Wiegers)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class PriorityBand(str, Enum):
    MUST = "Must"
    SHOULD = "Should"
    COULD = "Could"
    WONT = "Won't"


@dataclass
class PriorityResult:
    requirement_id: str
    text: str
    band: PriorityBand
    score: float  # 0..100
    rationale: str


class PriorityManager:
    """
    Combines simple keyword heuristics with explicit weights for
    business value, risk, and regulatory drivers.
    """

    def __init__(
        self,
        weight_value: float = 0.45,
        weight_risk: float = 0.35,
        weight_regulatory: float = 0.20,
    ) -> None:
        self.weight_value = weight_value
        self.weight_risk = weight_risk
        self.weight_regulatory = weight_regulatory

    def score_requirement(
        self,
        req_id: str,
        text: str,
        *,
        value: int | None = None,
        risk: int | None = None,
        regulatory: int | None = None,
    ) -> PriorityResult:
        """
        value/risk/regulatory: 1..5 if provided; else inferred from text.
        """
        t = (text or "").lower()
        v = value if value is not None else self._infer_scale(t, self._value_keywords(), default=3)
        r = risk if risk is not None else self._infer_scale(t, self._risk_keywords(), default=2)
        reg = regulatory if regulatory is not None else self._infer_scale(t, self._reg_keywords(), default=1)
        # normalize 1..5 to 0..1
        nv, nr, nreg = (v - 1) / 4, (r - 1) / 4, (reg - 1) / 4
        wsum = self.weight_value + self.weight_risk + self.weight_regulatory
        score = 100 * (
            self.weight_value * nv + self.weight_risk * nr + self.weight_regulatory * nreg
        ) / wsum
        band = self._band_from_score(score, t)
        rationale = (
            f"Оценка: ценность={v}, риск={r}, регуляторика={reg}. "
            f"Взвешенный балл {score:.1f}/100 → {band.value}."
        )
        return PriorityResult(req_id, text, band, score, rationale)

    def prioritize_batch(self, items: list[dict[str, Any]]) -> list[PriorityResult]:
        out: list[PriorityResult] = []
        for it in items:
            out.append(
                self.score_requirement(
                    str(it.get("id", "")),
                    str(it.get("text", "")),
                    value=it.get("value"),
                    risk=it.get("risk"),
                    regulatory=it.get("regulatory"),
                )
            )
        out.sort(key=lambda x: x.score, reverse=True)
        return out

    @staticmethod
    def _value_keywords() -> tuple[str, ...]:
        return (
            "доход",
            "revenue",
            "конкурент",
            "customer",
            "клиент",
            "ценность",
            "value",
            "kpi",
        )

    @staticmethod
    def _risk_keywords() -> tuple[str, ...]:
        return (
            "безопасн",
            "security",
            "персональн",
            "gdpr",
            "pci",
            "отказ",
            "availability",
            "данн",
            "утечк",
        )

    @staticmethod
    def _reg_keywords() -> tuple[str, ...]:
        return (
            "закон",
            "law",
            "регулятор",
            "compliance",
            "аудит",
            "audit",
            "стандарт",
            "iso",
        )

    def _infer_scale(self, text: str, keywords: tuple[str, ...], default: int) -> int:
        hits = sum(1 for k in keywords if k in text)
        if hits >= 3:
            return 5
        if hits == 2:
            return 4
        if hits == 1:
            return 3
        return default

    def _band_from_score(self, score: float, text: str) -> PriorityBand:
        low = ("nice", "опционально", "optional", "wish", "желательно")
        if any(x in text for x in low) and score < 70:
            return PriorityBand.COULD
        if score >= 80:
            return PriorityBand.MUST
        if score >= 55:
            return PriorityBand.SHOULD
        if score >= 35:
            return PriorityBand.COULD
        return PriorityBand.WONT
