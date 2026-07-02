from pydantic import BaseModel, Field

from app.enums import Priority


class CreateReqShem(BaseModel):
    title: str = Field(..., min_length=3, max_length=120, description="Заголовок внутренней заявки")
    description: str | None = Field(default=None, max_length=1000, description="Описание внутренней заявки")
    priority: Priority = Field(..., description="Приоритет обработки заявки")
