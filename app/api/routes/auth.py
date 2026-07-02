from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import create_access_token, get_current_user, verify_password
from app.models import User as DBUser
from app.repositories import UserRepo, get_user_repo
from app.schemas import Token, User

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(payload: User, user_repo: UserRepo = Depends(get_user_repo)) -> Token:
    created_user = await user_repo.create_user(payload)
    access_token = create_access_token({'sub': created_user.id, 'login': created_user.login, 'role': created_user.role.value})
    return Token(
        access_token=access_token,
        user_id=created_user.id,
        login=created_user.login,
        role=created_user.role.value,
    )


@router.post('/login', response_model=Token)
async def login_user(payload: User, user_repo: UserRepo = Depends(get_user_repo)) -> Token:
    user = await user_repo.get_user(payload.login)
    if user is None or not verify_password(payload.password, user.hash_pwd):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Неверный логин или пароль')

    access_token = create_access_token({'sub': user.id, 'login': user.login, 'role': user.role.value})
    return Token(
        access_token=access_token,
        user_id=user.id,
        login=user.login,
        role=user.role.value,
    )


@router.get('/me')
async def get_me(current_user: DBUser = Depends(get_current_user)) -> dict:
    return {
        'id': current_user.id,
        'login': current_user.login,
        'role': current_user.role.value,
    }
