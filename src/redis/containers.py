from dependency_injector import containers, providers

from src.redis import pool
from src.redis import services


class Container(containers.DeclarativeContainer):

    config = providers.Configuration()

    redis_pool = providers.Resource(
        pool.init_redis_pool,
        host=config.redis_host,
        password=config.redis_password,
    )

    service = providers.Factory(
        services.ParserInfoService,
        redis=redis_pool,
    )
