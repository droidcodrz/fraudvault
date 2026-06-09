from pydantic import BaseModel


class KeyHitBreakdown(BaseModel):
    key_prefix: str
    hits: int


class UsageResponse(BaseModel):
    period_start: str
    period_end: str
    total_hits: int
    by_type: dict[str, int]
    by_key: list[KeyHitBreakdown]
    plan_limit: int | None
    overage_hits: int
