from typing import Optional

from pydantic import BaseModel, Field

from app.enums import Priority, Status


class Filters(BaseModel):
    status: Status = Optional[Field(..., description='Status of the filter',)]
    priority: Priority = Optional[Field(..., description='Priority of the filter',)]

    page: int = Field(..., description='Page of the filter',)
    limit: int = Field(..., description='Limit of the filter',)

    sort_date: bool = Field(..., description='Sort of the filter')
    sort_priority: bool = Field(..., description='Sort of the filter')
