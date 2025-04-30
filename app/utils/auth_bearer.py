from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.utils.security import decode_token



class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if credentials.scheme != "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            payload = self.verify_jwt(credentials.credentials)
            if not payload:
                raise HTTPException(status_code=403, detail="Invalid or expired token.")
            return payload  # 🔥 Return the decoded payload
        raise HTTPException(status_code=403, detail="Invalid authorization code.")


    def verify_jwt(self, jwtoken: str):
        try:
            return decode_token(jwtoken)
        except:
            return None