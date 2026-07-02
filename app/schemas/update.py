from pydantic import BaseModel, Field

from app.enums import Status


class UpdateParams(BaseModel):
    target_status: Status = Field(..., description="The target status to change")
    req_id: int = Field(..., description="The request id")
