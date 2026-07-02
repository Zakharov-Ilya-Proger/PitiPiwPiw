from pydantic import BaseModel, Field


class Search(BaseModel):
    title: str | None = Field(default=None, description="Поиск по заголовку")
    description: str | None = Field(default=None, description="Поиск по описанию")
