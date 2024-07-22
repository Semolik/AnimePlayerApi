import io
import os
import shutil
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, UploadFile
from pathlib import Path
from src.models.files import Image
from PIL import Image as pillow
from src.crud.base import BaseCRUD
from src.core.config import settings
content_folder = '/content'
images_folder = 'images'
images_extension = '.png'
supported_image_extensions = {
    ex for ex, f in pillow.registered_extensions().items() if f in pillow.OPEN}


def init_folders():
    Path(content_folder).mkdir(exist_ok=True)
    for folder in [images_folder]:
        Path('/'.join([content_folder, folder])).mkdir(exist_ok=True)


async def get_image_path(image: Image) -> str:
    return '/'.join([content_folder, images_folder, str(image.id)]) + images_extension


def init_folders():
    Path(content_folder).mkdir(exist_ok=True)
    for folder in [images_folder]:
        Path('/'.join([content_folder, folder])).mkdir(exist_ok=True)


def get_image_link(image_id: UUID) -> str:
    return f'{settings.API_V1_STR}/images/{image_id}'


async def save_image(db: AsyncSession,  upload_file: UploadFile, resize_image_options=(250, 250),
                     detail_error_message="поврежденное изображение") -> Image:

    originalFileName = upload_file.filename
    originalFilePath = Path(originalFileName)
    suffix = originalFilePath.suffix
    if suffix.lower() not in supported_image_extensions:
        raise HTTPException(
            status_code=422, detail="Расширение изображения не поддерживается")

    buf = io.BytesIO()
    buf.name = originalFileName
    shutil.copyfileobj(upload_file.file, buf)
    buf.seek(0)

    # try:
    image = pillow.open(buf)
    image.thumbnail(resize_image_options)
    image_model = await BaseCRUD(db).create(Image())
    image_path = await get_image_path(image=image_model)
    image.save(image_path)
    return image_model
    # except:
    #     raise HTTPException(status_code=422, detail=detail_error_message)
