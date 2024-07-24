import asyncio
from celery import Celery
from src.models.users import User
from src.parsers import parsers_dict
from src.utils.parsers import Parser
import os
from src.core.config import settings
from src.mail.conf import conf
from fastapi_mail import FastMail, MessageSchema, MessageType

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


async def update_parser(parser: Parser):
    service = await parser.get_service()
    for i in range(1, parser.main_pages_count+1):
        await parser.update_titles(page=i, service=service, raise_error=False)


async def check_parser(parser_id: str):
    parser: Parser = parsers_dict.get(parser_id)
    timeout = await parser.get_parser_expires_in()
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
    sender.control.purge()
    for parser_id in parsers_dict.keys():
        check_parser_wrapper.apply_async((parser_id,))
