from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    identifier: str
    password: str


class UserOut(BaseModel):
    id: str = Field(default="demo-user")
    name: str = Field(default="Demo User")
    role: str = Field(default="technician")


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut
