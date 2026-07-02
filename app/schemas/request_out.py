from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import Priority, Status


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: Status
    priority: Priority
    created_by: int
    created_at: datetime
    updated_at: datetime | None


class RequestListOut(BaseModel):
    items: list[RequestOut]
    page: int
    limit: int
    total: int
