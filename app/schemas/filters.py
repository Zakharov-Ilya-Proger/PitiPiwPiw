from pydantic import BaseModel, Field

from app.enums import Priority, Status


class Filters(BaseModel):
    status: Status | None = Field(default=None, description="Фильтр по статусу")
    priority: Priority | None = Field(default=None, description="Фильтр по приоритету")
    page: int = Field(default=1, ge=1, description="Номер страницы")
    limit: int = Field(default=10, ge=1, le=100, description="Размер страницы")
    sort_date: bool = Field(default=True, description="Сортировка по дате создания")
    sort_priority: bool = Field(default=False, description="Сортировка по приоритету")
