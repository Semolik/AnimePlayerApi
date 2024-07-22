import asyncio
from src.models.files import Image
from src.utils.files import get_image_path
from pathlib import Path
from sqlalchemy import event


async def delete_image_file(target: Image):
    image_path = await get_image_path(image=target)
    path = Path(image_path)
    if path.exists():
        path.unlink()


@event.listens_for(Image, "before_delete")
def receive_after_delete(mapper, connection, target: Image):
    asyncio.create_task(delete_image_file(target=target))
