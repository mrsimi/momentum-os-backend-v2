from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi import HTTPException
import jwt
import os
from dotenv import load_dotenv
import secrets
import string
import base64
import hmac
import hashlib

load_dotenv()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def generate_salt(length: int = 16) -> str:
    return secrets.token_urlsafe(length)

def generate_encrypted_user_id(user_id: int) -> str:
    # Generate a random salt
    salt = generate_salt()
    
    # Create payload with user_id and timestamp
    payload = {
        'user_id': user_id,
        'timestamp': int(datetime.now(timezone.utc).timestamp()),
        'salt': salt
    }
    
    # Create signature using HMAC
    signature = hmac.new(
        os.getenv('JWT_SECRET_KEY').encode(),
        f"{user_id}{salt}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Combine payload and signature
    token_parts = {
        'payload': payload,
        'signature': signature
    }
    
    # Encode the entire token
    token = jwt.encode(
        token_parts,
        os.getenv('JWT_SECRET_KEY'),
        algorithm='HS256'
    )
    
    # URL-safe base64 encoding
    return base64.urlsafe_b64encode(token.encode()).decode()

def decrypt_encrypted_user_id(encrypted_user_id: str) -> int:
    try:
        # Decode base64
        decoded_token = base64.urlsafe_b64decode(encrypted_user_id.encode()).decode()
        
        # Decode JWT
        token_parts = jwt.decode(
            decoded_token,
            os.getenv('JWT_SECRET_KEY'),
            algorithms=['HS256']
        )
        
        # Verify signature
        expected_signature = hmac.new(
            os.getenv('JWT_SECRET_KEY').encode(),
            f"{token_parts['payload']['user_id']}{token_parts['payload']['salt']}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if token_parts['signature'] != expected_signature:
            raise ValueError("Invalid signature")
            
        # Check token expiration (optional)
        if datetime.now(timezone.utc).timestamp() - token_parts['payload']['timestamp'] > 3600:  # 1 hour
            raise ValueError("Token expired")
            
        return token_parts['payload']['user_id']
    except Exception as e:
        raise ValueError(f"Invalid token: {str(e)}")

#create access token to expire in 24 hours
def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=48)
    payload = {
        'user_id': user_id,
        'exp': expire
    }
    token = jwt.encode(
        payload,
        os.getenv('JWT_SECRET_KEY'),
        algorithm='HS256'
    )
    return token

def get_current_user(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            os.getenv('JWT_SECRET_KEY'),
            algorithms=['HS256']
        )
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    


def encrypt_payload (payload: dict) -> str:
    # Convert payload to string
    payload_str = str(payload)
    
    # Generate a random salt
    salt = generate_salt()
    
    # Create HMAC signature
    signature = hmac.new(
        os.getenv('JWT_SECRET_KEY').encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Combine payload and signature
    token_parts = {
        'payload': payload,
        'signature': signature,
        'salt': salt
    }
    
    # Encode the entire token
    token = jwt.encode(
        token_parts,
        os.getenv('JWT_SECRET_KEY'),
        algorithm='HS256'
    )
    
    # URL-safe base64 encoding
    return base64.urlsafe_b64encode(token.encode()).decode()

def decrypt_payload(encrypted_payload: str) -> dict:
    try:
        # Decode base64
        decoded_token = base64.urlsafe_b64decode(encrypted_payload.encode()).decode()
        
        # Decode JWT
        token_parts = jwt.decode(
            decoded_token,
            os.getenv('JWT_SECRET_KEY'),
            algorithms=['HS256']
        )
        
        # Verify signature
        expected_signature = hmac.new(
            os.getenv('JWT_SECRET_KEY').encode(),
            str(token_parts['payload']).encode(),
            hashlib.sha256
        ).hexdigest()
        
        if token_parts['signature'] != expected_signature:
            raise ValueError("Invalid signature")
            
        return token_parts['payload']
    except Exception as e:
        raise ValueError(f"Invalid token: {str(e)}")
    
    