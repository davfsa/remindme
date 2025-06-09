from __future__ import annotations

import asyncpg
import confspec
import hikari
import lightbulb

from remindme import component_handler
from remindme import config as configuration
from remindme import extensions
from remindme.db import queries as db_queries

config = confspec.load("config.yml", cls=configuration.Config)

bot = hikari.RESTBot(token=config.token, public_key=config.public_key)
client = lightbulb.client_from_app(bot)


async def pool_teardown(pool: asyncpg.pool.Pool) -> None:
    await pool.close()


async def start_client(_: hikari.RESTBot) -> None:
    default_registry = client.di.registry_for(lightbulb.di.Contexts.DEFAULT)

    pool = await asyncpg.create_pool(
        host=config.db.host,
        port=config.db.port,
        database=config.db.database,
        user=config.db.username,
        password=config.db.password,
    )
    default_registry.register_value(asyncpg.Pool, pool, teardown=pool_teardown)

    queries = db_queries.Queries(pool)
    default_registry.register_value(db_queries.Queries, queries)

    token = component_handler.handler.set(ch := component_handler.ComponentHandler(client))
    default_registry.register_value(component_handler.ComponentHandler, ch)

    try:
        await client.load_extensions_from_package(extensions, recursive=True)
    finally:
        component_handler.handler.reset(token)

    await client.start()


async def stop_client(_: hikari.RESTBot) -> None:
    await client.stop()


bot.add_startup_callback(start_client)
bot.add_shutdown_callback(stop_client)

bot.run(port=config.port)
