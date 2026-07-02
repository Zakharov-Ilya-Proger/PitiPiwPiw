from typing import Optional

from pydantic import BaseModel, Field

class Search(BaseModel):
    title: str = Optional[Field(..., description='Title of the search query')]
    description: str = Optional[Field(..., description='Description of the search query')]
