import uuid
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from src.models.files import Image
from src.db.session import get_async_session
from src.crud.base import BaseCRUD
from src.utils.files import get_image_path

api_router = APIRouter(tags=["files"])


@api_router.get("/images/{image_id}", response_class=FileResponse)
async def get_app_image(
    image_id: uuid.UUID = Path(...),
    db=Depends(get_async_session),
):
    base_crud = BaseCRUD(db)
    image = await base_crud.get(id=image_id, model=Image)
    if not image:
        raise HTTPException(status_code=404, detail="Изображение не найдено")
    return FileResponse(await get_image_path(image=image))
