from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import StatementError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenError, decode_access_token
from app.database import get_db
from app.models.user import User, UserRole

# Using a standard tokenUrl for the Bearer token setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Dependency to extract and validate the Bearer token,
    then retrieve the authenticated user from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
    except TokenError:
        raise credentials_exception
        
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
    except StatementError: # In case the sub is not a valid UUID string
        raise credentials_exception
    
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to ensure the authenticated user is active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

class RoleChecker:
    """
    Dependency class to verify the active user has a required role.
    """
    def __init__(self, required_roles: list[UserRole]):
        self.required_roles = required_roles

    def __call__(self, user: Annotated[User, Depends(get_current_active_user)]) -> User:
        if user.role not in [role.value for role in self.required_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough privileges"
            )
        return user
