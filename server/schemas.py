from pydantic import BaseModel


class RunSummary(BaseModel):
    id: str
    timestamp: str
    question: str


class LaunchRequest(BaseModel):
    question: str | None = None
    num_rounds: int | None = None
    principal_ids: list[str] | None = None


class LaunchResponse(BaseModel):
    session_id: str
    stream_url: str
