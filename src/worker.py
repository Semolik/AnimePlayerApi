import asyncio
from celery import Celery
from src.parsers import parsers_dict
from src.utils.parsers import Parser
import os
from src.core.config import settings

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND")


async def update_parser(parser: Parser):
    service = await parser.get_service()
    await parser.update_titles(page=1, service=service, raise_error=True)


@celery.task(name="update_parser_task")
def update_parser_wrapper(parser_id: str):
    parser = parsers_dict.get(parser_id)
    if parser:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(update_parser(parser))
    else:
        print(f"Parser with ID {parser_id} not found.")


async def check_parser(parser_id: str):
    parser: Parser = parsers_dict.get(parser_id)
    timeout = await parser.get_parser_expires_in()
    print(f"Timeout for {parser_id}: {timeout}")
    if timeout <= 0:
        print(f"Updating {parser_id}")
        await update_parser(parser)
        print(f"Updated {parser_id}")
        timeout = settings.titles_cache_hours * 3600
    check_parser_wrapper.apply_async((parser_id,), countdown=timeout)


@celery.task(name="check_parser_task")
def check_parser_wrapper(parser_id: str):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_parser(parser_id))


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    for parser_id in parsers_dict.keys():
        check_parser_wrapper.apply_async((parser_id,))
