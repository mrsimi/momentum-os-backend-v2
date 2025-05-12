from pydantic import BaseModel, EmailStr

class GoogleLoginRequest(BaseModel):
    token: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str

    class Config:
        from_attributes = True

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    
        
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UpdatePasswordRequest(BaseModel):
    token: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


