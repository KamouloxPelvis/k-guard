import os
import bcrypt
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import APIRouter, HTTPException, Depends, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from dotenv import load_dotenv

load_dotenv()

# Configuration Sécurité - Récupérées via k-guard-secrets dans K3s
SECRET_KEY = os.getenv("SECRET_KEY", "une-cle-tres-secrete-par-defaut")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_HASH = os.getenv("ADMIN_PASSWORD_HASH")

security_scheme = HTTPBearer()
# Pas de préfixe ici, géré par le router central
router = APIRouter(tags=["Authentication"])

def verify_password(plain_password: str, hashed_password: str):
    if not hashed_password:
        return False
    try:
        # Bcrypt nécessite des bytes pour les deux arguments
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"❌ Erreur de vérification password: {e}")
        return False

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security_scheme)):
    """Dépendance utilisée pour protéger les routes"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except (JWTError, Exception):
        raise HTTPException(status_code=401, detail="Erreur de signature ou token invalide")
    
@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Route d'authentification (OAuth2 Password Flow)"""
    # Vérification Username + Hash Bcrypt
    if form_data.username != ADMIN_USERNAME or not verify_password(form_data.password, ADMIN_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Accès refusé : Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Génération du JWT
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": form_data.username, "exp": expire}
    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": access_token, "token_type": "bearer"}