from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from auth_store import AuthFailure, AuthStore, Identity

bearer=HTTPBearer(auto_error=False)

def current_user(credentials:HTTPAuthorizationCredentials|None=Depends(bearer)) -> Identity:
    try:return AuthStore().authenticate(credentials.credentials if credentials else '')
    except AuthFailure as exc:raise HTTPException(exc.status,str(exc),headers={'WWW-Authenticate':'Bearer'}) from exc

def require_admin(user:Identity=Depends(current_user)) -> Identity:
    if user.role!='admin':raise HTTPException(403,'此功能仅限管理员')
    return user
