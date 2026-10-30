from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from pydantic import BaseModel,ConfigDict,Field
from auth_store import AuthFailure,AuthStore,Identity
from auth_dependencies import current_user,require_admin

router=APIRouter(prefix='/api/auth',tags=['账户'])

class UserResponse(BaseModel):
    id:str
    username:str
    role:Literal['user','admin']

class LoginRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    username:str=Field(min_length=3,max_length=64)
    password:str=Field(min_length=1,max_length=128)

class LoginResponse(BaseModel):
    access_token:str
    token_type:Literal['bearer']
    expires_at:float
    user:UserResponse

class CreateUserRequest(LoginRequest):
    password:str=Field(min_length=12,max_length=128)
    role:Literal['user','admin']='user'

@router.post('/login',response_model=LoginResponse)
def login(payload:LoginRequest,request:Request,response:Response):
    response.headers['Cache-Control']='no-store'
    try:return AuthStore().login(payload.username,payload.password,request.client.host if request.client else 'unknown')
    except AuthFailure as exc:raise HTTPException(exc.status,str(exc),headers={'Cache-Control':'no-store','Retry-After':'900'} if exc.status==429 else {'Cache-Control':'no-store'}) from exc

@router.get('/me',response_model=UserResponse)
def me(response:Response,user:Identity=Depends(current_user)):
    response.headers['Cache-Control']='no-store'
    return user.public()

@router.post('/logout',status_code=204)
def logout(user:Identity=Depends(current_user)):
    AuthStore().logout(user)
    return Response(status_code=204,headers={'Cache-Control':'no-store'})

@router.post('/users',response_model=UserResponse,status_code=201)
def create_user(payload:CreateUserRequest,user:Identity=Depends(require_admin)):
    try:return AuthStore().create_user(payload.username,payload.password,payload.role).public()
    except ValueError as exc:raise HTTPException(409,str(exc)) from exc
