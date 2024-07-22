from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from src.crud.users_crud import UsersCrud
from src.schemas.images import ImageInfo
from src.db.session import get_async_session
from src.schemas.users import UserRead, UserUpdate
from src.users_controller import current_active_user
api_router = APIRouter(prefix="/users", tags=["users"])


@api_router.get("/me", response_model=UserRead)
async def get_me(
    current_user=Depends(current_active_user),
    db=Depends(get_async_session)
):
    return await UsersCrud(db).get_user_by_id(current_user.id)


@api_router.put("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    current_user=Depends(current_active_user),
    db=Depends(get_async_session),
):
    users_crud = UsersCrud(db)
    if data.email != data.email and await users_crud.get_user_by_email(data.email) is not None:
        raise HTTPException(
            status_code=400, detail="Пользователь с таким email уже существует")
    await users_crud.update_user(current_user, data)
    return await users_crud.get_user_by_id(current_user.id)


@api_router.put("/me/image", response_model=ImageInfo)
async def update_user_me_image(
    userPicture: UploadFile = File(
        default=..., description='Фото пользователя'),
    db=Depends(get_async_session),
    current_user=Depends(current_active_user)
):
    users_crud = UsersCrud(db)
    image = await users_crud.update_user_image(user=current_user, image=userPicture)
    return image


@api_router.delete("/me/image", status_code=204)
async def delete_user_me_image(
    db=Depends(get_async_session),
    current_user=Depends(current_active_user)
):
    await UsersCrud(db).delete_user_image(user=current_user)
