
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DrawingAnalysis(BaseModel):
    part_identifier: str
    units: Literal["mm", "inches"]
    manufacturing_operations: dict[str, list[dict[str, Any]]]
    precision_fits: list[dict[str, Any]]
    geometric_tolerances: list[dict[str, Any]] = Field(default_factory=list)
    form_features: list[dict[str, Any]]
    critical_operations: list[dict[str, Any]] = Field(default_factory=list)
    inspection_checklist: list[dict[str, Any]] = Field(default_factory=list)
    quality_document_templates: dict[str, Any] = Field(default_factory=dict)
    metadata_and_notes: list[dict[str, Any]] = Field(default_factory=list)
    review_flags: list[dict[str, Any]] = Field(default_factory=list)

    # Persisted normalized engineering feature representation.
    # Older analysis records may not contain this field.
    normalized_feature_model: dict[str, Any] | None = Field(default=None, exclude=True)

    model_config = ConfigDict(extra="forbid")


class ProjectAnalysisResponse(BaseModel):
    project_id: str
    status: str
    analysis: DrawingAnalysis | None
    review: "ProjectAnalysisReview | None" = None
    process_plan_status: str = "not_generated"
    route_review: dict[str, Any] | None = None


class AnalysisReviewDecision(BaseModel):
    target_id: str = Field(min_length=1, max_length=256)
    decision: Literal["accepted", "corrected", "rejected"]
    corrected_callout: str | None = Field(default=None, max_length=256)
    corrected_value: float | None = None
    corrected_feature: str | None = Field(default=None, max_length=128)
    corrected_units: Literal["mm", "inches"] | None = None
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_correction(self):
        if self.decision == "corrected" and all(
            value is None
            for value in (
                self.corrected_callout,
                self.corrected_value,
                self.corrected_feature,
                self.corrected_units,
            )
        ):
            raise ValueError(
                "A corrected decision must include at least one corrected field"
            )
        return self


class ProjectAnalysisReviewUpdate(BaseModel):
    status: Literal["in_review", "approved", "changes_requested"]
    decisions: list[AnalysisReviewDecision]


class ProjectAnalysisReview(BaseModel):
    status: Literal["in_review", "approved", "changes_requested"]
    reviewer: str
    updated_at: datetime
    decisions: list[AnalysisReviewDecision]


class ProcessPlanReviewUpdate(BaseModel):
    status: Literal["approved", "changes_requested"]
    comment: str | None = Field(default=None, max_length=2000)
    operations: list["ProcessOperationReview"] = Field(default_factory=list)


class ProcessOperationReview(BaseModel):
    operation_id: UUID
    operation_name: str = Field(min_length=1, max_length=255)
    sequence_order: int = Field(ge=1)
    estimated_time_minutes: float = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    machine_type: str | None = Field(default=None, max_length=128)


ProjectAnalysisResponse.model_rebuild()
ProcessPlanReviewUpdate.model_rebuild()
