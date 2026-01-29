from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Схема запроса авторизации"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Схема ответа авторизации"""
    access_token: str
    token_type: str = "bearer"
