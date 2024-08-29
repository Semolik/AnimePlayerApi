import asyncio
import os
from uuid import UUID
from celery import Celery
from fastapi_mail import FastMail, MessageSchema, MessageType
from src.models.parsers import Title
from src.redis.services import CacheService
from src.schemas.parsers import Episode, TitlesPage
from src.crud.episodes_crud import EpisodesCrud
from src.crud.titles_crud import TitlesCrud
from src.models.users import User
from src.parsers import parsers_dict
from src.utils.parsers import Parser
from src.core.config import settings
from src.mail.conf import conf
from src.db.session import get_async_session_context
from src.utils.videos import VideoDuration
from src.utils.shikimori import Shikimori

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND")


async def send_reset_password_email(user: dict, token: str):
    print(f'Sending reset password email to {user["id"]}')
    message = MessageSchema(
        subject='Сброс пароля',
        recipients=[user['email']],
        template_body={
            'title': 'Сброс пароля',
            'text': f'''<p>Здравствуйте, {user['name']}</p>
                        <p>
                            Вы получили это письмо, так
                            как был запрошен сброс
                            пароля для вашей учетной
                            записи. Если вы не
                            запрашивали сброс пароля,
                            пожалуйста, проигнорируйте
                            это сообщение.
                        </p>
                        <p>
                            Никогда не предоставляйте
                            свои учетные данные и не
                            переходите по незнакомым
                            ссылкам.
                        </p>
                        <a
                            href="{os.environ.get('API_HOST', '')}/reset-password?token={token}"
                            class="btn btn-primary"
                            target="_blank"
                        >
                            Сбросить пароль
                        </a>'''
        },
        subtype=MessageType.html
    )
    try:
        fm = FastMail(conf)
        await fm.send_message(message, template_name='default.html')
        print(f'Reset password email sent to {user["id"]}')
    except Exception as e:
        print(e)


async def send_verify_email(user: dict, token: str):
    print(f'Sending verify email to {user["id"]}')
    message = MessageSchema(
        subject='Подтверждение почты',
        recipients=[user['email']],
        template_body={
            'title': 'Подтверждение почты',
            'text': f'''<p>Здравствуйте, {user['name']}</p>
                            <p>
                                Для подтверждения вашей учетной записи, пожалуйста, нажмите на кнопку ниже:
                            </p>
                            <a
                                href="{os.environ.get('API_HOST', '')}/verify-email?token={token}"
                                class="btn btn-primary"
                                target="_blank"
                            >
                                Подтвердить почту
                            </a>'''
        },
        subtype=MessageType.html
    )
    try:
        fm = FastMail(conf)
        await fm.send_message(message, template_name='default.html')
        print(f'Verify email sent to {user["id"]}')
    except Exception as e:
        print(e)


@celery.task(name="send_reset_password_email_task")
def send_reset_password_email_wrapper(user: User, token: str):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_reset_password_email(user, token))


@celery.task(name="send_verify_email_task")
def send_verify_email_wrapper(user: User, token: str):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_verify_email(user, token))


async def fetch_shikimori(parsed_title, db_title, service, db):
    shikimori_title = await Shikimori(service=service).get_title(parsed_title)
    if shikimori_title:
        print(
            f"Title {parsed_title.id} linked to shikimori {shikimori_title.data['id']}")
    else:
        print(f"Title {parsed_title.id} not found on shikimori")
    await TitlesCrud(db).update_shikimori_info(db_title=db_title, shikimori_id=int(shikimori_title.data['id']) if shikimori_title else None)


async def update_parser(parser: Parser):
    service = await parser.get_service()
    for i in range(1, parser.main_pages_count+1):
        titles = await parser.update_titles(page=i, service=service, raise_error=False)
        for title in titles:
            db_title = await TitlesCrud().get_title_by_id(title.id)
            if not db_title.shikimori_fetched:
                await fetch_shikimori(title=title, db_title=db_title, service=service, db=None)
                await asyncio.sleep(5)


