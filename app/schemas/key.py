from pydantic import BaseModel


class APIKeyCreate(BaseModel):
    name: str | None = None
    environment: str = "live"


class APIKeyResponse(BaseModel):
    id: str
    prefix: str
    name: str | None
    environment: str
    hit_count: int
    last_used_at: str | None


class APIKeyCreateResponse(BaseModel):
    key: str
    prefix: str
    id: str
    name: str | None
