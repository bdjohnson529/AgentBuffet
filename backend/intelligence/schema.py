from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


Moat = Literal["High", "Medium", "Low", "unknown"]
FinancialHealth = Literal["Pass", "Fail", "unknown"]
Valuation = Literal["Over-valued", "Under-valued", "unknown"]
Action = Literal["BUY", "HOLD", "SELL", "AVOID"]


class EvidenceItem(BaseModel):
    """
    Optional audit trail back to deterministic inputs.
    Keep this small; it's meant for debugging and portfolio rollups.
    """

    claim: str = Field(..., description="Short claim being supported")
    source: str = Field(..., description="Fact key or pointer, e.g. financials.forwardPE or latest_filing.snippets[2]")


class ReportModel(BaseModel):
    moat: Moat
    financial_health: FinancialHealth
    valuation: Valuation

    base_case: str
    upside_case: str
    downside_case: str

    action: Action
    reasoning: str

    evidence: Optional[list[EvidenceItem]] = None

