from pydantic import BaseModel


class DetectAsyncResponse(BaseModel):
    job_id: str
    status: str
    poll_url: str


class ScoreBreakdown(BaseModel):
    ela: float | None = None
    clone_detection: float | None = None
    metadata: float | None = None
    ai_generated: float | None = None
    font_consistency: float | None = None
    ocr_diff: float | None = None


class FlagItem(BaseModel):
    type: str
    severity: str
    region: list | None = None
    details: str | None = None


class DetectResponse(BaseModel):
    job_id: str
    status: str
    verdict: str | None = None
    confidence: float | None = None
    risk_score: int | None = None
    flags: list[dict] = []
    scores: dict | None = None
    heatmap_url: str | None = None
    processing_ms: int | None = None
    file_name: str | None = None
    file_type: str | None = None