async def check_parser(parser_id: str):
    parser: Parser = parsers_dict.get(parser_id)
    timeout = await parser.get_parser_expires_in()
    if timeout <= 0:
        print(f"Updating {parser_id}")
        await update_parser(parser)
        print(f"Updated {parser_id}")
        timeout = settings.titles_cache_hours * 3600
    check_parser_wrapper.apply_async((parser_id,), countdown=timeout)


async def get_episode_duration(episode: Episode):
    async with get_async_session_context() as session:
        episode_id = episode.id
        episodes_crud = EpisodesCrud(session)
        db_episode = await episodes_crud.get_by_id(episode_id)
        if not db_episode or db_episode.duration_fetched:
            return
        video_duration = None
        try:
            video_duration = VideoDuration(
                episode.links[0].link, use_m3u8=episode.is_m3u8)
            duration = video_duration.get_duration()
            print(f"Duration for {episode_id}: {duration}")
        except Exception as e:
            print(f"Error while getting duration for {episode_id}: {e}")
            duration = None
        episode.seconds = duration
        await episodes_crud.update_episode_duration(episode=db_episode, duration=duration)


@celery.task(name="get_episode_duration_task")
def get_episode_duration_wrapper(episode: dict):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_episode_duration(Episode(**episode)))


@celery.task(name="check_parser_task")
def check_parser_wrapper(parser_id: str):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_parser(parser_id))


@celery.task(name="get_episodes_duration_task")
def get_episodes_duration(title_episodes: list[dict]):
    wait = 0
    for episode in title_episodes:
        if not episode['seconds']:
            get_episode_duration_wrapper.apply_async(
                (episode,), countdown=wait)
            wait += 5


async def prepare_title(parser: Parser, title_id: UUID, id_on_website: str):
    try:
        print(f"Preparing title {title_id}")
        service = await parser.get_service()
        async with get_async_session_context() as session:
            title_obj = await parser._update_title_cache(id_on_website=id_on_website, title_id=title_id, service=service)
            db_title = await parser.update_title_in_db(title_id=title_id, title_data=title_obj, db=session)
            if not db_title.shikimori_fetched:
                shikimori_title = await Shikimori(service=service).get_title(title_obj)
                await TitlesCrud(session).update_shikimori_info(db_title=db_title, shikimori_id=int(shikimori_title.data['id']) if shikimori_title else None)
            await session.commit()
    except Exception as e:
        print(f"Error while preparing title {title_id}: {e}")


@celery.task(name="prepare_title_task")
def prepare_title_wrapper(title_id: UUID, parser_id: str, id_on_website: str):
    loop = asyncio.get_event_loop()
    parser = parsers_dict.get(parser_id)
    loop.run_until_complete(prepare_title(
        parser=parser, title_id=title_id, id_on_website=id_on_website))


async def prepare_all_parser_titles(parser_id: str):
    print(f"Preparing all titles for {parser_id}")
    parser: Parser = parsers_dict.get(parser_id)
    service = await parser.get_service()
    async with get_async_session_context() as session:
        first_page = await parser.get_titles(page=1, db=session, service=service)
        total_pages = first_page.total_pages
        for page in range(1, total_pages+1):
            print(f"Preparing page {page} for {parser_id}")
            try:
                if page == 1:
                    page_data = first_page
                else:
                    page_data = await parser.get_titles(page=page, db=session, service=service)
                for title in page_data.titles:
                    db_title = await TitlesCrud(session).get_title_by_id(title.id)
                    if not db_title.shikimori_fetched:
                        await fetch_shikimori(title=title, db_title=db_title, service=service, db=session)
                        await asyncio.sleep(5)
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Error while getting page {page} for {parser_id}: {e}")

    print(f"Titles for {parser_id} prepared")


@celery.task(name="prepare_all_parser_titles_task")
def prepare_all_parser_titles_wrapper(parser_id: str):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(prepare_all_parser_titles(parser_id))


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.control.purge()
    for parser_id in parsers_dict.keys():
        check_parser_wrapper.apply_async((parser_id,))
