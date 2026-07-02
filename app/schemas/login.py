from pydantic import BaseModel, Field

class User(BaseModel):
    login: str = Field(..., description='The user name.')
    password: str = Field(..., description='The password.')
