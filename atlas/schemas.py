"""Pydantic schemas passed between agents. (Re-exported from atlas.agents.)"""

from typing import Literal

from pydantic import BaseModel, Field


class ResearchTask(BaseModel):
    id: str = Field(description="Short id for this task, e.g. R1")
    kind: Literal["cost", "quality"] = Field(description="cost -> Cost Researcher; quality -> Quality Researcher")
    question: str = Field(description="What this researcher should find out, in one or two sentences")
    cohort_handle: str = Field(description="Cohort handle from resolve_cohort, e.g. C1")
    drg_codes: list[int] = Field(default_factory=list, description="DRG codes to look at (cost tasks)")
    measure_ids: list[str] = Field(default_factory=list, description="Measure ids to look at (quality tasks), e.g. READM-30-HF-HRRP, MORT_30_HF")


class CohortSpec(BaseModel):
    cohort_handle: str
    hospital_ccns: list[str]
    focus_ccns: list[str] = Field(default_factory=list)
    drg_codes: list[int] = Field(default_factory=list)
    measure_ids: list[str] = Field(default_factory=list)
    region_label: str = ""
    unresolved: list[str] = Field(default_factory=list)


class Gap(BaseModel):
    kind: Literal["missing_metric", "small_n", "no_benchmark", "unresolved_entity", "period_mismatch"]
    detail: str
    fillable: bool = False
    suggested_task: dict | None = None  # for fillable gaps: {"kind": "cost", "drg_codes": [..]} or {"kind": "quality", "measure_ids": [..]}


class Finding(BaseModel):
    task_id: str
    status: Literal["ok", "partial", "failed"] = "ok"
    agent: str = ""
    table_handles: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    summary: str = ""
    gaps: list[Gap] = Field(default_factory=list)


class Claim(BaseModel):
    text: str = Field(description="One to three sentences. Numbers appear only as the exact `display` strings of the facts you cite. End with the source markers, e.g. [S1].")
    fact_ids: list[str] = Field(default_factory=list, description="Ids (F#) of every fact this claim uses")
    source_ids: list[str] = Field(default_factory=list, description="Source ids (S#) for the claim")


class Report(BaseModel):
    headline: str = Field(description="One sentence that answers the question. No numbers unless copied from a fact display.")
    claims: list[Claim] = Field(description="3 to 6 claims supporting the headline")
    data_cannot_tell_you: list[str] = Field(description="At least 2 things this data cannot answer for this question")
    followups: list[str] = Field(default_factory=list, description="Up to 3 follow-up questions the data could answer")


class CritiqueTask(BaseModel):
    kind: Literal["cost", "quality"]
    drg_codes: list[int] = Field(default_factory=list, description="DRG codes (cost tasks)")
    measure_ids: list[str] = Field(default_factory=list, description="Measure ids from the allowed list (quality tasks)")
    why: str = Field(description="One sentence: what part of the question this would answer")


class Critique(BaseModel):
    unanswered: list[str] = Field(default_factory=list, description="Parts of the question the facts do not answer, max 3, one short sentence each")
    tasks: list[CritiqueTask] = Field(default_factory=list, description="At most 2 extra lookups that would answer an unanswered part, only with allowed ids")
