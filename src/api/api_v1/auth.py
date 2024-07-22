from fastapi import APIRouter, Depends, HTTPException, status
from src.schemas.users import UserCreate, UserRead, UserReadAfterRegister, ChangePassword
from src.db.session import get_async_session, AsyncSession
from src.crud.users_crud import UsersCrud
from src.users_controller import auth_backend, fastapi_users, current_active_user, get_password_hash
from .oauth import oauth_router

api_router = APIRouter(prefix="/auth", tags=["auth"])

api_router.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/jwt"
)

api_router.include_router(
    fastapi_users.get_reset_password_router(),
)
api_router.include_router(
    fastapi_users.get_verify_router(UserReadAfterRegister)
)

api_router.include_router(
    fastapi_users.get_register_router(UserReadAfterRegister, UserCreate)
)
api_router.include_router(oauth_router)


@api_router.put("/change-password", status_code=204)
async def change_password(
    passwords: ChangePassword,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(current_active_user)
):
    """
    Изменение пароля пользователя
    """
    user_cruds = UsersCrud(db)
    if await get_password_hash(passwords.password) != current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный пароль",
        )
    if (await get_password_hash(passwords.new_password)) == current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Новый пароль совпадает со старым",
        )
    await user_cruds.change_password(user=current_user,
                                     new_password=passwords.new_password)
