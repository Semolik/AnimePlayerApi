from pathlib import Path
from fastapi_mail import ConnectionConfig
from os import getenv
conf = ConnectionConfig(
    MAIL_USERNAME=getenv("EMAIL_USERNAME"),
    MAIL_PASSWORD=getenv("EMAIL_PASSWORD"),
    MAIL_FROM=getenv("EMAIL_FROM"),
    MAIL_PORT=int(getenv("EMAIL_PORT")),
    MAIL_SERVER=getenv("EMAIL_SERVER"),
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    TEMPLATE_FOLDER=Path(__file__).parent / 'templates',
)
