from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from email_validator import validate_email, EmailNotValidError
from typing import Optional
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models import User
from backend.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    is_account_locked,
    record_failed_login,
    reset_failed_logins,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from backend.services.audit_service import log_audit_event
from backend.metrics import AUTH_FAILURES_TOTAL
from backend.config import settings
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: str
    password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_admin: bool = False

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", response_model=UserResponse)
@limiter.limit(settings.REGISTER_RATE_LIMIT)
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    try:
        email_info = validate_email(user.email, check_deliverability=False)
        email = email_info.normalized
    except EmailNotValidError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_password = get_password_hash(user.password)
    new_user = User(
        name=user.name,
        email=email,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    log_audit_event(db, action="USER_CREATED", outcome="SUCCESS", user_id=new_user.id, request=request)
    return new_user

@router.post("/login", response_model=Token)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    raw_username = (form_data.username or "").strip().lower()
    try:
        email_info = validate_email(raw_username, check_deliverability=False)
        username = email_info.normalized.lower()
    except EmailNotValidError:
        username = raw_username

    user = db.query(User).filter(User.email == username).first()
    
    if user:
        if is_account_locked(user):
            AUTH_FAILURES_TOTAL.labels(reason="account_locked").inc()
            log_audit_event(db, action="SECURITY_EVENT", outcome="BLOCKED", user_id=user.id, details="Account locked due to excessive failed attempts", request=request)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account locked due to multiple failed login attempts. Try again in {settings.ACCOUNT_LOCKOUT_DURATION_MINUTES} minutes."
            )

    if not user or not verify_password(form_data.password, user.password_hash):
        if user:
            record_failed_login(db, user)
            log_audit_event(db, action="FAILED_LOGIN", outcome="FAILURE", user_id=user.id, details={"email": form_data.username, "attempts": user.failed_login_attempts}, request=request)
        else:
            log_audit_event(db, action="FAILED_LOGIN", outcome="FAILURE", details={"email": form_data.username}, request=request)
            
        AUTH_FAILURES_TOTAL.labels(reason="invalid_credentials").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    reset_failed_logins(db, user)
    log_audit_event(db, action="LOGIN", outcome="SUCCESS", user_id=user.id, request=request)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(request: Request, current_user: Optional[User] = Depends(get_current_user), db: Session = Depends(get_db)):
    uid = current_user.id if current_user else None
    log_audit_event(db, action="LOGOUT", outcome="SUCCESS", user_id=uid, request=request)
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

