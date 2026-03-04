import os
import bcrypt
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import APIRouter, HTTPException, Depends, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm, OAuth2PasswordBearer
from dotenv import load_dotenv

# Load environment variables (from .env or K3s Secrets)
load_dotenv()

# --- SECURITY CONFIGURATION ---
SECRET_KEY = os.getenv("SECRET_KEY", "default-fallback-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_HASH = os.getenv("ADMIN_PASSWORD_HASH")

# Security scheme for Axios interceptor (Frontend)
security_scheme = HTTPBearer()

# Security scheme for Swagger documentation (Interactive)
# Using "api/token" as the global /api prefix is managed by main.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

router = APIRouter(tags=["Authentication"])

# --- VERIFICATION LOGIC ---

def verify_password(plain_password: str, hashed_password: str):
    """Verifies password by comparing plain text with Bcrypt hash"""
    if not hashed_password:
        return False
    try:
        # Bcrypt requires bytes for comparison
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        return False

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security_scheme)):
    """
    Security dependency used to protect routes.
    Validates the JWT presence and signature in the Authorization header.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired"
        )
    except (JWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Signature error or invalid token"
        )

# --- ROUTES ---

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authentication route (OAuth2 Password Flow).
    Generates a JWT if credentials are valid.
    """
    # 1. User and Hash verification
    if form_data.username != ADMIN_USERNAME or not verify_password(form_data.password, ADMIN_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access Denied: Incorrect credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Expiration calculation
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 3. Payload creation
    to_encode = {
        "sub": form_data.username, 
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    
    # 4. JWT Encoding
    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }