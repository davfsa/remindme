from __future__ import annotations

import asyncpg
import confspec
import hikari
import lightbulb

from remindme import config as configuration
from remindme import extensions
from remindme.db import queries as db_queries

config = confspec.load("config.yml", cls=configuration.Config)

bot = hikari.GatewayBot(token=config.token)
client = lightbulb.client_from_app(bot)


async def pool_teardown(pool: asyncpg.pool.Pool) -> None:
    await pool.close()


@bot.listen(hikari.StartingEvent)
async def start_client(_: hikari.StartingEvent) -> None:
    """Start the client."""
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

    await client.load_extensions_from_package(extensions, recursive=True)
    await client.start()


@bot.listen(hikari.StoppedEvent)
async def stop_client(_: hikari.StoppedEvent) -> None:
    """Stop the client."""
    await client.stop()


bot.run()
