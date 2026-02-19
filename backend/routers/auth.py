import os
import bcrypt
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import APIRouter, HTTPException, Depends, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm, OAuth2PasswordBearer
from dotenv import load_dotenv

# Chargement des variables d'environnement (.env ou K3s Secrets)
load_dotenv()

# --- CONFIGURATION SÉCURITÉ ---
SECRET_KEY = os.getenv("SECRET_KEY", "une-cle-tres-secrete-par-defaut")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_HASH = os.getenv("ADMIN_PASSWORD_HASH")

# Schéma pour l'intercepteur Axios (Frontend)
security_scheme = HTTPBearer()

# Schéma pour la documentation Swagger (Interactif)
# On utilise "api/token" car le préfixe global /api est géré par main.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

router = APIRouter(tags=["Authentication"])

# --- LOGIQUE DE VÉRIFICATION ---

def verify_password(plain_password: str, hashed_password: str):
    """Vérifie le mot de passe en comparant le clair et le hash Bcrypt"""
    if not hashed_password:
        return False
    try:
        # Bcrypt nécessite des bytes
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"❌ Erreur de vérification password: {e}")
        return False

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security_scheme)):
    """
    Dépendance de sécurité utilisée pour protéger les routes.
    Vérifie la validité du JWT présent dans le header Authorization.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token expiré"
        )
    except (JWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Erreur de signature ou token invalide"
        )

# --- ROUTES ---

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Route d'authentification (Flux OAuth2 Password).
    Génère un JWT si les identifiants sont corrects.
    """
    # 1. Vérification de l'utilisateur et du hash
    if form_data.username != ADMIN_USERNAME or not verify_password(form_data.password, ADMIN_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Accès refusé : Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Calcul de l'expiration
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 3. Création du Payload
    to_encode = {
        "sub": form_data.username, 
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    
    # 4. Encodage du JWT
    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }